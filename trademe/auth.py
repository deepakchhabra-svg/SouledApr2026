import json
import os
from requests_oauthlib import OAuth1Session
import config


def _load_tokens():
    if os.path.exists(config.TOKENS_FILE):
        with open(config.TOKENS_FILE) as f:
            return json.load(f)
    return {}


def _save_tokens(tokens: dict):
    with open(config.TOKENS_FILE, "w") as f:
        json.dump(tokens, f)


def is_authenticated() -> bool:
    tokens = _load_tokens()
    return bool(tokens.get("oauth_token") and tokens.get("oauth_token_secret"))


def get_oauth_session() -> OAuth1Session:
    tokens = _load_tokens()
    return OAuth1Session(
        config.TRADEME_CONSUMER_KEY,
        client_secret=config.TRADEME_CONSUMER_SECRET,
        resource_owner_key=tokens["oauth_token"],
        resource_owner_secret=tokens["oauth_token_secret"],
    )


def start_oauth_flow() -> str:
    """Initiate OOB OAuth flow, return the TradeMe authorization URL."""
    oauth = OAuth1Session(
        config.TRADEME_CONSUMER_KEY,
        client_secret=config.TRADEME_CONSUMER_SECRET,
        callback_uri="oob",
    )
    fetch_response = oauth.fetch_request_token(
        config.OAUTH_REQUEST_TOKEN_URL,
        params={"scope": "MyTradeMeRead,MyTradeMeWrite"},
    )
    _save_tokens({
        "request_token": fetch_response["oauth_token"],
        "request_token_secret": fetch_response["oauth_token_secret"],
    })
    return oauth.authorization_url(config.OAUTH_AUTHORIZE_URL)


def complete_oauth_flow(oauth_token: str, oauth_verifier: str) -> bool:
    """Exchange verifier for access token. Returns True on success."""
    tokens = _load_tokens()
    oauth = OAuth1Session(
        config.TRADEME_CONSUMER_KEY,
        client_secret=config.TRADEME_CONSUMER_SECRET,
        resource_owner_key=tokens.get("request_token"),
        resource_owner_secret=tokens.get("request_token_secret"),
        verifier=oauth_verifier,
    )
    access_tokens = oauth.fetch_access_token(config.OAUTH_ACCESS_TOKEN_URL)
    _save_tokens({
        "oauth_token": access_tokens["oauth_token"],
        "oauth_token_secret": access_tokens["oauth_token_secret"],
    })
    return True


def revoke_tokens():
    if os.path.exists(config.TOKENS_FILE):
        os.remove(config.TOKENS_FILE)
