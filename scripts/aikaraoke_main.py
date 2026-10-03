"""
AIKaraoke Resolve - Main Script
================================
Entry point for DaVinci Resolve scripting menu.
Place this file in your DaVinci Resolve Scripts folder:

  Windows: C:\\ProgramData\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting\\Scripts\\
  Mac:     ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting/Scripts/

Then access via: Workspace > Scripts > AIKaraoke Resolve

Author: AIKaraoke Resolve Contributors
License: MIT
GitHub: https://github.com/YOUR_USERNAME/AIKaraoke-Resolve
"""

import sys
import os

# ─────────────────────────────────────────────────────────
# Auto-detect script directory to import sibling modules
# ─────────────────────────────────────────────────────────
if "__file__" in globals():
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
else:
    # Resolve internal script execution fallback
    potential_dirs = [
        r"E:\DEVELOPER\AI\FACTORY SOFTWARE\TESTING\AIKaraoke Resolve\scripts",
        os.path.join(os.environ.get("APPDATA", ""), r"Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Edit"),
        os.path.join(os.environ.get("APPDATA", ""), r"Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts"),
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Edit",
    ]
    SCRIPT_DIR = next((d for d in potential_dirs if os.path.exists(d)), os.getcwd())

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# DaVinci Resolve API paths
RESOLVE_API_PATHS = [
    "C:\\ProgramData\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting\\Modules",
    "C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\",
    "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/",
    "/opt/resolve/libs/Fusion/",
]
for p in RESOLVE_API_PATHS:
    if os.path.exists(p) and p not in sys.path:
        sys.path.append(p)

try:
    import DaVinciResolveScript as dvr
except ImportError:
    dvr = None

# ─────────────────────────────────────────────────────────
# Connect to DaVinci Resolve (handles both internal & external execution)
# ─────────────────────────────────────────────────────────
resolve_obj = globals().get("resolve")
if not resolve_obj and dvr:
    try:
        resolve_obj = dvr.scriptapp("Resolve")
    except Exception:
        resolve_obj = None

if not resolve_obj:
    print("ERROR: Could not connect to DaVinci Resolve.")
    print("Make sure DaVinci Resolve is open with a timeline.")
    sys.exit(1)

resolve = resolve_obj
project_manager = resolve.GetProjectManager()
project = project_manager.GetCurrentProject()
if not project:
    print("ERROR: No project open in DaVinci Resolve.")
    sys.exit(1)

timeline = project.GetCurrentTimeline()
if not timeline:
    print("ERROR: No timeline open. Please open a timeline first.")
    sys.exit(1)

print(f"Connected to: {project.GetName()} / {timeline.GetName()}")

# ─────────────────────────────────────────────────────────
# Configuration — edit these values or expose via GUI
# ─────────────────────────────────────────────────────────
CONFIG = {
    # Path to your song audio file (WAV recommended for best Whisper accuracy)
    "audio_file": "",

    # Output directory for generated files
    "output_dir": os.path.join(os.path.expanduser("~"), "AIKaraoke_Output"),

    # Ball appearance
    "ball_radius": 50,           # pixels (increase for higher resolution)
    "ball_color": (255, 215, 0), # RGB — golden yellow
    "bounce_height": 50,         # pixels above baseline
    "tail_length": 32,           # frames of comet tail history

    # Whisper AI settings
    "whisper_model": "base",     # tiny | base | small | medium | large
    "whisper_language": "es",    # language code: es, en, fr, pt, etc.

    # Timeline
    "ball_track_index": 3,       # Video track number for the bouncing ball
    "subtitle_track_index": 1,   # Subtitle track number

    # Ball Y positions (pixels from top, 1080p)
    "y_single_line": 895,        # Y for single-line subtitles
    "y_line1": 830,              # Y for line 1 of 2-line subtitles
    "y_line2": 895,              # Y for line 2 of 2-line subtitles

    # Font for word width calculation
    "font_size": 48,
}

# ─────────────────────────────────────────────────────────
# Main workflow
# ─────────────────────────────────────────────────────────
def run():
    """Main entry point — runs the full AIKaraoke workflow."""

    print("\n" + "="*50)
    print("  AIKaraoke Resolve - Starting")
    print("="*50)

    from resolve_integration import get_timeline_audio_path, get_subtitle_clips, relink_ball_clip

    # 1. Resolve Audio File (Auto-detect from timeline or use CONFIG)
    audio_path = CONFIG.get("audio_file", "").strip()
    if not audio_path or not os.path.exists(audio_path):
        print("\n🔍 Detecting audio directly from Timeline...")
        audio_path = get_timeline_audio_path(timeline)
        if audio_path and os.path.exists(audio_path):
            print(f"  ✓ Auto-detected timeline audio: {audio_path}")
        else:
            print("\n❌ ERROR: Could not find audio in timeline and 'audio_file' is not configured.")
            print("Please make sure you have an audio or video clip in your timeline.")
            return

    # Create output directory
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    output_ball = os.path.join(CONFIG["output_dir"], "karaoke_bouncing_ball.mov")
    output_srt  = os.path.join(CONFIG["output_dir"], "karaoke_subtitles.srt")

    # Step 1: Analyze voice with Whisper AI
    print("\n[1/3] Analyzing voice with Whisper AI...")
    from whisper_align import analyze_voice
    word_timestamps = analyze_voice(
        audio_path=audio_path,
        model_name=CONFIG["whisper_model"],
        language=CONFIG["whisper_language"],
        output_dir=CONFIG["output_dir"]
    )
    print(f"      Found {len(word_timestamps)} words with timestamps.")

    # Step 2: Read subtitle clips from timeline
    print("\n[2/3] Reading subtitle clips from timeline...")
    subtitle_clips = get_subtitle_clips(timeline)
    print(f"      Found {len(subtitle_clips)} subtitle clips.")

    # Step 3: Render bouncing ball video
    print("\n[3/3] Rendering bouncing ball (ProRes 4444 alpha)...")
    from build_ball import render_ball
    render_ball(
        word_timestamps=word_timestamps,
        subtitle_clips=subtitle_clips,
        output_file=output_ball,
        output_srt=output_srt,
        config=CONFIG
    )

    # Step 4: Relink in DaVinci Resolve
    print("\n[4/4] Updating DaVinci Resolve timeline...")
    relink_ball_clip(
        project=project,
        timeline=timeline,
        ball_file=output_ball,
        config=CONFIG
    )

    print("\n" + "="*50)
    print("  DONE! AIKaraoke Resolve complete.")
    print("="*50)
    print(f"\n  Ball video: {output_ball}")
    print(f"  Subtitles:  {output_srt}")
    print(f"\n  To sync subtitles in Resolve:")
    print(f"  File > Import > Subtitles > select karaoke_subtitles.srt")


# Execute workflow
run()
