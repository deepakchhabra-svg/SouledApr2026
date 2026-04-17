"""TradeMe API client — verified against live API responses."""
from typing import Any
import config
from trademe.auth import get_oauth_session


def _get(path: str, params: dict = None) -> Any:
    session = get_oauth_session()
    resp = session.get(f"{config.TRADEME_BASE_URL}{path}", params=params or {})
    resp.raise_for_status()
    return resp.json()


def _post(path: str, json_body: dict = None) -> Any:
    session = get_oauth_session()
    resp = session.post(f"{config.TRADEME_BASE_URL}{path}", json=json_body)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Member profile  (verified: /MyTradeMe/Profile.json)
# ---------------------------------------------------------------------------

def get_member_profile() -> dict:
    return _get("/MyTradeMe/Profile.json")


# ---------------------------------------------------------------------------
# Orders — verified working, TotalCount correct, list key = "List"
# ---------------------------------------------------------------------------

def get_sold_items(status: str = "All", page: int = 1, rows: int = 50,
                   date_from: str = None, date_to: str = None) -> dict:
    params = {"page": page, "rows": rows}
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to
    return _get(f"/MyTradeMe/SoldItems/{status}.json", params)


def get_order_details(order_id: int) -> dict:
    return _get(f"/MyTradeMe/SaleOrders/{order_id}.json")


# ---------------------------------------------------------------------------
# Listings — verified working, list key = "List"
# ---------------------------------------------------------------------------

def get_my_listings(status: str = "Active", page: int = 1, rows: int = 50) -> dict:
    return _get(f"/MyTradeMe/SellingItems/{status}.json", {"page": page, "rows": rows})


def get_listing_detail(listing_id: int) -> dict:
    return _get(f"/Listings/{listing_id}.json")


def withdraw_listing(listing_id: int, reason: str = "ListedInError") -> dict:
    return _post(f"/Listings/{listing_id}/Withdraw.json", {"Reason": reason})


def relist_listing(listing_id: int) -> dict:
    return _post(f"/Listings/{listing_id}/Relist.json")


def create_listing(payload: dict) -> dict:
    return _post("/Listings.json", payload)


def edit_listing(listing_id: int, payload: dict) -> dict:
    return _post(f"/Listings/{listing_id}/Edit.json", payload)


# ---------------------------------------------------------------------------
# Questions — correct path: /Listings/Questions/Unanswered.json
# ---------------------------------------------------------------------------

def get_all_questions(page: int = 1, rows: int = 50) -> dict:
    return _get("/Listings/Questions/Unanswered.json", {"page": page, "rows": rows})


def post_answer(listing_id: int, question_id: int, answer: str) -> dict:
    return _post(f"/Listings/{listing_id}/Questions/{question_id}/Answer.json",
                 {"Answer": answer})


# ---------------------------------------------------------------------------
# Feedback — correct path: /MyTradeMe/Feedback/Seller.json
# ---------------------------------------------------------------------------

def get_pending_feedback(page: int = 1, rows: int = 50) -> dict:
    return _get("/MyTradeMe/Feedback/Seller.json", {"page": page, "rows": rows})


def post_feedback(feedback_id: int, comment: str, rating: str = "Positive") -> dict:
    return _post("/Feedback.json", {
        "FeedbackId": feedback_id,
        "Comment": comment,
        "Rating": rating,
    })


# ---------------------------------------------------------------------------
# Watchlist — verified working, list key = "List"
# ---------------------------------------------------------------------------

def get_watchlist(page: int = 1, rows: int = 50) -> dict:
    return _get("/MyTradeMe/Watchlist/All.json", {"page": page, "rows": rows})


# ---------------------------------------------------------------------------
# Categories & shipping (for listing creation)
# ---------------------------------------------------------------------------

def get_categories(category_id: int = None) -> dict:
    if category_id:
        return _get(f"/Categories/{category_id}.json")
    return _get("/Categories.json")


def get_shipping_options() -> dict:
    return _get("/ShippingOptions.json")


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

def _safe_count(fn, *args, **kwargs) -> int:
    try:
        return fn(*args, **kwargs).get("TotalCount", 0)
    except Exception:
        return 0


def get_dashboard_summary() -> dict:
    return {
        "total_sold": _safe_count(get_sold_items, "All", rows=1),
        "active_listings": _safe_count(get_my_listings, "Active", rows=1),
        "unanswered_questions": _safe_count(get_all_questions, rows=1),
        "pending_feedback": _safe_count(get_pending_feedback, rows=1),
    }
