#!/data/data/com.termux/files/usr/bin/sh
# Restore pending reminders from reminders.json on Termux boot
export HOME="/data/data/com.termux/files/home"
export PREFIX="/data/data/com.termux/files/usr"
export PATH="$PREFIX/bin:$PATH"
sleep 5  # let other services settle first
python3 "$HOME/bin/restore-reminders.py" >> "$HOME/logs/restore-reminders.log" 2>&1
