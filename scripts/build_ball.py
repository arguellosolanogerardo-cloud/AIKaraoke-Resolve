"""
build_ball.py
--------------
Renders the karaoke bouncing ball as a ProRes 4444 MOV file
with alpha channel transparency (transparent background).

Features:
  - Exact 1-line and 2-line subtitle detection (handles \\u2028, \\r\\n, \\n)
  - Centered independent X calculation for each line
  - Smooth line-to-line transitions during inter-line pauses
  - Parabolic bounce arc over each word
  - Golden glow with multiple radius layers
  - Comet tail with fade history

Requires: pip install Pillow
          ffmpeg in system PATH
"""

import os
import re
import subprocess
from PIL import Image, ImageDraw, ImageFont


def render_ball(word_timestamps: list, subtitle_clips: list,
                output_file: str, output_srt: str, config: dict):
    """
    Render the bouncing ball video and generate the SRT file.

    Args:
        word_timestamps: List of {"word", "start", "end"} from Whisper AI
        subtitle_clips:  List of {"index", "start_f", "end_f", "text"} from Resolve
        output_file:     Output .mov path (ProRes 4444 with alpha)
        output_srt:      Output .srt path with voice-synced timestamps
        config:          CONFIG dict from aikaraoke_main.py
    """
    # ── Setup ──────────────────────────────────────────────────────────────
    width, height   = 1920, 1080
    fps             = 24
    base_frame      = 86400  # Default 01:00:00:00
    ball_radius     = config.get("ball_radius", 40)
    ball_color      = config.get("ball_color", (255, 215, 0))
    bounce_height   = config.get("bounce_height", 45)
    max_tail        = config.get("tail_length", 28)
    y_single        = config.get("y_single_line", 895)
    y_line1         = config.get("y_line1", 820)
    y_line2         = config.get("y_line2", 895)
    font_size       = config.get("font_size", 48)

    # Use timeline start frame from first subtitle clip
    if subtitle_clips:
        first_start = min(c["start_f"] for c in subtitle_clips)
        base_frame = (first_start // (3600 * fps)) * (3600 * fps)

    def f2s(frame):  return (frame - base_frame) / float(fps)
    def s2f(sec):    return sec * fps + base_frame

    # Font for word width calculation
    font_path = _find_font()
    font = ImageFont.truetype(font_path, font_size)
    space_w = font.getlength(" ")

    # ── Build animation schedule ───────────────────────────────────────────
    sub_schedules = _build_schedules(
        subtitle_clips, word_timestamps, font, space_w,
        y_single, y_line1, y_line2, base_frame, fps, f2s, s2f
    )

    # ── Generate voice-synced SRT ──────────────────────────────────────────
    _write_srt(sub_schedules, subtitle_clips, base_frame, fps, output_srt)
    print(f"  SRT saved: {output_srt}")

    # ── Render video via ffmpeg ────────────────────────────────────────────
    total_frames = max(c["end_f"] for c in subtitle_clips) - base_frame + fps
    _render_video(
        sub_schedules, base_frame, total_frames, fps,
        width, height, ball_radius, ball_color,
        bounce_height, max_tail, output_file
    )


# ── Helpers ────────────────────────────────────────────────────────────────

def _find_font() -> str:
    """Find a suitable font file for word width measurement."""
    candidates = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("No font file found. Install Arial font.")


def _clean_word(w: str) -> str:
    """Strip punctuation and lowercase for comparison."""
    return re.sub(r"[^\w]", "", w).lower()


def _build_schedules(subtitle_clips, word_timestamps, font, space_w,
                     y_single, y_line1, y_line2, base_frame, fps, f2s, s2f):
    """Map Whisper word timestamps to subtitle clip positions."""
    schedules = []

    for clip in subtitle_clips:
        clip_start_s = f2s(clip["start_f"])
        clip_end_s   = f2s(clip["end_f"])
        raw_text     = clip["text"]

        # Normalize line breaks: replace Unicode \u2028 (Line Separator), \r\n, \r with \n
        normalized_text = raw_text.replace("\u2028", "\n").replace("\r\n", "\n").replace("\r", "\n")
        raw_lines = [l.strip() for l in normalized_text.split("\n") if l.strip()]

        if not raw_lines:
            continue

        # Extract words per line
        line_word_lists = [l.split() for l in raw_lines]
        all_sub_words = []
        for l_words in line_word_lists:
            all_sub_words.extend(l_words)
        n_sub = len(all_sub_words)

        # Find Whisper words in this clip's time window
        whisper_in = [
            w for w in word_timestamps
            if w["start"] >= clip_start_s - 0.2 and w["start"] <= clip_end_s + 1.2
        ]
        n_whi = len(whisper_in)

        if whisper_in:
            voice_start_s = max(clip_start_s, whisper_in[0]["start"])
            voice_end_s   = min(clip_end_s, max(voice_start_s + 0.5, whisper_in[-1]["end"]))
        else:
            voice_start_s = clip_start_s
            voice_end_s   = clip_end_s

        # Map timings to subtitle words
        word_timings = []
        if n_whi == 0:
            span = max(0.1, clip_end_s - clip_start_s)
            dur = span / max(1, n_sub)
            for i in range(n_sub):
                ws = clip_start_s + i * dur
                word_timings.append((ws, ws + dur))
        elif n_whi >= n_sub:
            for i in range(n_sub):
                word_timings.append((whisper_in[i]["start"], whisper_in[i]["end"]))
        else:
            for i in range(n_sub):
                if i < n_whi:
                    word_timings.append((whisper_in[i]["start"], whisper_in[i]["end"]))
                else:
                    prev_end = word_timings[-1][1]
                    rem = n_sub - i
                    dur = max(0.1, voice_end_s - prev_end) / rem
                    word_timings.append((prev_end, prev_end + dur))

        # Build word nodes with calculated (X, Y) positions
        nodes = []
        flat_idx = 0
        is_multi_line = len(line_word_lists) > 1

        for l_idx, l_words in enumerate(line_word_lists):
            if not l_words:
                continue
            y_base = y_single if not is_multi_line else (y_line1 if l_idx == 0 else y_line2)

            widths = [font.getlength(w) for w in l_words]
            total_w = sum(widths) + (len(l_words) - 1) * space_w
            cur_x = 960.0 - total_w / 2.0

            for w_idx, w in enumerate(l_words):
                w_w = font.getlength(w)
                cx = cur_x + w_w / 2.0
                cur_x += w_w + space_w

                ws, we = word_timings[flat_idx] if flat_idx < len(word_timings) else (clip_start_s, clip_end_s)
                nodes.append({
                    "word": w,
                    "line_idx": l_idx,
                    "cx": cx,
                    "cy": float(y_base),
                    "start": s2f(ws),
                    "end": s2f(we)
                })
                flat_idx += 1

        if nodes:
            schedules.append({
                "clip_start":   clip["start_f"],
                "clip_end":     clip["end_f"],
                "voice_start":  s2f(voice_start_s),
                "voice_end":    s2f(voice_end_s),
                "nodes": nodes
            })

    return schedules


def _write_srt(schedules, subtitle_clips, base_frame, fps, output_srt):
    """Generate SRT file with voice-synced timestamps."""
    tc_offset = base_frame / fps

    def fmt(sec_from_audio):
        total = sec_from_audio + tc_offset
        h  = int(total // 3600)
        m  = int((total % 3600) // 60)
        s  = int(total % 60)
        ms = int(round((total - int(total)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def f2s(frame): return (frame - base_frame) / float(fps)

    entries = []
    for i, (sched, clip) in enumerate(zip(schedules, subtitle_clips)):
        vs = f2s(sched["voice_start"])
        ve = f2s(sched["voice_end"])
        clean_text = clip['text'].replace("\u2028", "\n")
        entries.append(f"{i+1}\n{fmt(vs)} --> {fmt(ve)}\n{clean_text}\n")

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(entries))


def _render_video(schedules, base_frame, total_frames, fps,
                  width, height, ball_radius, ball_color,
                  bounce_height, max_tail, output_file):
    """Render ProRes 4444 video with bouncing ball."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgba",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "prores_ks",
        "-profile:v", "4444",
        "-pix_fmt", "yuva444p10le",
        output_file
    ]

    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    empty   = Image.new("RGBA", (width, height), (0, 0, 0, 0)).tobytes()
    tail    = []
    r, g, b = ball_color

    print(f"  Rendering {total_frames} frames to {output_file}...")

    for f in range(total_frames):
        abs_f = base_frame + f

        if f % 500 == 0:
            print(f"  Frame {f:5d}/{total_frames} ({100*f//total_frames}%)")

        # Find active subtitle schedule
        active = next((s for s in schedules
                       if s["clip_start"] <= abs_f <= s["clip_end"]), None)

        if not active or abs_f < active["voice_start"] or abs_f > active["voice_end"]:
            tail.clear()
            process.stdin.write(empty)
            continue

        nodes = active["nodes"]

        # Find node that contains abs_f or is closest
        curr = None
        for n in nodes:
            if n["start"] <= abs_f <= n["end"]:
                curr = n
                break

        if curr is None:
            if abs_f < nodes[0]["start"]:
                curr = nodes[0]
                nxt = nodes[0]
                p = 0.0
            else:
                curr = nodes[-1]
                nxt = nodes[-1]
                p = 1.0
        else:
            n_idx = nodes.index(curr)
            dur = max(1.0, curr["end"] - curr["start"])
            p = max(0.0, min(1.0, (abs_f - curr["start"]) / dur))

            if n_idx + 1 < len(nodes):
                nxt = nodes[n_idx + 1]
            else:
                nxt = curr

        # Calculate X and Y coordinates
        # Check if jumping between two different lines
        if curr["line_idx"] != nxt["line_idx"] and curr != nxt:
            # During the word on line 1, stay on line 1:
            if p < 0.75:
                # Bounce on curr word
                local_p = p / 0.75
                x = curr["cx"]
                y = curr["cy"] - 4.0 * bounce_height * local_p * (1.0 - local_p)
            else:
                # Smooth glide to first word of next line
                trans_p = (p - 0.75) / 0.25
                x = curr["cx"] + (nxt["cx"] - curr["cx"]) * trans_p
                y = (curr["cy"] + (nxt["cy"] - curr["cy"]) * trans_p) - 2.0 * bounce_height * trans_p * (1.0 - trans_p)
        else:
            # Same line: smooth bounce towards next word center
            x = curr["cx"] + (nxt["cx"] - curr["cx"]) * p
            y = (curr["cy"] + (nxt["cy"] - curr["cy"]) * p) - 4.0 * bounce_height * p * (1.0 - p)

        tail.append((x, y))
        if len(tail) > max_tail:
            tail.pop(0)

        img  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Comet tail with gradient fade
        n_hist = len(tail)
        for idx, (hx, hy) in enumerate(tail[:-1]):
            fac = (idx + 1) / float(n_hist)
            fade = fac ** 1.5
            tr = int(22 * fac + 3)
            ta = int(180 * fade)
            draw.ellipse([hx-tr, hy-tr, hx+tr, hy+tr], fill=(r, g//2, 0, int(ta*0.35)))
            r2 = max(3, int(tr * 0.55))
            draw.ellipse([hx-r2, hy-r2, hx+r2, hy+r2], fill=(r, g, b//4, ta))

        # Golden glow layers
        for rad, alpha in [
            (ball_radius,               18),
            (int(ball_radius * 0.75),   42),
            (int(ball_radius * 0.55),   90),
            (int(ball_radius * 0.38),  160),
            (int(ball_radius * 0.25),  220),
        ]:
            draw.ellipse([x-rad, y-rad, x+rad, y+rad], fill=(r, g, b, alpha))

        # Core
        draw.ellipse([x-7, y-7, x+7, y+7], fill=(255, 255, 250, 255))

        process.stdin.write(img.tobytes())

    process.stdin.close()
    ret = process.wait()
    if ret == 0:
        print(f"  Render complete: {output_file}")
    else:
        print(f"  ERROR: ffmpeg exited with code {ret}")
