"""TradeMe API client — thin wrapper around authenticated HTTP calls."""
from typing import Any
import config
from trademe.auth import get_oauth_session


def _get(path: str, params: dict = None) -> Any:
    session = get_oauth_session()
    url = f"{config.TRADEME_BASE_URL}{path}"
    resp = session.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, json_body: dict = None) -> Any:
    session = get_oauth_session()
    url = f"{config.TRADEME_BASE_URL}{path}"
    resp = session.post(url, json=json_body)
    resp.raise_for_status()
    return resp.json()


def _delete(path: str) -> Any:
    session = get_oauth_session()
    url = f"{config.TRADEME_BASE_URL}{path}"
    resp = session.delete(url)
    resp.raise_for_status()
    return resp.json() if resp.content else {}


# ---------------------------------------------------------------------------
# Member / store info
# ---------------------------------------------------------------------------

def get_member_profile() -> dict:
    return _get("/Members/Me.json")


# ---------------------------------------------------------------------------
# Orders (sold items)
# ---------------------------------------------------------------------------

def get_sold_items(status: str = "All", page: int = 1, rows: int = 50) -> dict:
    """
    status options: All, SoldPendingPayment, SoldPendingFeedback,
                    SoldWithFeedback, SoldAndPosted, SoldAndNotPosted
    """
    return _get(f"/MyTradeMe/SoldItems/{status}.json", {
        "page": page,
        "rows": rows,
    })


def get_order_details(order_id: int) -> dict:
    return _get(f"/MyTradeMe/SaleOrders/{order_id}.json")


# ---------------------------------------------------------------------------
# Listings (products)
# ---------------------------------------------------------------------------

def get_my_listings(status: str = "Active", page: int = 1, rows: int = 50) -> dict:
    """
    status: Active, Unsold, Sold, Withdrawn, Expired
    """
    return _get(f"/MyTradeMe/SellingItems/{status}.json", {
        "page": page,
        "rows": rows,
    })


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
# Questions
# ---------------------------------------------------------------------------

def get_unsold_questions(page: int = 1, rows: int = 50) -> dict:
    return _get("/MyTradeMe/UnansweredQuestions.json", {"page": page, "rows": rows})


def get_all_questions(status: str = "Unanswered", page: int = 1, rows: int = 50) -> dict:
    """status: Unanswered, All"""
    return _get(f"/MyTradeMe/Questions/{status}.json", {"page": page, "rows": rows})


def post_answer(listing_id: int, question_id: int, answer: str) -> dict:
    return _post(f"/Listings/{listing_id}/Questions/{question_id}/Answer.json", {
        "Answer": answer
    })


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

def get_pending_feedback(page: int = 1, rows: int = 50) -> dict:
    return _get("/MyTradeMe/FeedbackPending.json", {"page": page, "rows": rows})


def post_feedback(feedback_id: int, comment: str, rating: str = "Positive") -> dict:
    return _post(f"/Feedback.json", {
        "FeedbackId": feedback_id,
        "Comment": comment,
        "Rating": rating,
    })


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

def get_watchlist(page: int = 1, rows: int = 50) -> dict:
    return _get("/MyTradeMe/Watchlist.json", {"page": page, "rows": rows})


# ---------------------------------------------------------------------------
# Categories (for listing creation)
# ---------------------------------------------------------------------------

def get_categories(category_id: int = None) -> dict:
    if category_id:
        return _get(f"/Categories/{category_id}.json")
    return _get("/Categories.json")


# ---------------------------------------------------------------------------
# Shipping options (for listing creation)
# ---------------------------------------------------------------------------

def get_shipping_options() -> dict:
    return _get("/ShippingOptions.json")


# ---------------------------------------------------------------------------
# Summary / dashboard
# ---------------------------------------------------------------------------

def get_dashboard_summary() -> dict:
    """Aggregate key counts for the dashboard."""
    sold = get_sold_items("All", rows=1)
    active = get_my_listings("Active", rows=1)
    questions = get_all_questions("Unanswered", rows=1)
    feedback = get_pending_feedback(rows=1)
    return {
        "total_sold": sold.get("TotalCount", 0),
        "active_listings": active.get("TotalCount", 0),
        "unanswered_questions": questions.get("TotalCount", 0),
        "pending_feedback": feedback.get("TotalCount", 0),
    }
