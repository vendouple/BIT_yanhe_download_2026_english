# Yanhe Classroom Downloader (BIT_yanhe_download_2026)

This fork provides an English user interface while keeping the upstream
Chinese source strings as the fallback for anything not translated yet.

The GitHub Actions workflow in `.github/workflows/upstream-build.yml` checks
the upstream repository weekly and on every push. It merges upstream changes,
adds any new Chinese UI strings to `locales/en.json` without changing existing
translations, commits the result, and builds both Windows editions as an
artifact. Fill in blank catalog values when upstream adds new UI text; those
new strings intentionally remain Chinese until translated.

> **End-to-end, zero-dependency, dual-edition release**
>
> A downloader for recorded videos from Beijing Institute of Technology's
> "Yanhe Classroom", deeply optimized for VPN / campus-network environments
> with high packet loss. This repository is a refactor of
> [AuYang261/BIT_yanhe_download](https://github.com/AuYang261/BIT_yanhe_download).

![GUI](https://github.com/lankerr/BIT_yanhe_download_2026/raw/main/assets/screenshot.png)

---

## 🚀 Two editions, pick what you need

| Edition | Executable | Size | Features | Best for |
|---------|-----------|------|----------|----------|
| **Simple** | `延河课堂下载器-简易版.exe` | ~80 MB | Course video download (including MP4 merging) | Just watching replays, saving disk space |
| **Full** | `延河课堂下载器-完整版.exe` | ~500 MB | Download + **smart PPT extraction** + **audio transcription (Whisper GPU)** | Taking notes / courseware / subtitles |

Both are **single-file executables** bundled with the Python runtime and FFmpeg —
unzip and double-click to run.

> 💡 **GPU users**: For the full edition's speech transcription, running on a
> machine with **NVIDIA CUDA 12.x + cuDNN 9** is recommended for 30–50×
> real-time transcription speed. Without a GPU it automatically falls back to
> CPU + int8, but `large-v3` is quite slow on CPU — consider using `medium`
> or `small` instead.

---

## 📦 Get a release

Download the edition you need from
[Releases](https://github.com/lankerr/BIT_yanhe_download_2026/releases).

First-time use:
1. Log in to [Yanhe Classroom](https://www.yanhekt.cn) in your browser → press `F12` to open the console
2. Paste `javascript:alert(JSON.parse(localStorage.auth).token)` and press Enter, then copy the 32-character token from the popup
3. Launch the exe, paste the token + enter the 5-digit course ID (from `yanhekt.cn/course/****`) → click **Get course list**
4. Select the chapters you want → click **Start download**

---

## ✅ Verified working as of 2026-05-22

As of **2026-05-22**, this downloader still works with the current Yanhe
Classroom. An end-to-end test was completed with course `67092`
(Advanced Aerial Target Detection, Prof. Wang Rui):

- Video download succeeded: all 297 HLS segments downloaded and merged into an MP4 of about 776.7 MB.
- Full-edition post-processing succeeded: extracted 59 PPT slides, produced a TXT transcript of 2,448 segments, and generated matching SRT subtitles.
- Both executables were rebuilt and smoke-tested: Simple ~182.1 MB, Full ~295.5 MB, both with bundled `ffmpeg.exe` / `ffprobe.exe`.

See [docs/TEST_REPORT_2026.md](docs/TEST_REPORT_2026.md) for the full record.

---

## 🧠 Core technology

### 1. Fixed-concurrency engine (v3)
After full-range testing (`docs/speed_stage4_fullseg.md`), the original AIMD
adaptive concurrency was removed in favor of a fixed thread pool (default
K=16, the saturation point measured on the Yanhe CDN). On the same network it
is a stable 33–35% faster than the old AIMD engine and no longer suffers from
"tail stall / death spiral" behavior.

### 2. Two-phase download + missing-segment recovery
Phase 1 pulls all segments at fixed concurrency; failures go into a deferred
queue. Phase 2 retries missing segments serially with exponential backoff
(0.5s → 1s → 2s …). The `_success_sum` counter is lock-protected, eliminating
the multithreaded "stuck at 99%" infinite loop. Before merging, a reconciliation
step normally fills all 297 segments; under extreme network conditions it
allows ≤5% missing segments as a fallback merge with a clear warning, so one
or two unrecoverable segments no longer fail the entire session. The watchdog
is retained but demoted to a true-hang fallback (180s with no progress) and no
longer drives the flow.

### 3. Embedded FFmpeg
During packaging, `fetch_ffmpeg.py` embeds `ffmpeg.exe` / `ffprobe.exe` into
the exe; at runtime they are loaded from `_MEIPASS` — **truly zero external
dependencies**.

### 4. Smart PPT extraction (Full edition)
`FFmpeg scene` filter detects major frame changes → timestamp filtering → pHash
deduplication → outputs JPG + PPTX, at roughly 50× real time.

### 5. Audio transcription (Full edition)
`faster-whisper` (CTranslate2) with automatic GPU `float16` / CPU `int8`
selection; models are pulled from `hf-mirror.com` by default to avoid
huggingface.co being unreachable.

### 6. Automatic direct connection for VPN/proxy environments
Yanhe API, m3u8, ts segments, and audio downloads all use direct sessions that
ignore the system proxy, reducing 403 errors, ProxyError, and long hangs caused
by VPNs, system proxies, and transparent proxies. You can keep your VPN on for
other work — the downloader will try to bypass the system proxy and connect
directly to Yanhe domains.

### 7. Chunked transcription for long lectures
Audio longer than 30 minutes is automatically split into ~20-minute chunks,
transcribed separately, then merged back onto the original video timeline —
avoiding out-of-memory failures when feeding 90+ minute courses into Whisper
in one pass.

---

## 🛠 Build it yourself

### Requirements
- Python 3.9 – 3.12
- Windows 10+ (the spec files need adjustment for other platforms)

### Steps

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Prepare ffmpeg / ffprobe (copied automatically if on PATH)
python fetch_ffmpeg.py

# 3a. Build Simple edition (~80MB)
build_simple.bat

# 3b. Build Full edition (~500MB; pip install faster-whisper etc. first)
build_full.bat
```

Outputs: `dist\延河课堂下载器-简易版.exe` / `dist\延河课堂下载器-完整版.exe`

> ⚠️ For the Full edition to run on GPU directly inside the exe, the build
> machine must first run `pip install torch --index-url https://download.pytorch.org/whl/cu121`,
> otherwise `torch.cuda.is_available()` will return False when the exe starts.

---

## 📁 Repository structure

```
.
├── app_simple.py              # Simple edition entry point
├── app_full.py                # Full edition entry point
├── app_paths.py               # Unified paths / edition / ffmpeg lookup
├── gui_app.py                 # Main GUI (CustomTkinter)
├── i18n.py                    # Runtime English localization layer
├── locales/en.json            # English translation catalog
├── m3u8dl.py                  # Fixed-concurrency download engine + HLS merging
├── utils.py                   # Signing / course list / authentication
├── ppt_extractor_gpu.py       # Courseware extraction (Full edition)
├── audio_transcriber_gpu.py   # Whisper transcription (Full edition)
├── batch_process.py           # Post-processing batch orchestration
├── fetch_ffmpeg.py            # Pre-packaging ffmpeg preparation
├── scripts/update_translations.py  # Translation catalog updater
├── .github/workflows/upstream-build.yml  # Weekly upstream sync + build
├── 延河课堂下载器-简易版.spec
├── 延河课堂下载器-完整版.spec
├── build_simple.bat
├── build_full.bat
├── requirements.txt
└── scripts/legacy/            # Historical / experimental scripts (not packaged)
```

---

## 📜 Changelog

### v2026.05.29 – Download engine v3 (AIMD removed, fixed concurrency)
- **Refactored**: The download engine moved from AIMD adaptive concurrency to a
  **fixed thread pool**. Per `docs/speed_stage4_fullseg.md`, three full-range
  (297-segment) test rounds showed a stable **33–35% speedup** on the same
  network under interleaved comparison; after backporting, the new production
  engine regressed the full range at 405.7s / 1.91 MB/s with 297/297 success
  and 0 missing segments.
- **Fixed**: Eliminated the AIMD "death spiral" — the old engine always entered
  "tail mode" on full-range runs with weak-network throughput collapsing to
  0.86 MB/s; the new engine never triggers tail mode / the watchdog.
- **Fixed**: Added locking to the `_success_sum` counter, eliminating the
  multithreaded "stuck at 99%" bug.
- **Refactored**: Two-phase download (phase 1 concurrent bulk pull + phase 2
  serial exponential-backoff repair of missing segments) replaced three
  mutually overriding tail-mode code paths.
- **Changed**: The watchdog was demoted to a true-hang fallback (180s with no
  progress) and no longer drives the download flow.
- **Changed**: GUI default concurrency 32 → **16** (full-range saturation point),
  limit 64 → 32.

### v2.0.0 (2026-05) – Dual-edition release
- **Fixed**: Adapted to the 2026 Yanhe HLS path signature, updated from the old `_100` to the current `_200`
- **Fixed**: Yanhe API / video segment requests now bypass the system proxy by default, reducing VPN/proxy-caused 403s, timeouts, and hangs
- **Fixed**: Long-form transcription now auto-chunks, solving out-of-memory issues when transcribing 90+ minute courses in a single Whisper pass
- **Added**: Simple / Full dual-exe release format
- **Added**: FFmpeg / FFprobe embedded at build time, zero external dependencies
- **Added**: Full edition auto-detects the GPU and sets default device / compute_type
- **Refactored**: `app_paths.py` unifies resource paths and edition identifiers
- **Cleanup**: Experimental scripts moved to `scripts/legacy/`

### v1.2.0 (2026-02) – Tail optimization
- Tail Mode: bypasses the AIMD slot limit when fewer than 8 files remain
- Stall Detection: forces tail mode after 30 seconds with no progress
- GUI switched from direct `after()` calls to a Queue, completely fixing GUI freezes
- Fixed exe path issues (`auth.txt` / `output`) and FFmpeg popup windows

### v1.1.0 (2026-01) – GUI refactor
- CustomTkinter "geek black" theme
- Integrated AIMD adaptive flow control

### v1.0.0
- Based on AuYang261's original version

---

## 🙏 Acknowledgments

- Original project author [AuYang261](https://github.com/AuYang261) (a good friend from the Cyberspace Security School, now recommended for graduate study at Peking University)
- [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) – CTranslate2 Whisper
- [Gyan.Dev FFmpeg builds](https://www.gyan.dev/ffmpeg/builds/) – Windows FFmpeg binaries

This project is for technical learning and exchange only. Users must comply
with applicable laws, regulations, and university policies. **Commercial use
and infringement of others' intellectual property rights are strictly
prohibited.**

License: MIT
