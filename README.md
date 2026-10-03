# 🎤 AIKaraoke Resolve

> Bouncing ball karaoke plugin for DaVinci Resolve with **Whisper AI** voice synchronization.

![AIKaraoke Resolve Demo](examples/demo_preview.gif)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![DaVinci Resolve 18+](https://img.shields.io/badge/DaVinci%20Resolve-18%2B-orange.svg)](https://blackmagicdesign.com)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](docs/CONTRIBUTING.md)

---

## ✨ Features

- 🟡 **Golden bouncing ball** with comet tail effect (classic karaoke style)
- 🤖 **Whisper AI** voice analysis — automatically syncs ball to singer's voice (frame-perfect)
- 🎬 **ProRes 4444 with alpha channel** — transparent overlay on Video Track 3
- 📝 **Auto-generates SRT** subtitle file with real voice timestamps
- 🎨 Configurable ball size, tail length, and glow intensity
- 🖥️ Windows & macOS compatible

---

## 🚀 Quick Start

### Requirements
- DaVinci Resolve 18+ (Free or Studio)
- Python 3.8+
- ffmpeg (in PATH)

### Installation

**Windows:**
```bat
install.bat
```

**Mac / Linux:**
```bash
chmod +x install.sh && ./install.sh
```

### Usage

1. Open DaVinci Resolve
2. Go to **Workspace → Scripts → AIKaraoke Resolve**
3. Select your audio file (WAV/MP3)
4. Click **"Analyze Voice"** → Whisper AI detects every word
5. Click **"Generate Ball + SRT"** → renders the bouncing ball video
6. The ball is automatically placed on **Video Track 3** with alpha transparency
7. Import the generated SRT for synchronized subtitles

---

## 📁 Project Structure

```
AIKaraoke Resolve/
├── scripts/
│   ├── aikaraoke_main.py        # Main script (DaVinci Resolve menu)
│   ├── whisper_align.py         # Whisper AI voice word-level analysis
│   ├── build_ball.py            # Bouncing ball ProRes 4444 renderer
│   └── resolve_integration.py  # DaVinci Resolve API integration
├── docs/
│   └── CONTRIBUTING.md          # How to contribute
├── examples/
│   └── demo_preview.gif         # Demo animation
├── requirements.txt
├── install.bat                  # Windows installer
├── install.sh                   # Mac/Linux installer
└── README.md
```

---

## 🛠️ How It Works

```
Audio WAV
    │
    ▼
Whisper AI ──► Word-level timestamps (every word: start/end in seconds)
    │
    ▼
DaVinci Resolve API ──► Read subtitle clip positions from timeline
    │
    ▼
Ball Renderer ──► ProRes 4444 RGBA (transparent background)
    │            • Golden ball with glow layers
    │            • Parabolic bounce per word
    │            • Comet tail with fade history
    ▼
Video Track 3 ──► Overlaid on your main video (alpha composite)
    │
    ▼
SRT Generator ──► Subtitle file with exact voice timestamps
```

---

## 🗺️ Roadmap

- [ ] GUI window with PyQt5 (ball color picker, size slider)
- [ ] Multi-language support (Whisper detects 99 languages)
- [ ] Custom ball shapes (star, heart, note ♪)
- [ ] Windows `.exe` installer (no Python required)
- [ ] Mac `.dmg` installer
- [ ] Support for multiple subtitle tracks
- [ ] Real-time preview inside Resolve

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

**Good first issues:**
- Add GUI window (PyQt5)
- Test on macOS
- Add more ball color presets
- Write unit tests

---

## 📄 License

MIT License — free for personal and commercial use. See [LICENSE](LICENSE).

---

## 🙏 Credits

- [OpenAI Whisper](https://github.com/openai/whisper) — voice analysis AI
- [DaVinci Resolve Scripting API](https://www.blackmagicdesign.com/products/davinciresolve) — timeline integration
- [FFmpeg](https://ffmpeg.org) — ProRes 4444 video encoding
- [Pillow](https://python-pillow.org) — frame rendering

---

*Made with ❤️ for the video editing community*
