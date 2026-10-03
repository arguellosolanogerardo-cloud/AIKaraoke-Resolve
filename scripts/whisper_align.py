"""
whisper_align.py
-----------------
Whisper AI voice analysis module.
Extracts word-level timestamps from an audio file.

Runs in an isolated Python subprocess to avoid host application (Resolve) DLL conflicts.
"""

import os
import sys
import json
import subprocess


def _find_system_python() -> str:
    """Finds the best available standalone Python executable on the system."""
    candidates = [
        r"C:\Users\INGENIERO\AppData\Local\Programs\Python\Python313\python.exe",
        r"C:\Users\INGENIERO\AppData\Local\Programs\Python\Python311\python.exe",
        r"C:\Users\INGENIERO\AppData\Local\Programs\Python\Python314\python.exe",
        "python",
        "python3"
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return "python"


def _find_whisper_script() -> str:
    """Locates the absolute path to this whisper_align.py script."""
    candidates = [
        r"E:\DEVELOPER\AI\FACTORY SOFTWARE\TESTING\AIKaraoke Resolve\scripts\whisper_align.py",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "whisper_align.py") if "__file__" in globals() else "",
        os.path.join(os.path.expandvars(r"%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Edit"), "whisper_align.py"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return "whisper_align.py"


def _run_transcribe_internal(audio_path: str, model_name: str, language: str, output_dir: str) -> list:
    """Performs transcription directly using whisper library."""
    import whisper

    print(f"  Loading Whisper model: '{model_name}'...")
    model = whisper.load_model(model_name)

    print(f"  Transcribing audio with Whisper AI (language='{language}')...")
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        verbose=False
    )

    word_timestamps = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            word_timestamps.append({
                "word":  word_info["word"].strip(),
                "start": round(word_info["start"], 3),
                "end":   round(word_info["end"], 3),
            })

    cache_file = os.path.join(output_dir, "whisper_word_timestamps.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(word_timestamps, f, ensure_ascii=False, indent=2)

    print(f"  Saved {len(word_timestamps)} word timestamps to {cache_file}")
    return word_timestamps


def analyze_voice(audio_path: str, model_name: str = "base",
                  language: str = "es", output_dir: str = ".") -> list:
    """
    Analyze an audio file with Whisper AI and extract word-level timestamps.
    Automatically isolates Whisper in a subprocess to avoid DLL conflicts with DaVinci Resolve.
    """
    cache_file = os.path.join(output_dir, "whisper_word_timestamps.json")

    # Use cached results if available
    if os.path.exists(cache_file):
        print(f"  Loading cached Whisper results from {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # Run via isolated subprocess using Python 3.13 or system python
    script_path = _find_whisper_script()
    python_exe = _find_system_python()

    print(f"  Launching Whisper AI via {os.path.basename(python_exe)}...")
    cmd = [
        python_exe,
        script_path,
        audio_path,
        model_name,
        language,
        output_dir
    ]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.run(cmd, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"Whisper subprocess failed with exit code {proc.returncode}")

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise RuntimeError(f"Whisper voice analysis completed but {cache_file} was not found.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python whisper_align.py <audio_file> [model] [language] [output_dir]")
        sys.exit(1)

    _audio = sys.argv[1]
    _model = sys.argv[2] if len(sys.argv) > 2 else "base"
    _lang  = sys.argv[3] if len(sys.argv) > 3 else "es"
    _out   = sys.argv[4] if len(sys.argv) > 4 else "."

    _run_transcribe_internal(_audio, _model, _lang, _out)
