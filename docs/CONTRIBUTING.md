# Contributing to AIKaraoke Resolve

Thank you for your interest in contributing! 🎉

---

## 🐛 Reporting Bugs

1. Check [existing issues](../../issues) first
2. Create a new issue with:
   - DaVinci Resolve version
   - Python version (`python --version`)
   - Operating system
   - Full error message / traceback
   - Steps to reproduce

---

## 💡 Suggesting Features

Open an issue with the label **`enhancement`** and describe:
- What the feature does
- Why it would be useful
- Any implementation ideas

---

## 🔧 Submitting Code (Pull Requests)

### Setup
```bash
git clone https://github.com/YOUR_USERNAME/AIKaraoke-Resolve.git
cd AIKaraoke-Resolve
pip install -r requirements.txt
```

### Workflow
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Test with DaVinci Resolve open
5. Commit: `git commit -m "feat: describe your change"`
6. Push: `git push origin feature/your-feature-name`
7. Open a Pull Request

### Commit Convention
We use [Conventional Commits](https://conventionalcommits.org):

| Prefix | Use for |
|--------|---------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code restructure (no new features) |
| `test:` | Adding tests |
| `chore:` | Build, deps, tools |

---

## 🗺️ Good First Issues

| Issue | Difficulty |
|-------|------------|
| Add PyQt5 GUI window | Medium |
| Test on macOS | Easy |
| Add more ball color presets | Easy |
| Support MP3 audio input | Easy |
| Write unit tests for build_ball.py | Medium |
| Create `.exe` installer with PyInstaller | Hard |
| Add `faster-whisper` support for speed | Medium |

---

## 📁 Code Structure

```
scripts/
├── aikaraoke_main.py       # Entry point — edit CONFIG here
├── whisper_align.py        # Voice analysis (Whisper AI)
├── build_ball.py           # Video renderer (PIL + ffmpeg)
└── resolve_integration.py  # DaVinci Resolve API calls
```

**Key design decisions:**
- `whisper_align.py` is independent — can be tested without Resolve
- `build_ball.py` is independent — can be tested without Resolve
- `resolve_integration.py` requires Resolve to be running
- Word timestamps use **absolute frames** internally (based on timeline start frame)

---

## ✅ Code Style

- Python 3.8+ compatible
- Type hints on all public functions
- Docstrings on all public functions and modules
- No hardcoded paths — use `os.path` and config variables
- Keep functions small and focused (single responsibility)

---

*Questions? Open an issue or start a Discussion on GitHub.*
