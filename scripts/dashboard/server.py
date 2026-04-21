#!/data/data/com.termux/files/usr/bin/env python3
"""
Voice Assistant Settings API Server
Runs on 0.0.0.0:8080
Serves the dashboard PWA and handles all settings operations
"""
from flask import Flask, jsonify, request, send_from_directory
import json
import os
import re
import subprocess
import signal
import time
import tempfile
from datetime import datetime
from pathlib import Path

app = Flask(__name__, static_folder='/data/data/com.termux/files/home/dashboard')

HOME = Path.home()
SETTINGS_FILE = HOME / '.assistant-settings.json'
SHIFTS_FILE = HOME / '.shift-schedule.json'
LOCATION_CONFIG = HOME / '.location-config.json'
HEY_NOTHING_CONFIG = HOME / '.hey-nothing-config'
ANTHROPIC_KEY_FILE = HOME / '.anthropic_key'
STRIPE_KEY_FILE = HOME / '.stripe_key'
LOGS_DIR = HOME / 'logs'
NOTES_DIR = HOME / 'notes'
JOURNAL_DIR = HOME / 'journal'
HISTORY_LOG = LOGS_DIR / 'command-history.log'


def atomic_write(path, data):
    """Write JSON atomically: write to temp file then rename."""
    path = Path(path)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix='.tmp')
    try:
        with os.fdopen(tmp_fd, 'w') as f:
            json.dump(data, f, indent=2)
        os.rename(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def default_settings():
    return {
        "wake_word": {
            "enabled": True,
            "threshold": 0.3,
            "cooldown": 5,
            "required_consecutive": 2,
            "quiet_hours_start": 0,
            "quiet_hours_end": 6
        },
        "voice": {
            "stt_model": "base",
            "tts_rate": 1.0,
            "listen_duration_default": 7,
            "journal_duration": 120
        },
        "claude": {
            "model": "claude-haiku-4-5",
            "max_tokens": 1024,
            "tone": "casual",
            "response_length": "brief",
            "medical_mode": True,
            "context_ttl_minutes": 10,
            "context_turns": 10
        },
        "notifications": {
            "shift_alerts": True,
            "shift_alert_minutes_before": 60,
            "battery_alerts": True,
            "battery_alert_threshold": 20,
            "location_alerts": True,
            "watchdog_alerts": True
        },
        "location": {
            "enabled": True,
            "home_wifi": "",
            "hospital_wifi": "",
            "hospital_lat": 53.5609,
            "hospital_lng": -0.0788,
            "hospital_radius_meters": 500
        },
        "assistant": {
            "name": "Hey Jarvis",
            "user_name": "Abdul",
            "language": "en",
            "proactive_suggestions": True
        }
    }


def deep_merge(base, override):
    """Merge override into base recursively. Returns new dict."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# -- Serve frontend --

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)


# -- Settings --

@app.route('/api/settings', methods=['GET'])
def get_settings():
    defaults = default_settings()
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text())
            return jsonify(deep_merge(defaults, saved))
        except json.JSONDecodeError:
            pass
    return jsonify(defaults)


@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.get_json(silent=True) or {}
    atomic_write(SETTINGS_FILE, data)
    apply_settings(data)
    return jsonify({"status": "saved"})


def apply_settings(settings):
    """Apply settings that take effect immediately without restart."""
    ww = settings.get("wake_word", {})
    config_lines = [
        "# Hey Nothing daemon config -- openWakeWord (hey_jarvis)",
        "# Updated by dashboard at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "",
        "THRESHOLD=" + str(ww.get("threshold", 0.3)),
        "COOLDOWN=" + str(ww.get("cooldown", 5)),
        "REQUIRED_CONSECUTIVE=" + str(ww.get("required_consecutive", 2)),
        "QUIET_HOURS_START=" + str(ww.get("quiet_hours_start", 0)),
        "QUIET_HOURS_END=" + str(ww.get("quiet_hours_end", 6)),
    ]
    HEY_NOTHING_CONFIG.write_text("\n".join(config_lines) + "\n")


# -- Status --

@app.route('/api/status')
def get_status():
    status = {
        "timestamp": datetime.now().isoformat(),
        "daemons": get_daemon_status(),
        "system": get_system_info(),
        "assistant": get_assistant_info()
    }
    return jsonify(status)


def get_daemon_status():
    daemons = {}
    pid_files = {
        "hey-nothing": HOME / ".hey-nothing.pid",
        "shift-monitor": HOME / ".shift-monitor.pid",
        "location-monitor": HOME / ".location-monitor.pid",
        "watchdog": HOME / ".watchdog.pid",
        "dashboard": HOME / ".dashboard.pid"
    }
    for name, pid_file in pid_files.items():
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 0)
                daemons[name] = {"running": True, "pid": pid}
            except (ProcessLookupError, ValueError, PermissionError):
                daemons[name] = {"running": False, "pid": None}
        else:
            daemons[name] = {"running": False, "pid": None}
    return daemons


def get_system_info():
    info = {}
    # Battery (termux-battery-status works without root, sysfs needs root)
    try:
        result = subprocess.run(["termux-battery-status"],
                                capture_output=True, text=True, timeout=5)
        batt = json.loads(result.stdout)
        info["battery"] = {"level": batt.get("percentage", 0), "status": batt.get("status", "unknown")}
    except Exception:
        info["battery"] = {"level": 0, "status": "unknown"}
    # WiFi
    try:
        result = subprocess.run(["termux-wifi-connectioninfo"],
                                capture_output=True, text=True, timeout=5)
        wifi_data = json.loads(result.stdout)
        info["wifi"] = {"ssid": wifi_data.get("ssid", ""), "rssi": wifi_data.get("rssi", 0)}
    except Exception:
        info["wifi"] = {"ssid": "unknown", "rssi": 0}
    # Storage
    try:
        result = subprocess.run(["df", "-h", "/data"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            info["storage"] = {"total": parts[1], "used": parts[2], "free": parts[3]}
    except Exception:
        info["storage"] = {}
    # Uptime
    try:
        uptime = Path("/proc/uptime").read_text().split()[0]
        info["uptime_seconds"] = float(uptime)
    except Exception:
        info["uptime_seconds"] = 0
    return info


def get_assistant_info():
    info = {}
    # Hey-nothing stats
    stats_file = HOME / ".hey-nothing-stats.json"
    if stats_file.exists():
        try:
            info["wake_word_stats"] = json.loads(stats_file.read_text())
        except Exception:
            pass
    # Command count today
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        if HISTORY_LOG.exists():
            lines = HISTORY_LOG.read_text().splitlines()
            today_lines = [l for l in lines if today in l]
            info["commands_today"] = len(today_lines)
        else:
            info["commands_today"] = 0
    except Exception:
        info["commands_today"] = 0
    # Current location
    location_file = HOME / ".current-location.json"
    if location_file.exists():
        try:
            info["location"] = json.loads(location_file.read_text())
        except Exception:
            pass
    # Current shift
    try:
        result = subprocess.run(
            [str(HOME / "bin" / "voice-shift"), "--summary"],
            capture_output=True, text=True, timeout=5
        )
        info["shift_status"] = result.stdout.strip()
    except Exception:
        info["shift_status"] = "unknown"
    return info


# -- Daemons --

DAEMON_COMMANDS = {
    "hey-nothing": {
        "start": "nohup python3 {home}/bin/hey-nothing > {home}/logs/hey-nothing.log 2>&1 &\necho $! > {home}/.hey-nothing.pid",
        "pid": ".hey-nothing.pid"
    },
    "shift-monitor": {
        "start": "nohup {home}/bin/shift-monitor > {home}/logs/shift-monitor.log 2>&1 &\necho $! > {home}/.shift-monitor.pid",
        "pid": ".shift-monitor.pid"
    },
    "location-monitor": {
        "start": "nohup {home}/bin/voice-location-monitor > {home}/logs/location-monitor.log 2>&1 &\necho $! > {home}/.location-monitor.pid",
        "pid": ".location-monitor.pid"
    },
    "watchdog": {
        "start": "nohup {home}/bin/assistant-watchdog > {home}/logs/watchdog.log 2>&1 &\necho $! > {home}/.watchdog.pid",
        "pid": ".watchdog.pid"
    },
}


@app.route('/api/daemon/<name>/start', methods=['POST'])
def start_daemon(name):
    if name not in DAEMON_COMMANDS:
        return jsonify({"error": "Unknown daemon"}), 404
    cmd = DAEMON_COMMANDS[name]["start"].format(home=HOME)
    subprocess.Popen(cmd, shell=True, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    return jsonify({"status": "started"})


@app.route('/api/daemon/<name>/stop', methods=['POST'])
def stop_daemon(name):
    if name not in DAEMON_COMMANDS:
        return jsonify({"error": "Unknown daemon"}), 404
    pid_file = HOME / DAEMON_COMMANDS[name]["pid"]
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            pid_file.unlink(missing_ok=True)
            return jsonify({"status": "stopped"})
        except ProcessLookupError:
            pid_file.unlink(missing_ok=True)
            return jsonify({"status": "was not running"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"status": "not running"})


@app.route('/api/daemon/<name>/restart', methods=['POST'])
def restart_daemon(name):
    if name not in DAEMON_COMMANDS:
        return jsonify({"error": "Unknown daemon"}), 404
    # Stop
    pid_file = HOME / DAEMON_COMMANDS[name]["pid"]
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            pid_file.unlink(missing_ok=True)
        except (ProcessLookupError, ValueError):
            pid_file.unlink(missing_ok=True)
    time.sleep(2)
    # Start
    cmd = DAEMON_COMMANDS[name]["start"].format(home=HOME)
    subprocess.Popen(cmd, shell=True, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    return jsonify({"status": "restarted"})


@app.route('/api/daemon/restart-all', methods=['POST'])
def restart_all():
    for name in DAEMON_COMMANDS:
        pid_file = HOME / DAEMON_COMMANDS[name]["pid"]
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, signal.SIGTERM)
                pid_file.unlink(missing_ok=True)
            except (ProcessLookupError, ValueError):
                pid_file.unlink(missing_ok=True)
    time.sleep(2)
    for name in DAEMON_COMMANDS:
        cmd = DAEMON_COMMANDS[name]["start"].format(home=HOME)
        subprocess.Popen(cmd, shell=True, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)  # stagger starts to avoid OOM on phone
    return jsonify({"status": "all restarted"})


# -- Logs --

SAFE_LOG_NAMES = frozenset([
    "hey-nothing", "shift-monitor", "location-monitor",
    "watchdog", "voice-alarm", "voice-claude", "command-history",
    "dashboard"
])


@app.route('/api/logs/<daemon>')
def get_logs(daemon):
    if daemon not in SAFE_LOG_NAMES:
        return jsonify({"error": "Invalid log name"}), 400
    log_file = LOGS_DIR / (daemon + ".log")
    if not log_file.exists():
        return jsonify({"lines": [], "exists": False})
    lines = log_file.read_text().splitlines()
    limit = request.args.get("limit", 100, type=int)
    limit = min(limit, 1000)
    return jsonify({"lines": lines[-limit:], "exists": True, "total": len(lines)})


@app.route('/api/logs/<daemon>/clear', methods=['POST'])
def clear_log(daemon):
    if daemon not in SAFE_LOG_NAMES:
        return jsonify({"error": "Invalid log name"}), 400
    log_file = LOGS_DIR / (daemon + ".log")
    if log_file.exists():
        log_file.write_text("")
    return jsonify({"status": "cleared"})


@app.route('/api/errors')
def get_errors():
    """Aggregate errors from all logs."""
    errors = []
    if not LOGS_DIR.exists():
        return jsonify({"errors": []})
    for log_file in LOGS_DIR.glob("*.log"):
        try:
            lines = log_file.read_text().splitlines()
            for i, line in enumerate(lines):
                low = line.lower()
                if any(kw in low for kw in ["error", "fatal", "exception", "traceback", "failed"]):
                    errors.append({
                        "source": log_file.stem,
                        "line": line[:500],
                        "line_number": i + 1,
                        "timestamp": line[:19] if line.startswith("[20") or line.startswith("20") else "unknown"
                    })
        except Exception:
            pass
    errors.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify({"errors": errors[:50]})


# -- Apps registry --

@app.route('/api/apps')
def get_apps():
    """Parse apps from voice-open script."""
    voice_open = HOME / "bin" / "voice-open"
    apps = []
    if voice_open.exists():
        content = voice_open.read_text()
        matches = re.findall(r'\["([^"]+)"\]="([^"]+)"', content)
        seen_packages = {}
        for keyword, package in matches:
            pkg_base = package.split("/")[0]
            if pkg_base not in seen_packages:
                seen_packages[pkg_base] = {
                    "package": package,
                    "keywords": [keyword],
                    "enabled": True
                }
            else:
                seen_packages[pkg_base]["keywords"].append(keyword)
        apps = [{"name": data["keywords"][0], **data} for _, data in seen_packages.items()]
    return jsonify({"apps": apps})


@app.route('/api/apps', methods=['POST'])
def add_app():
    """Add a new app keyword to voice-open."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").lower().strip()
    package = data.get("package", "").strip()
    if not name or not package:
        return jsonify({"error": "name and package required"}), 400
    # Validate no shell injection characters
    if any(c in name for c in "\"'\\$`"):
        return jsonify({"error": "Invalid characters in name"}), 400
    if any(c in package for c in "\"'\\$`"):
        return jsonify({"error": "Invalid characters in package"}), 400

    voice_open = HOME / "bin" / "voice-open"
    content = voice_open.read_text()
    new_entry = '    ["' + name + '"]="' + package + '"'
    content = content.replace("\n)\n", "\n" + new_entry + "\n)\n", 1)
    voice_open.write_text(content)
    return jsonify({"status": "added"})


@app.route('/api/apps/<path:package>', methods=['DELETE'])
def remove_app(package):
    """Remove all keywords for a package from voice-open."""
    voice_open = HOME / "bin" / "voice-open"
    content = voice_open.read_text()
    pkg_escaped = re.escape(package)
    content = re.sub(r'\s*\["[^"]+"\]="' + pkg_escaped + r'[^"]*"\n', "\n", content)
    voice_open.write_text(content)
    return jsonify({"status": "removed"})


# -- Shifts --

@app.route('/api/shifts')
def get_shifts():
    if SHIFTS_FILE.exists():
        try:
            return jsonify(json.loads(SHIFTS_FILE.read_text()))
        except json.JSONDecodeError:
            pass
    return jsonify({"shifts": []})


@app.route('/api/shifts', methods=['POST'])
def add_shift():
    data = request.get_json(silent=True) or {}
    shifts_data = {"shifts": []}
    if SHIFTS_FILE.exists():
        try:
            shifts_data = json.loads(SHIFTS_FILE.read_text())
        except json.JSONDecodeError:
            pass
    shifts_data["shifts"].append(data)
    shifts_data["shifts"].sort(key=lambda x: x.get("date", ""))
    atomic_write(SHIFTS_FILE, shifts_data)
    return jsonify({"status": "added"})


@app.route('/api/shifts/<date>', methods=['DELETE'])
def delete_shift(date):
    if SHIFTS_FILE.exists():
        try:
            data = json.loads(SHIFTS_FILE.read_text())
            data["shifts"] = [s for s in data["shifts"] if s.get("date") != date]
            atomic_write(SHIFTS_FILE, data)
        except json.JSONDecodeError:
            pass
    return jsonify({"status": "deleted"})


# -- API Keys --

@app.route('/api/keys/status')
def key_status():
    """Return masked key status -- never the full key."""
    result = {}
    if ANTHROPIC_KEY_FILE.exists():
        key = ANTHROPIC_KEY_FILE.read_text().strip()
        result["anthropic"] = key[:8] + "***" if len(key) > 8 else "***"
    else:
        result["anthropic"] = None
    if STRIPE_KEY_FILE.exists():
        key = STRIPE_KEY_FILE.read_text().strip()
        result["stripe"] = key[:8] + "***" if len(key) > 8 else "***"
    else:
        result["stripe"] = None
    return jsonify(result)


@app.route('/api/keys/test', methods=['POST'])
def test_api_key():
    """Test Anthropic API key."""
    import urllib.request
    key = ANTHROPIC_KEY_FILE.read_text().strip() if ANTHROPIC_KEY_FILE.exists() else ""
    if not key:
        return jsonify({"valid": False, "error": "No API key configured"})
    try:
        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "Hi"}]
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return jsonify({"valid": True, "status": r.status})
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)})


@app.route('/api/keys/anthropic', methods=['POST'])
def save_anthropic_key():
    key = (request.get_json(silent=True) or {}).get("key", "").strip()
    if not key:
        return jsonify({"error": "Empty key"}), 400
    ANTHROPIC_KEY_FILE.write_text(key)
    os.chmod(str(ANTHROPIC_KEY_FILE), 0o600)
    return jsonify({"status": "saved"})


@app.route('/api/keys/stripe', methods=['POST'])
def save_stripe_key():
    key = (request.get_json(silent=True) or {}).get("key", "").strip()
    if not key:
        return jsonify({"error": "Empty key"}), 400
    STRIPE_KEY_FILE.write_text(key)
    os.chmod(str(STRIPE_KEY_FILE), 0o600)
    return jsonify({"status": "saved"})


# -- Command history --

@app.route('/api/history')
def get_history():
    if not HISTORY_LOG.exists():
        return jsonify({"commands": []})
    lines = HISTORY_LOG.read_text().splitlines()
    limit = request.args.get("limit", 50, type=int)
    limit = min(limit, 500)
    commands = []
    for line in lines[-limit:]:
        parts = line.split("|")
        if len(parts) >= 4:
            commands.append({
                "timestamp": parts[0],
                "datetime": parts[1],
                "text": parts[2],
                "routed_to": parts[3]
            })
    return jsonify({"commands": list(reversed(commands))})


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    if HISTORY_LOG.exists():
        HISTORY_LOG.write_text("")
    return jsonify({"status": "cleared"})


# -- Notes and Journal --

@app.route('/api/notes')
def list_notes():
    notes = []
    if NOTES_DIR.exists():
        for f in sorted(NOTES_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            content = f.read_text()
            title = content.split("\n")[0].replace("# ", "") if content else f.stem
            notes.append({
                "filename": f.name,
                "title": title,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
    return jsonify({"notes": notes})


@app.route('/api/notes/<filename>')
def get_note(filename):
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"error": "Invalid filename"}), 400
    note_file = NOTES_DIR / filename
    if not note_file.exists() or note_file.suffix != ".md":
        return jsonify({"error": "Not found"}), 404
    return jsonify({"content": note_file.read_text(), "filename": filename})


@app.route('/api/notes/<filename>', methods=['DELETE'])
def delete_note(filename):
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"error": "Invalid filename"}), 400
    note_file = NOTES_DIR / filename
    if note_file.exists() and note_file.suffix == ".md":
        note_file.unlink()
    return jsonify({"status": "deleted"})


@app.route('/api/journal')
def list_journal():
    entries = []
    if JOURNAL_DIR.exists():
        for f in sorted(JOURNAL_DIR.glob("*.md"), key=lambda x: x.name, reverse=True):
            entries.append({
                "filename": f.name,
                "date": f.stem,
                "size": f.stat().st_size
            })
    return jsonify({"entries": entries})


# -- Quick actions --

SAFE_ACTIONS = frozenset([
    "voice-briefing", "voice-weather", "voice-screenshot",
    "voice-shift", "voice-calendar", "voice-history",
    "voice-note-list", "voice-info"
])


@app.route('/api/action/<script>', methods=['POST'])
def run_action(script):
    if script not in SAFE_ACTIONS:
        return jsonify({"error": "Script not allowed"}), 403
    arg = (request.get_json(silent=True) or {}).get("arg", "")
    try:
        cmd = [str(HOME / "bin" / "run-voice"), str(HOME / "bin" / script)]
        if arg:
            cmd.append(str(arg))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return jsonify({"status": "launched", "output": result.stdout[:2000]})
    except subprocess.TimeoutExpired:
        return jsonify({"status": "launched", "output": "(still running)"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/wifi/current')
def get_current_wifi():
    try:
        result = subprocess.run(["termux-wifi-connectioninfo"],
                                capture_output=True, text=True, timeout=5)
        data = json.loads(result.stdout)
        return jsonify({"ssid": data.get("ssid", ""), "bssid": data.get("bssid", "")})
    except Exception:
        return jsonify({"ssid": "", "bssid": ""})


# -- Data management --

@app.route('/api/data/clear-claude-history', methods=['POST'])
def clear_claude_history():
    hist = HOME / ".voice-claude-history.json"
    if hist.exists():
        hist.unlink()
    return jsonify({"status": "cleared"})


@app.route('/api/data/clear-all-logs', methods=['POST'])
def clear_all_logs():
    if LOGS_DIR.exists():
        for f in LOGS_DIR.glob("*.log"):
            f.write_text("")
    return jsonify({"status": "cleared"})


# -- Error handler --

@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import ssl
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (HOME / ".dashboard.pid").write_text(str(os.getpid()))
    cert_file = HOME / "dashboard" / "cert.pem"
    key_file = HOME / "dashboard" / "key.pem"
    if cert_file.exists() and key_file.exists():
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(cert_file), str(key_file))
        print("Dashboard running at https://0.0.0.0:8080 (SSL)")
        app.run(host="0.0.0.0", port=8080, debug=False, threaded=True, ssl_context=ctx)
    else:
        print("Dashboard running at http://0.0.0.0:8080 (no SSL certs found)")
        app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
