"""
resolve_integration.py
-----------------------
DaVinci Resolve API integration module.
Handles reading subtitle clips and relinking the ball video in the timeline.
"""

import os
import sys


def _get_resolve_api():
    """Import DaVinciResolveScript, adding API paths if needed."""
    api_paths = [
        "C:\\ProgramData\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting\\Modules",
        "C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\",
        "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/",
        "/opt/resolve/libs/Fusion/",
    ]
    for p in api_paths:
        if os.path.exists(p) and p not in sys.path:
            sys.path.append(p)

    import DaVinciResolveScript as dvr
    return dvr


def get_timeline_audio_path(timeline) -> str:
    """
    Detects the audio or video source file path directly from the timeline clips.
    First inspects Audio tracks (A1, A2...), then Video tracks (V1...).
    
    Returns:
        Full path to the media file on disk, or empty string if not found.
    """
    # 1. Search in Audio tracks
    audio_track_count = timeline.GetTrackCount("audio")
    for t_idx in range(1, audio_track_count + 1):
        items = timeline.GetItemListInTrack("audio", t_idx)
        if items:
            for item in items:
                mpi = item.GetMediaPoolItem()
                if mpi:
                    props = mpi.GetClipProperty()
                    file_path = props.get("File Path") if isinstance(props, dict) else mpi.GetClipProperty("File Path")
                    if file_path and os.path.exists(file_path):
                        return file_path

    # 2. Search in Video tracks (videos with embedded audio)
    video_track_count = timeline.GetTrackCount("video")
    for t_idx in range(1, video_track_count + 1):
        items = timeline.GetItemListInTrack("video", t_idx)
        if items:
            for item in items:
                mpi = item.GetMediaPoolItem()
                if mpi:
                    props = mpi.GetClipProperty()
                    file_path = props.get("File Path") if isinstance(props, dict) else mpi.GetClipProperty("File Path")
                    if file_path and os.path.exists(file_path):
                        return file_path

    return ""


def get_subtitle_clips(timeline) -> list:
    """
    Read all subtitle clips from Subtitle Track 1 of the timeline.

    Returns:
        List of dicts: [{"index", "start_f", "end_f", "text"}, ...]
    """
    clips = []
    try:
        items = timeline.GetItemListInTrack("subtitle", 1)
        if not items:
            return clips
        for i, item in enumerate(items):
            clips.append({
                "index":   i + 1,
                "start_f": item.GetStart(),
                "end_f":   item.GetEnd(),
                "text":    item.GetName(),
            })
    except Exception as e:
        print(f"  WARNING: Could not read subtitle track: {e}")

    return clips


def get_timeline_info(timeline) -> dict:
    """Get basic timeline properties."""
    return {
        "name":        timeline.GetName(),
        "start_frame": timeline.GetStartFrame(),
        "end_frame":   timeline.GetEndFrame(),
        "fps":         float(timeline.GetSetting("timelineFrameRate") or 24),
        "video_tracks":    timeline.GetTrackCount("video"),
        "subtitle_tracks": timeline.GetTrackCount("subtitle"),
    }


def find_clip_in_pool(media_pool, clip_name: str):
    """Recursively search the Media Pool for a clip by name."""
    def _search(folder):
        clips = folder.GetClipList()
        if clips:
            for c in clips:
                if c.GetName() == clip_name:
                    return c
        subs = folder.GetSubFolderList()
        if subs:
            for sf in subs:
                found = _search(sf)
                if found:
                    return found
        return None

    return _search(media_pool.GetRootFolder())


def relink_ball_clip(project, timeline, ball_file: str, config: dict) -> bool:
    """
    Relink the bouncing ball .mov clip in the Media Pool to the new rendered file.
    If the clip doesn't exist in the pool, import it and place it on the ball track.

    Args:
        project:   DaVinci Resolve project object
        timeline:  Current timeline object
        ball_file: Full path to the rendered karaoke_bouncing_ball.mov
        config:    CONFIG dict with ball_track_index

    Returns:
        True if successful, False otherwise
    """
    media_pool = project.GetMediaPool()
    clip_name  = os.path.basename(ball_file)
    clip_dir   = os.path.dirname(ball_file)

    # Try to find existing clip and relink
    existing = find_clip_in_pool(media_pool, clip_name)
    if existing:
        result = media_pool.RelinkClips([existing], clip_dir)
        if result:
            print(f"  Relinked '{clip_name}' in Media Pool.")
            return True
        else:
            print(f"  WARNING: RelinkClips failed for '{clip_name}'.")

    clip_to_insert = existing
    # If not found in pool, import it
    if not clip_to_insert and os.path.exists(ball_file):
        imported = media_pool.ImportMedia([ball_file])
        if imported:
            clip_to_insert = imported[0]
            print(f"  Imported '{clip_name}' into Media Pool.")

    # Check if clip is already on the timeline
    is_on_timeline = False
    for t_idx in range(1, timeline.GetTrackCount("video") + 1):
        for it in timeline.GetItemListInTrack("video", t_idx):
            if it.GetName() == clip_name:
                is_on_timeline = True
                break
        if is_on_timeline:
            break

    if not is_on_timeline and clip_to_insert:
        target_track = config.get("ball_track_index", 2)
        while timeline.GetTrackCount("video") < target_track:
            timeline.AddTrack("video")

        try:
            res = media_pool.AppendToTimeline([{
                "mediaPoolItem": clip_to_insert,
                "recordFrame": timeline.GetStartFrame(),
                "trackIndex": target_track
            }])
            print(f"  Auto-placed '{clip_name}' on Video Track {target_track} at frame {timeline.GetStartFrame()}.")
        except Exception as e:
            print(f"  Could not auto-place on timeline: {e}. Please drag '{clip_name}' to Video Track {target_track}.")

    return True


def export_subtitle_timecodes(timeline, output_path: str) -> list:
    """
    Export subtitle clip timecodes to a JSON file.
    Useful for debugging and re-runs without Resolve open.

    Args:
        timeline:    DaVinci Resolve timeline object
        output_path: Path to save the JSON file

    Returns:
        List of subtitle clip dicts
    """
    import json

    clips = get_subtitle_clips(timeline)
    info  = get_timeline_info(timeline)

    data = {
        "timeline_name":   info["name"],
        "start_frame":     info["start_frame"],
        "fps":             info["fps"],
        "subtitle_tracks": info["subtitle_tracks"],
        "subtitles":       clips,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  Exported {len(clips)} subtitle timecodes to {output_path}")
    return clips
