# Nothing Archives

Offline voice-control assistant for Nothing Phone 2a (rooted, Android 14, Nothing OS 2.5+).

## Project overview

All scripts live in `~/bin/` on the phone, backed up in `scripts/` in this repo.
Git remote: `https://github.com/abdular721-lgtm/nothing-archives`
Dev machine: Windows 11, SSH alias `nothing` (host 192.168.132.234, port 8022).

## Architecture

```
User speaks → whisper-listen (whisper.cpp, offline STT)
           → voice (unified router — keyword matching)
           → voice-* (action scripts)          [keyword match]
           → voice-claude (Claude API fallback) [no match]
           → Android APIs (am, cmd, termux-api, su shell)
```

- **Single entry point**: `~/bin/voice` (unified router)
- **STT engine**: `~/bin/whisper-listen` (whisper.cpp: tiny.en via --fast, base.en default for commands, small.en via --accurate for dictation)
- **Wake word**: `~/bin/hey-nothing` (openWakeWord daemon, hey_jarvis model, <1s latency)
- **Daemon control**: `~/bin/hey-nothing-ctl` (start/stop/status/restart)
- **TTS**: `termux-tts-speak` (synchronous, use `say()` helper)
- **Detached execution**: `~/bin/run-voice` (avoids OOM on SSH sessions)
- **Context store**: `~/bin/voice-context` (shared state, 10min TTL)
- **Claude API**: `~/bin/voice-claude` (Haiku 4.5, 16 tools, offline fallback)

## Critical device constraints

### Root command rules (MUST follow exactly)
- `su shell -c "command"` (uid 2000) — for Android service calls: `am`, `cmd`, `pm`, `settings`, `svc`, `dumpsys`, `input`
- `su -c "command"` (uid 0) — for kernel-level: `ip`, `screencap`, `sqlite3`, `cat /sys/*`
- Direct termux command — if `termux-*` API exists, use it first

### What FAILS
- `su -c "am broadcast/cmd/settings put/svc"` → **Failed transaction (2147483646)**
- `termux-speech-to-text` → unreliable, use `whisper-listen` instead
- `termux-microphone-record -e wav` → lies, actually outputs MP4. ffmpeg conversion mandatory.
- TTS over SSH → causes OOM kill on sshd. **Always use `run-voice` for testing.**
- `pvporcupine` / `precise-runner` → fail on Android bionic libc. openWakeWord works (installed via `pip install openwakeword --no-deps` + `pkg install python-onnxruntime python-scipy portaudio`)
- `sed -i` multi-line insert on Termux → collapses to single line. Use Python for multi-line edits.
- `/tmp` writes → permission denied. Use `~/` or `$HOME/.cache/`.
- `set -e` in long-running scripts → kills daemon on any non-zero sub-command. Never use in daemons.

## Script inventory (38 scripts)

### Core
| Script | Description |
|--------|-------------|
| `voice` | Unified router — listen once, route to sub-script by keyword |
| `whisper-listen` | Record + transcribe with whisper.cpp. Flags: `--fast` (tiny.en ~3s), `--accurate` (small.en ~20s), `--energy-gate N`. Default: base.en ~5-7s |
| `run-voice` | Detached script runner — prevents OOM on SSH |
| `voice-context` | Shared context store (write/read/clear/last). 10min TTL. |
| `voice-claude` | Claude API integration — intelligent fallback with 22 tool definitions, conversation memory, offline fallback |
| `assistant-watchdog` | Background watchdog — restarts dead daemons every 5 minutes, refreshes OOM protection and notifications |

### Wake word
| Script | Description |
|--------|-------------|
| `hey-nothing` | Wake word daemon — openWakeWord (hey_jarvis model), continuous inference, <1s latency, quiet hours. Python script. |
| `hey-nothing-ctl` | Daemon lifecycle: start, stop, status, restart |

### Action scripts
| Script | Description |
|--------|-------------|
| `voice-alarm` | Set alarm by voice ("7am", "wake me at 6:30") |
| `voice-briefing` | Daily summary: time, battery, weather, calendar, notifications. `--short` flag. |
| `voice-calendar` | Read calendar events or create new ones |
| `voice-call` | Dial a contact or hang up |
| `voice-home` | Smart home control (HTTP to Home Assistant/n8n). Stub mode if unconfigured. |
| `voice-info` | Device info: time, date, battery, storage, IP, signal |
| `voice-macro` | Multi-step sequences: goodnight, good morning, commute, focus, presentation |
| `voice-music` | Media control: play/pause/skip/previous/volume/now-playing/search YouTube Music |
| `voice-note` | Dictate and save a note to `~/notes/` |
| `voice-note-list` | List saved notes |
| `voice-note-search` | Search notes by keyword |
| `voice-open` | Launch apps by name |
| `voice-rcs` | RCS message reader (Google Messages bugle_db) |
| `voice-read-notif` | Read notifications aloud |
| `voice-reminder` | Set reminders (stored in `~/notes/reminders.json`) |
| `voice-screenshot` | Take and save a screenshot |
| `voice-sms` | Read or send SMS/RCS messages |
| `voice-toggle` | Toggle: wifi, bluetooth, flashlight, volume, brightness, DND, dark mode |
| `voice-weather` | Weather via OpenWeather API (if key configured) |
| `voice-whatsapp` | Reply to WhatsApp messages |
| `voice-youtube` | Search and play YouTube videos |
| `voice-journal` | Voice diary with sentiment tracking, weekly summaries via Claude |
| `voice-note-ai` | Claude-powered note search and summarisation |
| `voice-location` | Manual location queries and WiFi SSID configuration |
| `voice-location-monitor` | Background WiFi-based location daemon — triggers macros on location change |
| `voice-history` | Voice command history and usage analytics |
| `voice-settings` | Voice-controlled assistant settings (threshold, model, quiet hours, tone) |

### Utilities
| Script | Description |
|--------|-------------|
| `parse_alarm.py` | Parse natural language time expressions |
| `restore-reminders.py` | Restore reminders from JSON backup |

## Working command reference

```bash
# Android service calls (uid 2000 — su shell)
su shell -c "am start -a android.intent.action.SET_ALARM --ei android.intent.extra.alarm.HOUR 7 --ei android.intent.extra.alarm.MINUTES 0 --ez android.intent.extra.alarm.SKIP_UI true"
su shell -c "cmd media_session dispatch play|pause|next|previous|stop"
su shell -c "cmd media_session volume --stream 3 --adj raise|lower|--set N"
su shell -c "svc wifi enable|disable"
su shell -c "svc bluetooth enable|disable"
su shell -c "cmd statusbar expand-notifications"
su shell -c "settings put system screen_brightness N"  # 0-255
su shell -c "settings put global airplane_mode_on 1|0"
su shell -c "am start -a android.intent.action.VIEW -d 'https://...'"
su shell -c "input keyevent 6"  # hang up call
su shell -c "dumpsys power"  # check mWakefulness=Awake|Asleep

# Kernel-level (uid 0 — su root)
su -c "screencap -p /sdcard/screenshot.png"
su -c "cat /sys/class/power_supply/battery/capacity"
su -c "ip route show default"
su -c "sqlite3 /path/to/db 'SELECT ...'"

# Termux API
termux-microphone-record -f FILE -l DURATION -e wav
termux-microphone-record -q
termux-tts-speak "text"
termux-toast "text"
termux-notification-list
termux-contact-list
termux-sms-list -l N
termux-sms-send -n NUMBER "body"
termux-torch on|off
```

## File locations

```
~/bin/                        — all executable scripts
~/notes/                      — voice-dictated notes
~/notes/reminders.json        — active reminders
~/logs/                       — script execution logs
~/whisper.cpp/                — whisper binary and models
~/whisper.cpp/models/         — ggml-tiny.en.bin (75MB), ggml-base.en.bin (142MB), ggml-small.en.bin (466MB)
~/.cache/                     — temporary audio files
~/.voice-context.json         — conversation context (10min TTL)
~/.hey-nothing.pid            — daemon PID file
~/.hey-nothing-stats.json     — daemon statistics (JSON: cycles, triggers, start_time)
~/.hey-nothing-config         — wake word daemon tuning (threshold, cooldown, quiet hours)
~/.smart-home-config          — Home Assistant / n8n endpoints
~/.anthropic_key               — Claude API key (chmod 600)
~/.voice-claude-history.json   — Claude conversation history (10min TTL)
~/.assistant-settings.json     — Unified settings file (wake word, voice, notifications, assistant)
~/.location-config.json        — Location profiles (home/hospital WiFi SSIDs, GPS coords)
~/.location-monitor.pid        — Location monitor PID file
~/.watchdog.pid                — Watchdog PID file
~/journal/                     — Voice journal entries (one .md file per day)
~/logs/command-history.log     — Voice command history (timestamp|datetime|text|route)
~/logs/watchdog.log            — Watchdog restart log
~/.shortcuts/                 — Termux:Widget symlinks
~/.termux/boot/               — Termux:Boot startup scripts
~/projects/nothing-archives/  — this git repo
```

## Claude API Integration

- **Script**: `~/bin/voice-claude` (Python, 456 lines)
- **Model**: claude-haiku-4-5-20251001 (fastest, cheapest — ideal for voice)
- **API key**: `~/.anthropic_key` (chmod 600, never committed)
- **Conversation history**: `~/.voice-claude-history.json` (10min TTL, last 10 turns)
- **Fallback**: offline voice router if no network or API error
- **Tools**: 22 tools mapping to existing voice-* scripts
- **System prompt**: personalized (ED doctor, app developer, Grimsby)
- **Latency**: ~2s for direct answers, ~5s for tool calls (includes follow-up)

### How it works
1. Voice router tries keyword matching first (fast, offline, free)
2. If no keyword matches → `voice-claude` sends text to Claude API
3. Claude either answers directly (questions) or calls tools (actions)
4. Tool calls execute existing voice-* scripts via subprocess
5. Claude provides follow-up confirmation after tool execution
6. If no internet → falls back to offline voice router

### Tools available to Claude
set_alarm, open_app, search_youtube, play_music, toggle_setting, set_reminder,
get_weather, take_screenshot, make_call, send_sms, read_notifications,
get_system_info, run_macro, save_note, get_calendar, daily_briefing


## Stability & Background Processes

### Battery optimization
- Termux + Termux:API whitelisted from battery optimization
- AppOps: RUN_IN_BACKGROUND, WAKE_LOCK, RUN_ANY_IN_BACKGROUND
- WiFi sleep policy: never (wifi_sleep_policy=2, wifi_idle_ms=max)

### Process protection
- `termux-wake-lock` acquired on boot (02-wakelock.sh)
- Ongoing foreground notification ("Voice Assistant Active")
- OOM score adj set to -1000 for Termux process
- Watchdog daemon checks every 5 minutes, restarts dead processes

### Managed daemons
| Daemon | PID file | Boot script |
|--------|----------|-------------|
| hey-nothing (wake word) | ~/.hey-nothing.pid | 05-hey-nothing.sh |
| shift-monitor | ~/.shift-monitor.pid | 06-shift-monitor.sh |
| location-monitor | ~/.location-monitor.pid | 08-location-monitor.sh |
| assistant-watchdog | ~/.watchdog.pid | 07-watchdog.sh |

### SSH keepalive
- sshd: ClientAliveInterval=60, ClientAliveCountMax=10
- Client: ServerAliveInterval=60, ServerAliveCountMax=10, TCPKeepAlive=yes
## Development workflow

```bash
# Edit a script
ssh nothing "nano ~/bin/script-name"
# or edit locally and SCP
scp script-name nothing:~/bin/script-name

# Test (ALWAYS use run-voice for SSH testing)
ssh nothing "~/bin/run-voice ~/bin/script-name 'argument'"

# Check log
ssh nothing "tail -20 ~/logs/script-name-*.log"

# Copy to repo
ssh nothing "cp ~/bin/script-name ~/projects/nothing-archives/scripts/"

# Commit
ssh nothing "cd ~/projects/nothing-archives && git add . && git commit -m 'message' && git push"
```

## Known issues and workarounds

1. **TTS causes SSH OOM**: `termux-tts-speak` triggers Android OOM killer on sshd. Workaround: always use `run-voice` for testing. Scripts work fine via widget/wake word.

2. **Whisper hallucinations**: On silence, tiny.en generates plausible English ("are you here?", "[BLANK_AUDIO]"). Harmless for wake word (never matches trigger phrases). Filtered by sed regex in whisper-listen.

3. **termux-microphone-record lies about format**: `-e wav` flag is ignored, output is always MP4. ffmpeg conversion to 16kHz mono WAV is mandatory before whisper.

4. **sed multi-line on Termux**: `sed -i` with newlines collapses everything to one line. Use Python for multi-line file edits.

5. **Wake word latency**: <1s with openWakeWord (continuous inference on 80ms audio chunks). Trigger phrase: "Hey Jarvis". Old whisper polling was ~7.5s cycle time.

6. **Wake word resources**: openWakeWord daemon uses ~8% CPU steady, 162MB RAM. Estimated <1%/hr battery (vs ~2.2%/hr with whisper polling). Configurable via `~/.hey-nothing-config`.

7. **SSH connection refused after OOM**: Wait a few seconds, sshd restarts automatically.

8. **Root context**: Magisk provides `u:r:magisk:s0`. Must use `su shell -c` for Android services, NOT `su -c` (which uses uid 0 and causes Failed transaction errors for am/cmd/settings).
