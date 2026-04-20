# Nothing Archives

Termux scripts and tooling for Nothing Phone 2a (rooted, unlocked bootloader).

Offline voice control for alarms, app launching, YouTube search, system toggles, screenshots, notes, and notifications — all powered by whisper.cpp running locally on-device. No internet needed after setup, no Google STT dependency.

## Scripts

### `voice` (unified router)
Single entry point for all voice commands. Listens once via `whisper-listen 5`, then routes based on keywords:
- "alarm / wake me / set alarm" → `voice-alarm`
- "open / launch / start [app]" → `voice-open`
- "youtube / play video" → `voice-youtube`
- "screenshot" → `voice-screenshot`
- "wifi / bluetooth / data / airplane / flashlight + on/off" → `voice-toggle`
- "read notifications / whatsapp" → `voice-read-notif`
- "note / remember / write down" → `voice-note`
- "search note / find note" → `voice-note-search`
- "list notes / show notes" → `voice-note-list`

All sub-scripts accept pre-captured text as `$1` so the router doesn't re-listen.

### `voice-alarm`
Voice-controlled alarm setter. Captures speech via `whisper-listen`, parses with Python, and sets an alarm in the stock Clock app via `android.intent.action.SET_ALARM`.

Handles phrases like: "wake me at 7 AM", "set alarm for 6:30", "seven thirty am". Retries up to 3 times.

### `voice-open`
Voice-controlled app launcher. Say an app name (e.g., "WhatsApp", "YouTube") and it launches via `am start`. Supports substring matching — "open WhatsApp" or just "WhatsApp" both work.

### `voice-youtube`
Voice-controlled YouTube search. Opens YouTube directly to results page. Strips common prefixes ("play", "search for", "watch", etc.) so natural phrasing works.

### `voice-screenshot`
Takes a screenshot via `screencap` and saves to `/sdcard/Download/`. Registers with MediaStore so files appear in Gallery/Google Photos immediately.

### `voice-toggle`
Voice-controlled system toggles. Supports:
- **Wi-Fi** on/off/toggle — via `cmd -w wifi set-wifi-enabled`
- **Bluetooth** on/off/toggle — via `cmd bluetooth_manager enable/disable`
- **Mobile data** on/off/toggle — via `cmd phone data enable/disable`
- **Airplane mode** on/off/toggle — via `cmd connectivity airplane-mode`
- **Flashlight** on/off — via `termux-torch`

All Android framework commands use `su shell -c` (uid 2000) to avoid the "Failed transaction" issue on Nothing OS 2.5+.

### `voice-read-notif`
Reads the latest WhatsApp notification aloud via `termux-tts-speak`. Uses `termux-notification-list` to fetch active notifications. Requires Termux:API notification access.

### `voice-note`
Voice-dictated note taker. Prompts for a 5-second title, then up to 60 seconds of content. Saves as Markdown in `~/notes/` named `YYYY-MM-DD_HH-MM_slug.md`.

### `voice-note-list`
Lists all notes in `~/notes/`, newest first, showing filename and title.

### `voice-note-search`
Voice-search across all notes. Greps all `.md` files case-insensitively and prints matching filenames, titles, and context lines.

### `whisper-listen`
Offline STT wrapper around whisper.cpp. Records for a fixed duration (default 5s), converts to 16kHz mono WAV via ffmpeg, transcribes with `ggml-tiny.en.bin`, strips hallucinated tags.

### `parse_alarm.py`
Helper used by `voice-alarm`. Parses natural-language time expressions into `HOUR|MINUTE|LABEL` format.

## Requirements

- Termux (F-Droid build)
- Termux:API app (F-Droid) + `pkg install termux-api`
- Termux:Widget (F-Droid) for home-screen triggers (optional)
- `pkg install python ffmpeg cmake build-essential git`
- whisper.cpp compiled at `~/whisper.cpp` with `ggml-tiny.en.bin` model
- Microphone permission granted to Termux **and** Termux:API
- Notification access granted to Termux:API (for `voice-read-notif`)
- Magisk root (for `voice-screenshot` and `voice-toggle`)

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
chmod +x ~/bin/voice* ~/bin/whisper-listen ~/bin/parse_alarm.py
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Widget Setup

Symlinks in `~/.shortcuts/` point to scripts in `~/bin/`. Add a Termux:Widget to your home screen to trigger any voice command with one tap.

## Nothing OS Quirks

- `su -c "am ..."` fails with "Failed transaction (2147483646)" — use `su shell -c` instead (drops to shell uid 2000)
- Media scanner broadcast needs `su shell -c` as well
- Bluetooth uses `cmd bluetooth_manager` not `service call` (transaction codes differ on Android 14)
- Airplane mode uses `cmd connectivity airplane-mode` (broadcast requires privileged uid)
- `termux-wake-lock` recommended before sshd to prevent Android from killing background processes
