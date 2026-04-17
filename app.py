"""TradeMe Store Manager — main Flask application."""
from flask import (
    Flask, render_template, redirect, url_for, request,
    session, flash, send_file, jsonify, Response,
)
import io
import logging
import queue
import threading
import time
import config
import trademe.auth as auth
import trademe.client as tm
import trademe.export as export_util

# ---------------------------------------------------------------------------
# Logging — write to file + in-memory queue for live /dev/logs stream
# ---------------------------------------------------------------------------

log_queue: queue.Queue = queue.Queue(maxsize=500)

class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            log_queue.put_nowait(self.format(record))
        except queue.Full:
            log_queue.get_nowait()
            log_queue.put_nowait(self.format(record))

_fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S")
_qh = QueueHandler()
_qh.setFormatter(_fmt)

file_handler = logging.FileHandler("app.log")
file_handler.setFormatter(_fmt)

root = logging.getLogger()
if not root.handlers:
    root.setLevel(logging.INFO)
    root.addHandler(_qh)
    root.addHandler(file_handler)

wz = logging.getLogger("werkzeug")
if not wz.handlers:
    wz.addHandler(_qh)
    wz.addHandler(file_handler)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


@app.context_processor
def inject_globals():
    return {
        "auth_ok": auth.is_authenticated(),
        "environment": config.TRADEME_ENVIRONMENT,
    }


def require_auth(fn):
    from functools import wraps

    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not auth.is_authenticated():
            flash("Please connect your TradeMe account first.", "warning")
            return redirect(url_for("connect"))
        return fn(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if not auth.is_authenticated():
        return redirect(url_for("connect"))
    return redirect(url_for("dashboard"))


@app.route("/connect")
def connect():
    if auth.is_authenticated():
        return redirect(url_for("dashboard"))
    return render_template("connect.html", environment=config.TRADEME_ENVIRONMENT)


@app.route("/connect/start")
def connect_start():
    try:
        auth_url = auth.start_oauth_flow()
        return render_template("connect_pin.html", auth_url=auth_url)
    except Exception as e:
        flash(f"Failed to start OAuth flow: {e}", "danger")
        return redirect(url_for("connect"))


@app.route("/connect/pin", methods=["POST"])
def connect_pin():
    pin = request.form.get("pin", "").strip()
    if not pin:
        flash("Please enter the PIN from TradeMe.", "warning")
        return redirect(url_for("connect"))
    try:
        auth.complete_oauth_flow(None, pin)
        flash("Successfully connected to TradeMe!", "success")
    except Exception as e:
        flash(f"OAuth failed: {e}", "danger")
        return redirect(url_for("connect"))
    return redirect(url_for("dashboard"))


@app.route("/disconnect")
def disconnect():
    auth.revoke_tokens()
    flash("Disconnected from TradeMe.", "info")
    return redirect(url_for("connect"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@require_auth
def dashboard():
    try:
        summary = tm.get_dashboard_summary()
    except Exception as e:
        flash(f"Error loading dashboard: {e}", "danger")
        summary = {}
    return render_template("dashboard.html", summary=summary,
                           environment=config.TRADEME_ENVIRONMENT)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@app.route("/orders")
@require_auth
def orders():
    from datetime import date, timedelta
    status = request.args.get("status", "All")
    page = int(request.args.get("page", 1))
    rows = int(request.args.get("rows", 25))
    # Default: last 2 years so historical sales show up
    default_from = (date.today() - timedelta(days=730)).isoformat()
    date_from = request.args.get("date_from", default_from)
    date_to = request.args.get("date_to", "")
    try:
        data = tm.get_sold_items(status, page, rows,
                                 date_from=date_from or None,
                                 date_to=date_to or None)
        items = data.get("List") or data.get("SoldItems") or []
        total = data.get("TotalCount", 0)
        logging.info(f"Orders fetched: status={status} date_from={date_from} date_to={date_to} total={total}")
    except Exception as e:
        logging.error(f"Orders error: {e}")
        flash(f"Error loading orders: {e}", "danger")
        items, total = [], 0
    statuses = [
        "All", "SoldPendingPayment", "SoldPendingFeedback",
        "SoldWithFeedback", "SoldAndPosted", "SoldAndNotPosted",
    ]
    return render_template(
        "orders.html",
        items=items,
        total=total,
        page=page,
        rows=rows,
        status=status,
        statuses=statuses,
        date_from=date_from,
        date_to=date_to,
        total_pages=max(1, -(-total // rows)),
    )


@app.route("/orders/<int:order_id>")
@require_auth
def order_detail(order_id):
    try:
        order = tm.get_order_details(order_id)
    except Exception as e:
        flash(f"Error loading order {order_id}: {e}", "danger")
        return redirect(url_for("orders"))
    return render_template("order_detail.html", order=order)


@app.route("/orders/export")
@require_auth
def orders_export():
    status = request.args.get("status", "All")
    # Fetch up to 200 orders for the export
    try:
        page1 = tm.get_sold_items(status, page=1, rows=200)
        items = page1.get("List") or page1.get("SoldItems") or []
    except Exception as e:
        flash(f"Export failed: {e}", "danger")
        return redirect(url_for("orders"))
    xlsx = export_util.export_orders_to_excel(items)
    return send_file(
        io.BytesIO(xlsx),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"trademe_orders_{status}.xlsx",
    )


# ---------------------------------------------------------------------------
# Listings / Products
# ---------------------------------------------------------------------------

@app.route("/listings")
@require_auth
def listings():
    status = request.args.get("status", "Active")
    page = int(request.args.get("page", 1))
    rows = int(request.args.get("rows", 25))
    try:
        data = tm.get_my_listings(status, page, rows)
        items = data.get("List") or data.get("SellingItems") or []
        total = data.get("TotalCount", 0)
    except Exception as e:
        logging.error(f"Listings error: {e}")
        flash(f"Error loading listings: {e}", "danger")
        items, total = [], 0
    statuses = ["Active", "Unsold", "Sold", "Withdrawn", "Expired"]
    return render_template(
        "listings.html",
        items=items,
        total=total,
        page=page,
        rows=rows,
        status=status,
        statuses=statuses,
        total_pages=max(1, -(-total // rows)),
    )


@app.route("/listings/<int:listing_id>")
@require_auth
def listing_detail(listing_id):
    try:
        listing = tm.get_listing_detail(listing_id)
    except Exception as e:
        flash(f"Error loading listing {listing_id}: {e}", "danger")
        return redirect(url_for("listings"))
    return render_template("listing_detail.html", listing=listing)


@app.route("/listings/<int:listing_id>/withdraw", methods=["POST"])
@require_auth
def listing_withdraw(listing_id):
    reason = request.form.get("reason", "ListedInError")
    try:
        tm.withdraw_listing(listing_id, reason)
        flash(f"Listing {listing_id} withdrawn.", "success")
    except Exception as e:
        flash(f"Failed to withdraw listing: {e}", "danger")
    return redirect(url_for("listings"))


@app.route("/listings/<int:listing_id>/relist", methods=["POST"])
@require_auth
def listing_relist(listing_id):
    try:
        tm.relist_listing(listing_id)
        flash(f"Listing {listing_id} relisted.", "success")
    except Exception as e:
        flash(f"Failed to relist: {e}", "danger")
    return redirect(url_for("listings"))


@app.route("/listings/export")
@require_auth
def listings_export():
    status = request.args.get("status", "Active")
    try:
        data = tm.get_my_listings(status, page=1, rows=200)
        items = data.get("List") or data.get("SellingItems") or []
    except Exception as e:
        flash(f"Export failed: {e}", "danger")
        return redirect(url_for("listings"))
    xlsx = export_util.export_listings_to_excel(items)
    return send_file(
        io.BytesIO(xlsx),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"trademe_listings_{status}.xlsx",
    )


@app.route("/listings/new", methods=["GET", "POST"])
@require_auth
def listing_new():
    if request.method == "POST":
        payload = {
            "Category": request.form["category"],
            "Title": request.form["title"],
            "Description": request.form["description"],
            "BuyNowPrice": float(request.form["buy_now_price"]) if request.form.get("buy_now_price") else None,
            "StartPrice": float(request.form["start_price"]) if request.form.get("start_price") else None,
            "ReservePrice": float(request.form["reserve_price"]) if request.form.get("reserve_price") else None,
            "Duration": int(request.form.get("duration", 7)),
            "Quantity": int(request.form.get("quantity", 1)),
            "IsBrandNew": request.form.get("is_brand_new") == "on",
            "HasBuyNow": bool(request.form.get("buy_now_price")),
        }
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        try:
            result = tm.create_listing(payload)
            flash(f"Listing created! ID: {result.get('ListingId')}", "success")
            return redirect(url_for("listings"))
        except Exception as e:
            flash(f"Failed to create listing: {e}", "danger")
    return render_template("listing_new.html")


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

@app.route("/questions")
@require_auth
def questions():
    page = int(request.args.get("page", 1))
    try:
        data = tm.get_all_questions(page=page, rows=25)
        items = data.get("List") or data.get("Questions") or []
        total = data.get("TotalCount", 0)
    except Exception as e:
        logging.error(f"Questions error: {e}")
        flash(f"Error loading questions: {e}", "danger")
        items, total = [], 0
    return render_template(
        "questions.html",
        items=items,
        total=total,
        page=page,
        total_pages=max(1, -(-total // 25)),
    )


@app.route("/questions/answer", methods=["POST"])
@require_auth
def question_answer():
    listing_id = int(request.form["listing_id"])
    question_id = int(request.form["question_id"])
    answer = request.form["answer"]
    try:
        tm.post_answer(listing_id, question_id, answer)
        flash("Answer posted successfully.", "success")
    except Exception as e:
        flash(f"Failed to post answer: {e}", "danger")
    return redirect(url_for("questions"))


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

@app.route("/feedback")
@require_auth
def feedback():
    page = int(request.args.get("page", 1))
    try:
        data = tm.get_pending_feedback(page=page, rows=25)
        items = data.get("List") or data.get("FeedbackList") or []
        total = data.get("TotalCount", 0)
    except Exception as e:
        logging.error(f"Feedback error: {e}")
        flash(f"Error loading feedback: {e}", "danger")
        items, total = [], 0
    return render_template(
        "feedback.html",
        items=items,
        total=total,
        page=page,
        total_pages=max(1, -(-total // 25)),
    )


@app.route("/feedback/post", methods=["POST"])
@require_auth
def feedback_post():
    feedback_id = int(request.form["feedback_id"])
    comment = request.form["comment"]
    rating = request.form.get("rating", "Positive")
    try:
        tm.post_feedback(feedback_id, comment, rating)
        flash("Feedback posted successfully.", "success")
    except Exception as e:
        flash(f"Failed to post feedback: {e}", "danger")
    return redirect(url_for("feedback"))


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

@app.route("/watchlist")
@require_auth
def watchlist():
    page = int(request.args.get("page", 1))
    try:
        data = tm.get_watchlist(page=page, rows=25)
        items = data.get("List") or data.get("WatchlistItems") or []
        total = data.get("TotalCount", 0)
    except Exception as e:
        logging.error(f"Watchlist error: {e}")
        flash(f"Error loading watchlist: {e}", "danger")
        items, total = [], 0
    return render_template(
        "watchlist.html",
        items=items,
        total=total,
        page=page,
        total_pages=max(1, -(-total // 25)),
    )


# ---------------------------------------------------------------------------
# API proxy (for JS calls)
# ---------------------------------------------------------------------------

@app.route("/api/search-categories")
@require_auth
def api_search_categories():
    try:
        data = tm.get_categories()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Dev tools — live log stream
# ---------------------------------------------------------------------------

@app.route("/dev/logs")
def dev_logs():
    return render_template("dev_logs.html")


@app.route("/dev/logs/stream")
def dev_logs_stream():
    """Server-Sent Events stream of live log lines."""
    def generate():
        yield "data: [Log stream connected — watching live]\n\n"
        while True:
            try:
                line = log_queue.get(timeout=15)
                yield f"data: {line}\n\n"
            except queue.Empty:
                yield "data: [heartbeat]\n\n"
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
