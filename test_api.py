"""
Run this once to see exactly what TradeMe API returns for each endpoint.
Usage:  python test_api.py
Output is saved to api_test_results.txt
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from trademe.auth import get_oauth_session
import config

def get(path, params=None):
    s = get_oauth_session()
    r = s.get(f"{config.TRADEME_BASE_URL}{path}", params=params or {})
    return r.status_code, r.text[:1000]

tests = [
    ("Sold Items - All",          "/MyTradeMe/SoldItems/All.json",        {"page":1,"rows":3}),
    ("Sold Items - SoldWithFeedback", "/MyTradeMe/SoldItems/SoldWithFeedback.json", {"page":1,"rows":3}),
    ("My Listings - SellingItems/Active", "/MyTradeMe/SellingItems/Active.json",  {"page":1,"rows":3}),
    ("My Listings - SellingItems/Sold",  "/MyTradeMe/SellingItems/Sold.json",     {"page":1,"rows":3}),
    ("My Listings - MyListings",  "/MyTradeMe/MyListings.json",           {"page":1,"rows":3}),
    ("My Listings - SoldListings","/MyTradeMe/SoldListings.json",         {"page":1,"rows":3}),
    ("Questions.json",            "/MyTradeMe/Questions.json",            {"page":1,"rows":3}),
    ("Questions/All.json",        "/MyTradeMe/Questions/All.json",        {"page":1,"rows":3}),
    ("Feedback/ForSeller",        "/MyTradeMe/Feedback/ForSeller.json",   {"page":1,"rows":3}),
    ("Feedback/All",              "/MyTradeMe/Feedback/All.json",         {"page":1,"rows":3}),
    ("Watchlist/All",             "/MyTradeMe/Watchlist/All.json",        {"page":1,"rows":3}),
    ("Member Profile",            "/Members/Me.json",                     {}),
]

lines = []
for name, path, params in tests:
    code, body = get(path, params)
    status = "OK " if code == 200 else "ERR"
    # Show top-level keys if JSON
    try:
        keys = list(json.loads(body).keys())
    except Exception:
        keys = []
    line = f"[{status} {code}] {name}\n         keys: {keys}\n         {body[:300]}\n"
    lines.append(line)
    print(line)

with open("api_test_results.txt", "w") as f:
    f.write("\n".join(lines))

print("\nSaved to api_test_results.txt")
