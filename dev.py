"""
Dev runner — auto-pulls latest code and Flask auto-reloads on changes.
Run once:  python dev.py
Then just refresh your browser after any fix is pushed.
"""
import subprocess
import threading
import time
import os


def git_pull_loop():
    while True:
        time.sleep(10)
        result = subprocess.run(
            ["git", "pull"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__)
        )
        if result.stdout.strip() and result.stdout.strip() != "Already up to date.":
            print(f"\n[dev] Updated: {result.stdout.strip()}\n")


# Only start the pull thread in the reloader child process (not the parent watcher)
if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    t = threading.Thread(target=git_pull_loop, daemon=True)
    t.start()
    print("[dev] Auto-pull active — checks for updates every 10 seconds.")

from app import app
app.run(debug=True, port=5000, use_reloader=True)
