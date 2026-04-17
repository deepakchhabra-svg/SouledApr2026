"""
Dev runner — auto-pulls latest code, auto-reloads Flask, and pushes
app.log to a remote dev-logs branch so Claude can read errors live.
Run once:  python dev.py
"""
import subprocess
import threading
import time
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(ROOT, "app.log")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)


def git_pull_loop():
    while True:
        time.sleep(10)
        result = run(["git", "pull"])
        out = result.stdout.strip()
        if out and out != "Already up to date.":
            print(f"\n[dev] Updated: {out}\n")


def push_logs_loop():
    """Force-push app.log to origin/dev-logs branch every 30s if it changed."""
    last_size = -1
    while True:
        time.sleep(30)
        try:
            if not os.path.exists(LOG_FILE):
                continue
            size = os.path.getsize(LOG_FILE)
            if size == last_size:
                continue
            last_size = size
            run(["git", "add", "-f", "app.log"])
            run(["git", "commit", "-m", "logs", "--allow-empty",
                 "--no-verify", "-q"])
            run(["git", "push", "origin", "HEAD:dev-logs", "--force", "-q"])
        except Exception as e:
            print(f"[dev] Log push error: {e}")


# Only run threads in the Werkzeug reloader child process
if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    threading.Thread(target=git_pull_loop, daemon=True).start()
    threading.Thread(target=push_logs_loop, daemon=True).start()
    print("[dev] Auto-pull every 10s | Log push to dev-logs every 30s")

from app import app
app.run(debug=True, port=5000, use_reloader=True)
