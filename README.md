# Nothing Archives

Termux scripts and tooling for Nothing Phone 2a (rooted, unlocked bootloader).

## Scripts

### `voice-alarm`
Voice-controlled alarm setter. Uses `termux-speech-to-text` to capture natural language, parses it with Python, and sets an alarm in the stock Clock app via `android.intent.action.SET_ALARM`.

Handles phrases like:
- "wake me at 7 AM"
- "set alarm for 6:30"
- "seven thirty am"

Retries up to 3 times if speech capture fails.

### `voice-open`
Voice-controlled app launcher. Say an app name (e.g., "WhatsApp", "YouTube") and it launches via `am start`. Supports substring matching, so "open WhatsApp" or just "WhatsApp" both work.

App registry is defined inline in the script — edit `APPS` to add more.

### `parse_alarm.py`
Helper used by `voice-alarm`. Parses natural-language time expressions (word numbers, AM/PM, HH:MM formats) into `HOUR|MINUTE|LABEL` format.

## Requirements

- Termux (F-Droid build)
- Termux:API app (F-Droid) + `pkg install termux-api`
- Termux:Widget (F-Droid) for home-screen triggers (optional)
- Python 3: `pkg install python`
- Microphone permission granted to Termux:API

## Install

```bash
git clone https://github.com/<your-username>/nothing-archives.git
cd nothing-archives
mkdir -p ~/bin
cp scripts/* ~/bin/
chmod +x ~/bin/voice-alarm ~/bin/voice-open ~/bin/parse_alarm.py
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
