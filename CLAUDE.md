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
           → voice-* (action scripts)
           → Android APIs (am, cmd, termux-api, su shell)
```

- **Single entry point**: `~/bin/voice` (unified router)
- **STT engine**: `~/bin/whisper-listen` (whisper.cpp: tiny.en for wake word, base.en default for commands, small.en via --accurate for dictation)
- **Wake word**: `~/bin/hey-nothing` (whisper polling daemon, ~7.5s cycle)
- **Daemon control**: `~/bin/hey-nothing-ctl` (start/stop/status/restart)
- **TTS**: `termux-tts-speak` (synchronous, use `say()` helper)
- **Detached execution**: `~/bin/run-voice` (avoids OOM on SSH sessions)
- **Context store**: `~/bin/voice-context` (shared state, 10min TTL)

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
- `openWakeWord` / `pvporcupine` / `precise-runner` → all fail on Android bionic libc
- `sed -i` multi-line insert on Termux → collapses to single line. Use Python for multi-line edits.
- `/tmp` writes → permission denied. Use `~/` or `$HOME/.cache/`.
- `set -e` in long-running scripts → kills daemon on any non-zero sub-command. Never use in daemons.

## Script inventory (29 scripts)

### Core
| Script | Description |
|--------|-------------|
| `voice` | Unified router — listen once, route to sub-script by keyword |
| `whisper-listen` | Record + transcribe with whisper.cpp. Flags: `--fast` (tiny.en ~3s), `--accurate` (small.en ~20s), `--energy-gate N`. Default: base.en ~5-7s |
| `run-voice` | Detached script runner — prevents OOM on SSH |
| `voice-context` | Shared context store (write/read/clear/last). 10min TTL. |

### Wake word
| Script | Description |
|--------|-------------|
| `hey-nothing` | Wake word daemon — whisper polling with energy gating, screen-aware polling, quiet hours |
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
~/.hey-nothing-stats          — daemon statistics
~/.hey-nothing-config         — wake word daemon tuning
~/.smart-home-config          — Home Assistant / n8n endpoints
~/.shortcuts/                 — Termux:Widget symlinks
~/.termux/boot/               — Termux:Boot startup scripts
~/projects/nothing-archives/  — this git repo
```

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

5. **Wake word latency**: Cycle time ~7.5s (limited by whisper tiny.en ~2.9s transcription on Dimensity 7200 Pro). All neural wake word engines fail on Termux/bionic.

6. **Battery drain**: Estimated ~2.2%/hr weighted average with all optimizations (energy gating + screen-aware polling + quiet hours). Configurable via `~/.hey-nothing-config`.

7. **SSH connection refused after OOM**: Wait a few seconds, sshd restarts automatically.

8. **Root context**: Magisk provides `u:r:magisk:s0`. Must use `su shell -c` for Android services, NOT `su -c` (which uses uid 0 and causes Failed transaction errors for am/cmd/settings).
