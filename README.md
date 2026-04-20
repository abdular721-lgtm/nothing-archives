# Nothing Archives

Termux scripts and tooling for Nothing Phone 2a (rooted, unlocked bootloader).

Offline voice control for alarms, app launching, and YouTube search — all powered by whisper.cpp running locally on-device. No internet needed after setup, no Google STT dependency.

## Scripts

### `voice-alarm`
Voice-controlled alarm setter. Captures speech via `whisper-listen`, parses with Python, and sets an alarm in the stock Clock app via `android.intent.action.SET_ALARM`.

Handles phrases like:
- "wake me at 7 AM"
- "set alarm for 6:30"
- "set the alarm for 8am tomorrow"
- "seven thirty am"

Retries up to 3 times. Fast-fails cleanly when speech is unparseable.

### `voice-open`
Voice-controlled app launcher. Say an app name (e.g., "WhatsApp", "YouTube") and it launches via `am start`. Supports substring matching — "open WhatsApp" or just "WhatsApp" both work.

App registry (`APPS` associative array) is defined inline — add entries as `["keyword"]="package.name"` or `["keyword"]="package/.Activity"` for apps that need explicit activity names (like WhatsApp).

### `voice-youtube`
Voice-controlled YouTube search. Opens YouTube directly to results page for whatever you say. Uses `android.intent.action.VIEW` with a youtube.com URL, which YouTube's app intercepts natively.

Strips common prefixes ("play", "search for", "open youtube and play", "watch", etc.) so natural phrasing works.

### `whisper-listen`
Offline speech-to-text wrapper around whisper.cpp. Records for a fixed duration (default 5s), converts to 16kHz mono WAV via ffmpeg, transcribes with `ggml-tiny.en.bin`, strips Whisper's hallucinated tags (`[inaudible]`, `(speaking in foreign language)`, etc.).

Drop-in STT primitive used by all the voice-* scripts. Call directly as `whisper-listen 7` for a 7-second listen window.

### `parse_alarm.py`
Helper used by `voice-alarm`. Parses natural-language time expressions — word numbers ("seven thirty"), digit+meridiem ("7am"), HH:MM ("6:30"), AM/PM variants, morning/evening hints — into `HOUR|MINUTE|LABEL` format.

## Requirements

- Termux (F-Droid build — the Play Store version is outdated)
- Termux:API app (F-Droid) + `pkg install termux-api`
- Termux:Widget (F-Droid) for home-screen triggers (optional)
- `pkg install python ffmpeg cmake build-essential git`
- whisper.cpp compiled at `~/whisper.cpp` with `ggml-tiny.en.bin` model
- Microphone permission granted to Termux **and** Termux:API

## Install

```bash
# Clone
git clone https://github.com/abdular721-lgtm/nothing-archives.git
cd nothing-archives

# Install Termux deps
pkg install python ffmpeg cmake build-essential git termux-api

# Build whisper.cpp
cd ~
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
cmake -B build
cmake --build build -j --config Release
bash ./models/download-ggml-model.sh tiny.en

# Install scripts
cd ~/projects/nothing-archives
mkdir -p ~/bin
cp scripts/* ~/bin/
chmod +x ~/bin/voice-alarm ~/bin/voice-open ~/bin/voice-youtube ~/bin/whisper-listen ~/bin/parse_alarm.py
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
