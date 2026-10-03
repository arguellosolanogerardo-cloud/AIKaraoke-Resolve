"""
whisper_align.py
-----------------
Whisper AI voice analysis module.
Extracts word-level timestamps from an audio file.

Requires: pip install openai-whisper
"""

import os
import json


def analyze_voice(audio_path: str, model_name: str = "base",
                  language: str = "es", output_dir: str = ".") -> list:
    """
    Analyze an audio file with Whisper AI and extract word-level timestamps.

    Args:
        audio_path:  Path to the audio file (WAV, MP3, M4A, etc.)
        model_name:  Whisper model size: tiny | base | small | medium | large
                     Larger = more accurate but slower.
                     Recommended: 'base' for speed, 'small' for better accuracy.
        language:    ISO language code (es=Spanish, en=English, fr=French, etc.)
                     Use None for auto-detection.
        output_dir:  Directory to save the word timestamps JSON file.

    Returns:
        List of dicts: [{"word": str, "start": float, "end": float}, ...]
    """
    try:
        import whisper
    except ImportError:
        raise ImportError(
            "openai-whisper not installed. Run: pip install openai-whisper"
        )

    cache_file = os.path.join(output_dir, "whisper_word_timestamps.json")

    # Use cached results if available (saves time on re-runs)
    if os.path.exists(cache_file):
        print(f"  Loading cached Whisper results from {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"  Loading Whisper model: '{model_name}'...")
    model = whisper.load_model(model_name)

    print(f"  Transcribing audio (language='{language}')...")
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        verbose=False
    )

    # Extract word-level timestamps
    word_timestamps = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            word_timestamps.append({
                "word":  word_info["word"].strip(),
                "start": round(word_info["start"], 3),
                "end":   round(word_info["end"], 3),
            })

    # Save to cache
    os.makedirs(output_dir, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(word_timestamps, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(word_timestamps)} word timestamps to {cache_file}")

    return word_timestamps


if __name__ == "__main__":
    # Quick test
    import sys
    if len(sys.argv) < 2:
        print("Usage: python whisper_align.py <audio_file> [model] [language]")
        sys.exit(1)

    audio = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "base"
    lang  = sys.argv[3] if len(sys.argv) > 3 else "es"

    words = analyze_voice(audio, model, lang, os.path.dirname(audio))
    print(f"\nFirst 10 words:")
    for w in words[:10]:
        print(f"  {w['word']!r:20s} {w['start']:.2f}s - {w['end']:.2f}s")
