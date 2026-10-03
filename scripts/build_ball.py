"""
build_ball.py
--------------
Renders the karaoke bouncing ball as a ProRes 4444 MOV file
with alpha channel transparency (transparent background).

Features:
  - Exact 2-step automatic vocal alignment: matches subtitle texts directly
    to Whisper AI word timestamps, eliminating any timeline delays.
  - Multi-line subtitle support (handles \\u2028, \\r\\n, \\n).
  - Centered independent X coordinate calculation for each line.
  - Smooth line-to-line transitions during inter-line vocal pauses.
  - Parabolic bounce arc over each word.
  - Golden glow with multiple radius layers and comet tail.
"""

import os
import re
import subprocess
from PIL import Image, ImageDraw, ImageFont


def _clean_word(w: str) -> str:
    """Strip punctuation and lowercase for comparison."""
    return re.sub(r"[^\w]", "", w).lower()


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


def auto_align_subtitles(subtitle_clips: list, word_timestamps: list, fps: float, base_frame: int):
    """
    Aligns each subtitle clip to the real singer vocals by matching subtitle text
    tokens to Whisper AI word-level timestamps.

    Returns:
        List of aligned clip dictionaries with 'voice_start_s', 'voice_end_s',
        'word_timings', 'lines', and 'words'.
    """
    def f2s(frame): return (frame - base_frame) / float(fps)

    aligned_clips = []
    whisper_cursor = 0

    for idx, clip in enumerate(subtitle_clips):
        raw_name = clip["text"]
        normalized = raw_name.replace("\u2028", "\n").replace("\r\n", "\n").replace("\r", "\n")
        raw_lines = [l.strip() for l in normalized.split("\n") if l.strip()]
        if not raw_lines:
            raw_lines = [raw_name.strip()]

        line_words = [l.split() for l in raw_lines]
        all_words = []
        for lw in line_words:
            all_words.extend(lw)

        target_tokens = [_clean_word(w) for w in all_words if _clean_word(w)]
        n_target = len(target_tokens)
        orig_s = f2s(clip["start_f"])
        orig_e = f2s(clip["end_f"])

        best_score = -1
        best_start_idx = whisper_cursor
        best_end_idx = whisper_cursor + max(1, n_target - 1)

        # Search window in Whisper words (around cursor and original time)
        search_max = min(len(word_timestamps), whisper_cursor + 35)
        for si in range(whisper_cursor, search_max):
            for ei in range(si, min(len(word_timestamps), si + n_target + 6)):
                cand_tokens = [_clean_word(word_timestamps[k]["word"]) for k in range(si, ei + 1)]
                hits = sum(1 for w in cand_tokens if w in target_tokens)
                score = hits / max(len(cand_tokens), n_target)
                if score > best_score:
                    best_score = score
                    best_start_idx = si
                    best_end_idx = ei

        if best_score >= 0.25 and best_start_idx < len(word_timestamps):
            # Narrow/expand to the first and last actual matching token
            matched_indices = [k for k in range(best_start_idx, best_end_idx + 1)
                               if _clean_word(word_timestamps[k]["word"]) in target_tokens]
            if matched_indices:
                v_start = word_timestamps[matched_indices[0]]["start"]
                v_end = word_timestamps[matched_indices[-1]]["end"]
                sub_whisper_slice = word_timestamps[matched_indices[0]:matched_indices[-1] + 1]
                whisper_cursor = matched_indices[-1] + 1
            else:
                v_start = word_timestamps[best_start_idx]["start"]
                v_end = word_timestamps[best_end_idx]["end"]
                sub_whisper_slice = word_timestamps[best_start_idx:best_end_idx + 1]
                whisper_cursor = best_end_idx + 1
        else:
            v_start = orig_s
            v_end = orig_e
            sub_whisper_slice = []

        # Map timings to each word
        word_timings = []
        n_sub = len(all_words)
        n_whi = len(sub_whisper_slice)

        if n_whi == 0:
            span = max(0.1, v_end - v_start)
            dur = span / max(1, n_sub)
            for i in range(n_sub):
                ws = v_start + i * dur
                word_timings.append((ws, ws + dur))
        elif n_whi >= n_sub:
            for i in range(n_sub):
                word_timings.append((sub_whisper_slice[i]["start"], sub_whisper_slice[i]["end"]))
        else:
            for i in range(n_sub):
                if i < n_whi:
                    word_timings.append((sub_whisper_slice[i]["start"], sub_whisper_slice[i]["end"]))
                else:
                    prev_end = word_timings[-1][1]
                    rem = n_sub - i
                    dur = max(0.1, v_end - prev_end) / rem
                    word_timings.append((prev_end, prev_end + dur))

        aligned_clips.append({
            "index":        idx + 1,
            "raw_text":     raw_name,
            "lines":        raw_lines,
            "line_words":   line_words,
            "all_words":    all_words,
            "voice_start_s": v_start,
            "voice_end_s":   v_end,
            "word_timings": word_timings,
            "orig_start_f": clip["start_f"],
            "orig_end_f":   clip["end_f"]
        })

    return aligned_clips


def _write_perfect_srt(aligned_clips, base_frame, fps, output_srt):
    """Writes an absolute-timed SRT file (01:00:XX,XXX) synchronized to real singer voice."""
    tc_offset = base_frame / float(fps)

    def fmt(sec_from_audio):
        total = sec_from_audio + tc_offset
        h  = int(total // 3600)
        m  = int((total % 3600) // 60)
        s  = int(total % 60)
        ms = int(round((total - int(total)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    entries = []
    for c in aligned_clips:
        # Give a small 0.12s visual pre-roll before first word, and 0.3s hold after last word
        st = max(0.0, c["voice_start_s"] - 0.12)
        en = c["voice_end_s"] + 0.30
        text_block = "\n".join(c["lines"])
        entries.append(f"{c['index']}\n{fmt(st)} --> {fmt(en)}\n{text_block}\n")

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(entries))


def render_ball(word_timestamps: list, subtitle_clips: list,
                output_file: str, output_srt: str, config: dict):
    """
    Render the bouncing ball video and generate the voice-aligned SRT file.
    """
    width, height   = 1920, 1080
    fps             = 24
    base_frame      = 86400
    ball_radius     = config.get("ball_radius", 40)
    ball_color      = config.get("ball_color", (255, 215, 0))
    bounce_height   = config.get("bounce_height", 45)
    max_tail        = config.get("tail_length", 28)
    y_single        = config.get("y_single_line", 895)
    y_line1         = config.get("y_line1", 820)
    y_line2         = config.get("y_line2", 895)
    font_size       = config.get("font_size", 48)

    if subtitle_clips:
        first_start = min(c["start_f"] for c in subtitle_clips)
        base_frame = (first_start // (3600 * fps)) * (3600 * fps)

    def s2f(sec): return sec * fps + base_frame

    # Font setup
    font_path = _find_font()
    font = ImageFont.truetype(font_path, font_size)
    space_w = font.getlength(" ")

    # ── Step 1: Precise Vocal Alignment ─────────────────────────────────────
    print("  [Auto-Align] Synchronizing subtitles with singer voice...")
    aligned_clips = auto_align_subtitles(subtitle_clips, word_timestamps, fps, base_frame)

    # Save perfected SRT
    _write_perfect_srt(aligned_clips, base_frame, fps, output_srt)
    print(f"  [OK] Saved perfectly synced subtitles to: {output_srt}")

    # ── Step 2: Build Animation Schedules ──────────────────────────────────
    schedules = []
    for c in aligned_clips:
        line_word_lists = c["line_words"]
        word_timings = c["word_timings"]
        is_multi_line = len(line_word_lists) > 1

        nodes = []
        flat_idx = 0
        for l_idx, l_words in enumerate(line_word_lists):
            if not l_words:
                continue
            y_base = y_single if not is_multi_line else (y_line1 if l_idx == 0 else y_line2)

            widths = [font.getlength(w) for w in l_words]
            total_w = sum(widths) + (len(l_words) - 1) * space_w
            cur_x = 960.0 - total_w / 2.0

            for w in l_words:
                w_w = font.getlength(w)
                cx = cur_x + w_w / 2.0
                cur_x += w_w + space_w

                ws, we = word_timings[flat_idx] if flat_idx < len(word_timings) else (c["voice_start_s"], c["voice_end_s"])
                nodes.append({
                    "word":     w,
                    "line_idx": l_idx,
                    "cx":       cx,
                    "cy":       float(y_base),
                    "start":    s2f(ws),
                    "end":      s2f(we)
                })
                flat_idx += 1

        if nodes:
            # Active interval strictly matches actual vocal start and end
            sched_start_f = s2f(c["voice_start_s"] - 0.12)
            sched_end_f   = s2f(c["voice_end_s"] + 0.30)
            schedules.append({
                "clip_start":  sched_start_f,
                "clip_end":    sched_end_f,
                "voice_start": s2f(c["voice_start_s"]),
                "voice_end":   s2f(c["voice_end_s"]),
                "nodes":       nodes
            })

    video_codec = config.get("video_codec", "qtrle")

    # ── Step 3: Render Video via ffmpeg ────────────────────────────────────
    total_frames = max(s["clip_end"] for s in schedules) - base_frame + fps * 2
    total_frames = int(total_frames)

    _render_video(
        schedules, base_frame, total_frames, fps,
        width, height, ball_radius, ball_color,
        bounce_height, max_tail, output_file,
        video_codec=video_codec
    )


def _render_video(schedules, base_frame, total_frames, fps,
                  width, height, ball_radius, ball_color,
                  bounce_height, max_tail, output_file,
                  video_codec: str = "qtrle"):
    """Renders video frames via ffmpeg pipe with minimal CPU overhead."""
    if video_codec == "prores":
        codec_flags = ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"]
        codec_desc = "Apple ProRes 4444 (High Quality)"
    else:
        # QuickTime Animation (RLE Alpha) is native in Resolve and renders at 300+ fps with <15% CPU
        codec_flags = ["-c:v", "qtrle"]
        codec_desc = "QuickTime Animation (RLE Alpha - Ultra Fast & Low CPU)"

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgba",
        "-r", str(fps),
        "-i", "-",
        *codec_flags,
        output_file
    ]

    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    empty = b"\x00" * (width * height * 4)  # Zero-allocation static empty buffer
    tail = []
    r, g, b = ball_color

    print(f"  Rendering {total_frames} frames using {codec_desc}...")

    for f in range(total_frames):
        abs_f = base_frame + f

        if f % 500 == 0:
            print(f"  Frame {f:5d}/{total_frames} ({100*f//total_frames}%)")

        active = next((s for s in schedules
                       if s["clip_start"] <= abs_f <= s["clip_end"]), None)

        if not active or abs_f < active["voice_start"] or abs_f > active["voice_end"]:
            tail.clear()
            process.stdin.write(empty)
            continue

        nodes = active["nodes"]

        # Find current word
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

        # Coordinates with line transition support
        if curr["line_idx"] != nxt["line_idx"] and curr != nxt:
            if p < 0.70:
                local_p = p / 0.70
                x = curr["cx"]
                y = curr["cy"] - 4.0 * bounce_height * local_p * (1.0 - local_p)
            else:
                trans_p = (p - 0.70) / 0.30
                x = curr["cx"] + (nxt["cx"] - curr["cx"]) * trans_p
                y = (curr["cy"] + (nxt["cy"] - curr["cy"]) * trans_p) - 2.5 * bounce_height * trans_p * (1.0 - trans_p)
        else:
            x = curr["cx"] + (nxt["cx"] - curr["cx"]) * p
            y = (curr["cy"] + (nxt["cy"] - curr["cy"]) * p) - 4.0 * bounce_height * p * (1.0 - p)

        tail.append((x, y))
        if len(tail) > max_tail:
            tail.pop(0)

        img  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Comet tail
        n_hist = len(tail)
        for idx, (hx, hy) in enumerate(tail[:-1]):
            fac = (idx + 1) / float(n_hist)
            fade = fac ** 1.5
            tr = int(22 * fac + 3)
            ta = int(180 * fade)
            draw.ellipse([hx-tr, hy-tr, hx+tr, hy+tr], fill=(r, g//2, 0, int(ta*0.35)))
            r2 = max(3, int(tr * 0.55))
            draw.ellipse([hx-r2, hy-r2, hx+r2, hy+r2], fill=(r, g, b//4, ta))

        # Golden glow
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
        print(f"  [OK] Render complete: {output_file}")
    else:
        print(f"  [ERROR] ffmpeg exited with code {ret}")
