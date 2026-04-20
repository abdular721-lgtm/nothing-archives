# Nothing Archives

Termux scripts and tooling for Nothing Phone 2a (rooted, unlocked bootloader).

Offline voice control for alarms, app launching, YouTube search, system toggles, screenshots, notes, notifications, phone calls, SMS/RCS messaging, weather, reminders, and lifestyle macros — all powered by whisper.cpp running locally on-device. No internet needed after setup (except weather), no Google STT dependency.

## Scripts

### `voice` (unified router)
Single entry point for all voice commands. Listens once via `whisper-listen 5`, then routes based on keywords:
- "goodnight / morning / commute / focus / presentation / normal mode" → `voice-macro`
- "call / phone / ring / dial / hang up" → `voice-call`
- "send message / text / sms / read message / rcs" → `voice-sms`
- "remind me / reminder / don't forget" → `voice-reminder`
- "weather / forecast / umbrella / how hot" → `voice-weather`
- "alarm / wake me / set alarm" → `voice-alarm`
- "youtube / play video" → `voice-youtube`
- "open / launch / start [app]" → `voice-open`
- "screenshot" → `voice-screenshot`
- "wifi / bluetooth / volume / brightness / DND / dark mode..." → `voice-toggle`
- "time / battery / storage / IP / signal..." → `voice-info`
- "read notifications / whatsapp" → `voice-read-notif`
- "note / remember / write down" → `voice-note`
- "search note / find note" → `voice-note-search`
- "list notes / show notes" → `voice-note-list`

All sub-scripts accept pre-captured text as `$1` so the router doesn't re-listen.

### `voice-macro`
Multi-step lifestyle macros triggered by voice:
- **Goodnight** — DND on, Bluetooth off, asks about Wi-Fi, brightness min, asks for alarm time, screen off
- **Good morning** — DND off, auto brightness, reads time/battery/Wi-Fi/notification count
- **Commute** — mobile data on, Bluetooth on, volume max, opens Maps
- **Focus** — DND on, data off, volumes muted, screen timeout 60s
- **Presentation** — brightness max, rotation off, DND on, volume muted
- **Normal mode** — resets all: DND off, auto brightness, rotation on, volume 8, data on

### `voice-call`
Voice-controlled phone calls. Looks up contacts via `termux-contact-list` with fuzzy matching. Dials via `android.intent.action.CALL`. Hang up via `input keyevent 6`.

### `voice-sms`
Voice-controlled SMS/RCS messaging. Tries RCS (Google Messages bugle_db) first, falls back to traditional SMS via `termux-sms-list`. Send messages with voice confirmation before dispatch.

### `voice-rcs`
Standalone RCS reader. Queries Google Messages' bugle_db (copies to temp to avoid lock conflicts). Falls back to conversation snippets if parts table is empty.

### `voice-weather`
Weather readout using wttr.in API (Faisalabad default). Supports:
- General: current temp, description, humidity, wind, today's high/low
- Tomorrow: forecast with rain probability
- Rain/umbrella: precipitation check
- Temperature: current + feels like
- Wind: wind speed

### `voice-reminder`
Voice-controlled reminder system. Supports:
- Relative time: "remind me in 20 minutes to take medication"
- Absolute time: "remind me at 3pm to call the doctor"
- List reminders: "what are my reminders"
- Cancel: "cancel all reminders"

Fires via background `sleep` + `termux-notification` + TTS. Reminders tracked in `~/notes/reminders.json`.

### `voice-alarm`
Voice-controlled alarm setter. Parses with Python, sets via `android.intent.action.SET_ALARM`. Handles "wake me at 7 AM", "set alarm for 6:30", "seven thirty am".

### `voice-open`
Voice-controlled app launcher via `am start`. Supports substring matching.

### `voice-youtube`
Voice-controlled YouTube search. Opens YouTube directly to results page.

### `voice-screenshot`
Takes a screenshot via `screencap`, saves to `/sdcard/Download/`, registers with MediaStore for Gallery visibility.

### `voice-toggle`
Voice-controlled system toggles:
- **Wi-Fi** on/off — `cmd -w wifi set-wifi-enabled`
- **Bluetooth** on/off — `cmd bluetooth_manager`
- **Mobile data** on/off — `cmd phone data`
- **Airplane mode** on/off — `cmd connectivity airplane-mode`
- **Flashlight** on/off — `termux-torch`
- **Volume** up/down/mute/max (media, ring, notification, alarm streams) — `cmd media_session volume`
- **Brightness** up/down/min/max/percent/auto — `settings put system screen_brightness`
- **DND** on/off — `cmd notification set_dnd`
- **Dark mode** on/off — `cmd uimode night`

### `voice-info`
System information readouts: time, date, battery, storage, IP address, Wi-Fi SSID, signal strength.

### `voice-read-notif`
Reads latest WhatsApp/all notifications aloud via TTS. Requires Termux:API notification access.

### `voice-note` / `voice-note-list` / `voice-note-search`
Voice-dictated notes saved as Markdown in `~/notes/`. Search and list commands included.

### `whisper-listen`
Offline STT wrapper around whisper.cpp. Records for a fixed duration (default 5s), converts to 16kHz mono WAV via ffmpeg, transcribes with **ggml-base.en** model. Override with `WHISPER_MODEL=tiny.en` for faster (but less accurate) transcription.

### `parse_alarm.py`
Helper for `voice-alarm` and `voice-reminder`. Parses natural-language time expressions into `HOUR|MINUTE|LABEL` format.

## Requirements

- Termux (F-Droid build)
- Termux:API app (F-Droid) + `pkg install termux-api`
- Termux:Widget (F-Droid) for home-screen triggers (optional)
- `pkg install python ffmpeg cmake build-essential git sqlite-utils`
- whisper.cpp compiled at `~/whisper.cpp` with model
- Microphone, SMS, Contacts, Phone permissions granted to Termux:API
- Notification access granted to Termux:API (for `voice-read-notif`)
- Magisk root (for toggles, macros, screenshot, RCS reading)

## Install

```bash
# Clone
git clone https://github.com/abdular721-lgtm/nothing-archives.git
cd nothing-archives

# Install Termux deps
pkg install python ffmpeg cmake build-essential git termux-api sqlite-utils

# Build whisper.cpp
cd ~
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
cmake -B build
cmake --build build -j --config Release
# base.en: better accuracy, ~5.4s transcription on Dimensity 7200 Pro
bash ./models/download-ggml-model.sh base.en
# Optional: tiny.en for faster (~2.7s) but less accurate transcription
# bash ./models/download-ggml-model.sh tiny.en

# Install scripts
cd ~/projects/nothing-archives
mkdir -p ~/bin ~/notes
cp scripts/* ~/bin/
chmod +x ~/bin/voice* ~/bin/whisper-listen ~/bin/parse_alarm.py
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Permissions (run each, accept prompts)
# pm grant com.termux.api android.permission.READ_SMS
# pm grant com.termux.api android.permission.SEND_SMS
# pm grant com.termux.api android.permission.READ_CONTACTS
# pm grant com.termux.api android.permission.CALL_PHONE
```

## Doze / Background Protection

Nothing OS aggressively kills background processes. Run these to keep Termux alive:

```bash
termux-wake-lock
su shell -c "dumpsys deviceidle whitelist +com.termux"
su shell -c "dumpsys deviceidle whitelist +com.termux.api"
su shell -c "cmd appops set com.termux RUN_IN_BACKGROUND allow"
```

## Widget Setup

Symlinks in `~/.shortcuts/` point to scripts in `~/bin/`. Add a Termux:Widget to your home screen to trigger any voice command with one tap.

## Nothing OS Quirks

- `su -c "am ..."` fails with "Failed transaction (2147483646)" — use `su shell -c` instead (drops to shell uid 2000)
- Media scanner broadcast needs `su shell -c` as well
- Bluetooth uses `cmd bluetooth_manager` not `service call` (transaction codes differ on Android 14)
- Airplane mode uses `cmd connectivity airplane-mode` (broadcast requires privileged uid)
- `termux-tts-speak` is synchronous and shifts foreground focus, which can trigger OOM kills on background processes
- Google Messages stores RCS in bugle_db — must copy to temp before querying to avoid lock conflicts
