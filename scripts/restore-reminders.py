#!/data/data/com.termux/files/usr/bin/python3
"""Restore pending reminders after Termux boot.
Reads ~/notes/reminders.json, re-spawns background timers for future reminders,
and fires missed ones immediately with a "Missed" prefix.
"""
import json
import os
import subprocess
import time
from pathlib import Path

REMINDERS_JSON = Path.home() / "notes" / "reminders.json"
LOG = Path.home() / "logs" / "restore-reminders.log"


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n")
    print(msg)


def fire_reminder(message, missed=False):
    """Fire a reminder via notification + TTS."""
    prefix = "Missed reminder: " if missed else "Reminder: "
    full = prefix + message
    subprocess.Popen(
        ["termux-notification", "--title", "Reminder",
         "--content", full, "--sound", "--priority", "high"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    subprocess.Popen(
        ["termux-tts-speak", full],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def schedule_reminder(rem):
    """Spawn a background sleep + fire for a future reminder."""
    delay = rem["fire_epoch"] - int(time.time())
    if delay <= 0:
        return None
    msg = rem["message"]
    rem_id = rem["id"]
    json_path = str(REMINDERS_JSON)
    # Build the shell command for background fire
    parts = [
        f"sleep {delay}",
        f'termux-notification --title "Reminder" --content "Reminder: {msg}" --id "{rem_id}" --sound --priority high',
        f'termux-tts-speak "Reminder: {msg}" 2>/dev/null',
    ]
    # Cleanup: remove from JSON after firing
    cleanup = (
        "python3 -c \""
        "import json; "
        f"p='{json_path}'; "
        "r=json.load(open(p)); "
        f"r=[x for x in r if x.get('id')!='{rem_id}']; "
        "json.dump(r,open(p,'w'),indent=2)"
        "\""
    )
    cmd = "(" + " && ".join(parts) + " ; " + cleanup + ") &"
    proc = subprocess.Popen(
        ["bash", "-c", cmd],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    return proc.pid


def main():
    if not REMINDERS_JSON.exists():
        log("No reminders.json found -- nothing to restore.")
        return

    try:
        with open(REMINDERS_JSON) as f:
            reminders = json.load(f)
    except (json.JSONDecodeError, ValueError):
        log("reminders.json is corrupted -- skipping.")
        return

    if not reminders:
        log("No reminders to restore.")
        return

    now = int(time.time())
    kept = []
    missed_count = 0
    restored_count = 0

    for rem in reminders:
        fire_at = rem.get("fire_epoch", 0)
        msg = rem.get("message", "Unknown")

        if fire_at <= now:
            # Missed -- fire immediately
            log(f"MISSED: '{msg}' (was due {(now - fire_at) // 60}m ago)")
            fire_reminder(msg, missed=True)
            missed_count += 1
        else:
            # Future -- re-schedule
            remaining = fire_at - now
            pid = schedule_reminder(rem)
            if pid:
                rem["restored_pid"] = pid
                kept.append(rem)
                restored_count += 1
                log(f"RESTORED: '{msg}' in {remaining // 60}m (PID {pid})")
            else:
                log(f"FAILED to restore: '{msg}'")

    # Write back only active reminders
    with open(REMINDERS_JSON, "w") as f:
        json.dump(kept, f, indent=2)

    log(f"Done: {restored_count} restored, {missed_count} missed fired.")


if __name__ == "__main__":
    main()
