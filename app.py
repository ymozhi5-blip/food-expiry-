
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import date, datetime, timedelta
from pathlib import Path
from werkzeug.utils import secure_filename
import json
import uuid
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-key")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
INVENTORY_FILE = DATA_DIR / "inventory.json"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
if not INVENTORY_FILE.exists():
    INVENTORY_FILE.write_text("[]", encoding="utf-8")


def load_items():
    try:
        return json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_items(items):
    INVENTORY_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")


def expiry_status(item):
    try:
        expiry = date.fromisoformat(item["expiry_date"])
    except (KeyError, ValueError, TypeError):
        return "unknown", None

    days = (expiry - date.today()).days

    if days < 0:
        return "expired", days
    if days <= 7:
        return "soon", days
    return "fresh", days


def enrich_items(items):
    enriched = []

    for original in items:
        item = dict(original)
        status, days = expiry_status(item)
        item["status"] = status
        item["days_left"] = days
        enriched.append(item)

    return enriched


def cleanup_expired():
    """Archive items more than 24 hours after their expiry date."""
    items = load_items()
    keep, removed = [], []
    now = datetime.now()

    for item in items:
        try:
            expiry = datetime.combine(
                date.fromisoformat(item["expiry_date"]),
                datetime.min.time()
            )

            if now > expiry + timedelta(hours=24):
                removed.append(item)
            else:
                keep.append(item)

        except (KeyError, ValueError, TypeError):
            keep.append(item)

    if removed:
        history_file = DATA_DIR / "history.json"

        try:
            history = json.loads(
                history_file.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            history = []

        for item in removed:
            item["archived_at"] = now.isoformat(timespec="seconds")
            history.append(item)

        history_file.write_text(
            json.dumps(history, indent=2),
            encoding="utf-8"
        )
        save_items(keep)

    return keep


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def get_recipes(items):
    names = {i.get("name", "").lower() for i in items}

    ideas = [
        ({"tomato", "onion"}, "Tomato and onion stir-fry",
         "Use tomatoes and onions with a little oil and seasoning."),
        ({"milk", "banana"}, "Banana milk smoothie",
         "Blend banana and milk until smooth."),
        ({"bread", "cheese"}, "Cheese toast",
         "Top bread with cheese and toast until melted."),
        ({"egg", "tomato"}, "Tomato omelette",
         "Cook beaten eggs with chopped tomato."),
        ({"potato", "onion"}, "Potato and onion skillet",
         "Cook diced potatoes and onions until tender."),
    ]

    suggestions = []

    for ingredients, title, description in ideas:
        found = sorted(ingredients.intersection(names))

        if found:
            suggestions.append({
                "title": title,
                "description": description,
                "ingredients": found
            })

    return suggestions[:4]


@app.route("/")
def index():
    cleanup_expired()
    items = enrich_items(load_items())

    items.sort(
        key=lambda x: (
            x.get("expiry_date", "9999-12-31"),
            x.get("name", "").lower()
        )
    )

    stats = {
        "total": len(items),
        "soon": sum(1 for x in items if x["status"] == "soon"),
        "expired": sum(1 for x in items if x["status"] == "expired"),
    }

    alerts = []

    for item in items:
        if item["days_left"] is None:
            continue

        if item["days_left"] == 7:
            alerts.append({
                "level": "warning",
                "message": f'{item["name"]} expires in 7 days.'
            })

        elif item["days_left"] == 0:
            alerts.append({
                "level": "danger",
                "message": (
                    f'{item["name"]} reaches its expiry date today. '
                    "Check the label and condition before use."
                )
            })

        elif 0 < item["days_left"] < 7:
            alerts.append({
                "level": "warning",
                "message": (
                    f'{item["name"]} expires in {item["days_left"]} day(s).'
                )
            })

        elif item["days_left"] < 0:
            alerts.append({
                "level": "danger",
                "message": (
                    f'{item["name"]} is past its recorded expiry date. '
                    "Do not assume it is safe to consume."
                )
            })

    return render_template(
        "index.html",
        items=items,
        stats=stats,
        alerts=alerts,
        recipes=get_recipes(items),
        today=date.today().isoformat()
    )


@app.route("/add", methods=["POST"])
def add_item():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Other").strip()
    purchase_date = (
        request.form.get("purchase_date", "").strip()
        or date.today().isoformat()
    )
    expiry_date = request.form.get("expiry_date", "").strip()
    quantity = request.form.get("quantity", "1").strip()
    storage = request.form.get("storage", "Room temperature").strip()
    notes = request.form.get("notes", "").strip()

    if not name or not expiry_date:
        flash("Please enter a product name and expiry date.", "error")
        return redirect(url_for("index"))

    try:
        date.fromisoformat(purchase_date)
        date.fromisoformat(expiry_date)
    except ValueError:
        flash("Please enter valid dates.", "error")
        return redirect(url_for("index"))

    photo_name = ""
    photo = request.files.get("photo")

    if photo and photo.filename:
        if not allowed_file(photo.filename):
            flash("Photo must be PNG, JPG, JPEG, or WEBP.", "error")
            return redirect(url_for("index"))

        suffix = photo.filename.rsplit(".", 1)[1].lower()
        photo_name = f"{uuid.uuid4().hex}.{suffix}"
        photo.save(UPLOAD_DIR / secure_filename(photo_name))

    items = load_items()

    items.append({
        "id": uuid.uuid4().hex,
        "name": name,
        "category": category,
        "purchase_date": purchase_date,
        "expiry_date": expiry_date,
        "quantity": quantity,
        "storage": storage,
        "notes": notes,
        "photo": photo_name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "expiry_source": "user-entered"
    })

    save_items(items)
    flash(f"{name} added to your inventory.", "success")
    return redirect(url_for("index"))


@app.route("/delete/<item_id>", methods=["POST"])
def delete_item(item_id):
    items = load_items()
    remaining = [item for item in items if item.get("id") != item_id]

    if len(remaining) == len(items):
        flash("Item not found.", "error")
    else:
        save_items(remaining)
        flash("Food item removed from inventory.", "success")

    return redirect(url_for("index"))


@app.route("/feedback/<item_id>", methods=["POST"])
def feedback(item_id):
    outcome = request.form.get("outcome", "").strip()

    if outcome not in {"used", "discarded", "still_have"}:
        flash("Choose a valid feedback option.", "error")
        return redirect(url_for("index"))

    items = load_items()
    target = next(
        (i for i in items if i.get("id") == item_id),
        None
    )

    if not target:
        flash("Item not found.", "error")
        return redirect(url_for("index"))

    file = DATA_DIR / "feedback.json"

    try:
        records = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        records = []

    records.append({
        "item_id": item_id,
        "item_name": target.get("name"),
        "outcome": outcome,
        "recorded_at": datetime.now().isoformat(timespec="seconds")
    })

    file.write_text(json.dumps(records, indent=2), encoding="utf-8")
    flash(
        "Feedback saved. This starter records outcomes but does not "
        "train an ML model yet.",
        "success"
    )

    return redirect(url_for("index"))


@app.route("/api/items")
def api_items():
    cleanup_expired()
    return jsonify(enrich_items(load_items()))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "FreshTrack Starter"})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=True
    )
