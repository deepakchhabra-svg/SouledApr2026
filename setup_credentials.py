"""Run this once to securely write your .env file. Input is hidden (like a password prompt)."""
import getpass
import secrets
import os

print("\n=== TradeMe Store Manager — Credential Setup ===\n")
print("Input is hidden — nothing you type will appear on screen.\n")

key = getpass.getpass("TradeMe Consumer Key: ").strip()
secret = getpass.getpass("TradeMe Consumer Secret: ").strip()

if not key or not secret:
    print("\nError: both values are required.")
    exit(1)

env_path = os.path.join(os.path.dirname(__file__), ".env")
with open(env_path, "w") as f:
    f.write(f"TRADEME_CONSUMER_KEY={key}\n")
    f.write(f"TRADEME_CONSUMER_SECRET={secret}\n")
    f.write("TRADEME_ENVIRONMENT=production\n")
    f.write(f"SECRET_KEY={secrets.token_hex(32)}\n")

print(f"\n.env written to {env_path}")
print("Run:  python app.py\n")
