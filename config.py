import os
from dotenv import load_dotenv

load_dotenv()

TRADEME_CONSUMER_KEY = os.getenv("TRADEME_CONSUMER_KEY", "")
TRADEME_CONSUMER_SECRET = os.getenv("TRADEME_CONSUMER_SECRET", "")
TRADEME_ENVIRONMENT = os.getenv("TRADEME_ENVIRONMENT", "sandbox")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

if TRADEME_ENVIRONMENT == "production":
    TRADEME_BASE_URL = "https://api.trademe.co.nz/v1"
    TRADEME_AUTH_BASE = "https://secure.trademe.co.nz/Oauth"
else:
    TRADEME_BASE_URL = "https://api.tmsandbox.co.nz/v1"
    TRADEME_AUTH_BASE = "https://secure.tmsandbox.co.nz/Oauth"

OAUTH_REQUEST_TOKEN_URL = f"{TRADEME_AUTH_BASE}/RequestToken"
OAUTH_AUTHORIZE_URL = f"{TRADEME_AUTH_BASE}/Authorize"
OAUTH_ACCESS_TOKEN_URL = f"{TRADEME_AUTH_BASE}/AccessToken"

TOKENS_FILE = ".trademe_tokens.json"
