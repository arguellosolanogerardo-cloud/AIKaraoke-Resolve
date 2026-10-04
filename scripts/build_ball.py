"""
build_ball.py
--------------
Renders the karaoke bouncing ball as a transparent MOV file
(QuickTime Animation RLE with Alpha or ProRes 4444).

Features:
  - Exact sequential subtitle alignment to Whisper AI word timestamps.
  - Generates perfectly voice-synced SRT files.
  - Tighter, lower bounce height (20px) directly over syllables.
  - Word-synchronized parabolic jump: lands on each word at the exact vocal start.
  - Longer, ultra-saturated fiery golden comet tail (50 frames history).
  - Multi-line subtitle support (detects \\u2028, \\r\\n, \\n).
  - Centered X per line and smooth line-to-line transitions.
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
    Performs precise sequential alignment between subtitle texts and Whisper word timestamps.
    Ensures every subtitle begins at the exact vocal millisecond.
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

        if not target_tokens or whisper_cursor >= len(word_timestamps):
            # Fallback to original timeline bounds if voice is exhausted (instrumental outro)
            v_start = orig_s
            v_end = orig_e
            sub_whisper_slice = []
        else:
            first_clean = target_tokens[0]
            last_clean = target_tokens[-1]

            # 1. Search for start word anchor
            start_found = -1
            for k in range(whisper_cursor, min(len(word_timestamps), whisper_cursor + 28)):
                cand = _clean_word(word_timestamps[k]["word"])
                if cand == first_clean or (len(target_tokens) > 1 and cand == target_tokens[1]):
                    start_found = k
                    break
            if start_found == -1:
                start_found = whisper_cursor

            # 2. Search for end word anchor
            end_found = -1
            search_start_end = start_found + max(0, n_target - 5)
            search_end_limit = min(len(word_timestamps), start_found + n_target + 12)
            for k in range(search_start_end, search_end_limit):
                if k >= start_found and _clean_word(word_timestamps[k]["word"]) == last_clean:
                    end_found = k
                    break
            if end_found == -1:
                end_found = min(len(word_timestamps) - 1, start_found + max(0, n_target - 1))

            v_start = word_timestamps[start_found]["start"]
            v_end = word_timestamps[end_found]["end"]
            sub_whisper_slice = word_timestamps[start_found : end_found + 1]
            whisper_cursor = end_found + 1

        # Assign timings to each subtitle word
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
            "index":         idx + 1,
            "raw_text":      raw_name,
            "lines":         raw_lines,
            "line_words":    line_words,
            "all_words":     all_words,
            "voice_start_s": v_start,
            "voice_end_s":   v_end,
            "word_timings":  word_timings,
            "orig_start_f":  clip["start_f"],
            "orig_end_f":    clip["end_f"]
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
        # Pre-roll of 0.10s before vocal attack, hold for 0.30s after phrase
        st = max(0.0, c["voice_start_s"] - 0.10)
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
    ball_radius     = config.get("ball_radius", 38)
    ball_color      = config.get("ball_color", (255, 205, 0))
    bounce_height   = config.get("bounce_height", 20)      # Reduced height (tighter jump)
    max_tail        = config.get("tail_length", 50)        # Longer saturated comet tail
    y_single        = config.get("y_single_line", 895)
    y_line1         = config.get("y_line1", 820)
    y_line2         = config.get("y_line2", 895)
    font_size       = config.get("font_size", 48)
    video_codec     = config.get("video_codec", "qtrle")

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
            sched_start_f = s2f(c["voice_start_s"] - 0.10)
            sched_end_f   = s2f(c["voice_end_s"] + 0.30)
            schedules.append({
                "clip_start":  sched_start_f,
                "clip_end":    sched_end_f,
                "voice_start": s2f(c["voice_start_s"]),
                "voice_end":   s2f(c["voice_end_s"]),
                "nodes":       nodes
            })

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
    """Renders video frames via ffmpeg pipe with optimized CPU usage and rich comet tail."""
    if video_codec == "prores":
        codec_flags = ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"]
        codec_desc = "Apple ProRes 4444"
    else:
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
    empty = b"\x00" * (width * height * 4)  # Static zero-allocation buffer
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

        # Find current word or nearest
        curr = None
        for n in nodes:
            if n["start"] <= abs_f <= n["end"]:
                curr = n
                break

        if curr is None:
            if abs_f < nodes[0]["start"]:
                curr = nodes[0]
                nxt = nodes[0]
                p_jump = 0.0
                is_jumping = False
            else:
                curr = nodes[-1]
                nxt = nodes[-1]
                p_jump = 1.0
                is_jumping = False
        else:
            n_idx = nodes.index(curr)
            if n_idx + 1 < len(nodes):
                nxt = nodes[n_idx + 1]
            else:
                nxt = curr

            word_dur = max(1.0, curr["end"] - curr["start"])
            rel_f = abs_f - curr["start"]

            # Synchronized jumping physics:
            # First 60% of the word duration: Ball rests directly on current word
            # Last 40% of duration: Ball leaps in a parabolic arc and lands on next word at vocal start
            takeoff_f = curr["start"] + 0.60 * word_dur
            if abs_f < takeoff_f or curr == nxt:
                is_jumping = False
                p_jump = 0.0
            else:
                is_jumping = True
                jump_dur = max(1.0, nxt["start"] - takeoff_f)
                p_jump = max(0.0, min(1.0, (abs_f - takeoff_f) / jump_dur))

        # Position calculation
        if not is_jumping:
            x = curr["cx"]
            # Gentle breath idle hover over the active syllable
            y = curr["cy"]
        else:
            if curr["line_idx"] != nxt["line_idx"]:
                # Line-to-line transition
                x = curr["cx"] + (nxt["cx"] - curr["cx"]) * p_jump
                y = (curr["cy"] + (nxt["cy"] - curr["cy"]) * p_jump) - 1.8 * bounce_height * p_jump * (1.0 - p_jump)
            else:
                # Same-line crisp parabolic jump directly to next word
                x = curr["cx"] + (nxt["cx"] - curr["cx"]) * p_jump
                # Parabolic peak
                arc = 4.0 * bounce_height * p_jump * (1.0 - p_jump)
                y = (curr["cy"] + (nxt["cy"] - curr["cy"]) * p_jump) - arc

        tail.append((x, y))
        if len(tail) > max_tail:
            tail.pop(0)

        img  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Longer, highly saturated fiery golden comet tail
        n_hist = len(tail)
        for idx, (hx, hy) in enumerate(tail[:-1]):
            fac = (idx + 1) / float(n_hist)
            fade = fac ** 1.3
            tr = int(24 * fac + 4)

            # Outer fiery aura (saturated warm orange-red)
            ta_outer = int(140 * fade)
            draw.ellipse([hx-tr, hy-tr, hx+tr, hy+tr], fill=(255, 90, 0, ta_outer))

            # Mid glowing body (saturated golden amber)
            r_mid = max(3, int(tr * 0.65))
            ta_mid = int(220 * fade)
            draw.ellipse([hx-r_mid, hy-r_mid, hx+r_mid, hy+r_mid], fill=(255, 185, 0, ta_mid))

            # Bright inner streak (luminous light gold)
            r_core = max(2, int(tr * 0.35))
            ta_core = int(255 * fade)
            draw.ellipse([hx-r_core, hy-r_core, hx+r_core, hy+r_core], fill=(255, 245, 140, ta_core))

        # Golden glow layers on the ball
        for rad, alpha in [
            (ball_radius,               30),
            (int(ball_radius * 0.75),   65),
            (int(ball_radius * 0.55),  130),
            (int(ball_radius * 0.38),  200),
            (int(ball_radius * 0.25),  245),
        ]:
            draw.ellipse([x-rad, y-rad, x+rad, y+rad], fill=(r, g, b, alpha))

        # Core brilliant center
        draw.ellipse([x-6, y-6, x+6, y+6], fill=(255, 255, 240, 255))

        process.stdin.write(img.tobytes())

    process.stdin.close()
    ret = process.wait()
    if ret == 0:
        print(f"  [OK] Render complete: {output_file}")
    else:
        print(f"  [ERROR] ffmpeg exited with code {ret}")
