import hashlib
import hmac
import math
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g, jsonify, request, session, send_from_directory

ROOT = Path(__file__).resolve().parent
DB_FILE = Path(os.environ.get("SHOPNEST_DB", ROOT / "data" / "shopnest.db"))
app = Flask(__name__, static_folder="public", static_url_path="")
app.secret_key = os.environ.get("SHOPNEST_SECRET", "shopnest-college-demo-change-me")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7)

SEED_PRODUCTS = [
    ("p1", "Studio Wireless Headphones", "Electronics", 3499, 4499, 4.8, 128, "🎧", "#e6e8ff", "BESTSELLER", "Immersive sound, soft memory-foam ear cups and up to 30 hours of battery life.", 18),
    ("p2", "Everyday Canvas Backpack", "Accessories", 1899, 2399, 4.6, 86, "🎒", "#f6e5d8", "POPULAR", "A thoughtful everyday carry with a padded laptop sleeve and water-resistant canvas.", 24),
    ("p3", "Minimal Ceramic Table Lamp", "Home", 2299, 2799, 4.7, 54, "💡", "#f6eac8", "NEW", "Warm, gentle light in a sculptural ceramic design made for quiet evenings.", 12),
    ("p4", "Active Move Smart Watch", "Electronics", 4299, 5499, 4.5, 203, "⌚", "#dceef0", "SALE", "Track your movement, sleep and heart rate with a bright, easy-to-read display.", 15),
    ("p5", "Cloud Knit Everyday Sneakers", "Fashion", 2799, 3499, 4.9, 171, "👟", "#e7e3dc", "TOP RATED", "Lightweight knit sneakers with a cushioned sole for wherever the day takes you.", 20),
    ("p6", "Botanical Skincare Set", "Beauty", 1599, 1999, 4.7, 92, "🧴", "#e3f0e3", "GENTLE CARE", "A simple three-step plant-based routine: cleanse, hydrate and restore.", 30),
    ("p7", "Pour-Over Coffee Starter Kit", "Home", 1299, 1699, 4.6, 67, "☕", "#f1dfd1", "GIFT PICK", "Everything you need for a slow, delicious morning ritual, in one tidy kit.", 17),
    ("p8", "Pocket Bluetooth Speaker", "Electronics", 1999, 2599, 4.4, 119, "🔊", "#e1e6f2", "COMPACT", "Big, clear sound in a pocket-friendly, splash-resistant little package.", 22),
]


def connect_db():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with connect_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('customer','admin')),
                salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
                price REAL NOT NULL, old_price REAL NOT NULL, rating REAL NOT NULL,
                reviews INTEGER NOT NULL, emoji TEXT NOT NULL, color TEXT NOT NULL,
                badge TEXT NOT NULL, description TEXT NOT NULL, stock INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                address TEXT NOT NULL, subtotal REAL NOT NULL, shipping REAL NOT NULL,
                total REAL NOT NULL, status TEXT NOT NULL, payment_method TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_id TEXT NOT NULL, name TEXT NOT NULL, price REAL NOT NULL,
                quantity INTEGER NOT NULL, emoji TEXT NOT NULL
            );
        """)
        if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            conn.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", SEED_PRODUCTS)
        if not conn.execute("SELECT 1 FROM users WHERE email=?", ("admin@shopnest.demo",)).fetchone():
            salt = "shopnest-demo-admin-salt"
            password_hash = hashlib.scrypt(b"Admin123!", salt=salt.encode(), n=2**14, r=8, p=1).hex()
            conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?)", ("shopnest-demo-admin", "Shopnest Admin", "admin@shopnest.demo", "admin", salt, password_hash, now()))


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db():
    if "db" not in g:
        g.db = connect_db()
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def as_dict(row):
    return dict(row) if row is not None else None


def public_user(row):
    return {key: row[key] for key in ("id", "name", "email", "role")}


def public_product(row):
    result = as_dict(row)
    result["oldPrice"] = result.pop("old_price")
    return result


def error(message, status=400):
    return jsonify(error=message), status


def signed_in_user():
    if not session.get("user_id"):
        return None
    return get_db().execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()


def admin_required():
    user = signed_in_user()
    if not user or user["role"] != "admin":
        return None
    return user


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/products")
def list_products():
    query = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "All")
    rows = get_db().execute("SELECT * FROM products ORDER BY rowid DESC").fetchall()
    result = [public_product(row) for row in rows if (not query or query in f"{row['name']} {row['category']} {row['description']}".lower()) and (category == "All" or row["category"] == category)]
    return jsonify(result)


@app.get("/api/products/<product_id>")
def get_product(product_id):
    row = get_db().execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    return (jsonify(public_product(row)) if row else error("Product not found.", 404))


@app.get("/api/me")
def me():
    user = signed_in_user()
    return jsonify(user=public_user(user) if user else None)


@app.post("/api/register")
def register():
    body = request.get_json(silent=True) or {}
    name = str(body.get("name", "")).strip()
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    if not 2 <= len(name) <= 60:
        return error("Name must be between 2 and 60 characters.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return error("Enter a valid email address.")
    if not 8 <= len(password) <= 100:
        return error("Password must be at least 8 characters.")
    conn = get_db()
    if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        return error("An account with that email already exists.", 409)
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=2**14, r=8, p=1).hex()
    user_id = secrets.token_hex(16)
    try:
        conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?)", (user_id, name, email, "customer", salt, digest, now()))
        conn.commit()
    except sqlite3.IntegrityError:
        return error("An account with that email already exists.", 409)
    session.clear()
    session["user_id"] = user_id
    return jsonify(user={"id": user_id, "name": name, "email": email, "role": "customer"}), 201


@app.post("/api/login")
def login():
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user or len(password) > 100:
        return error("Email or password is incorrect.", 401)
    candidate = hashlib.scrypt(password.encode(), salt=user["salt"].encode(), n=2**14, r=8, p=1).hex()
    if not hmac.compare_digest(candidate, user["password_hash"]):
        return error("Email or password is incorrect.", 401)
    session.clear()
    session["user_id"] = user["id"]
    return jsonify(user=public_user(user))


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.post("/api/orders")
def create_order():
    user = signed_in_user()
    if not user:
        return error("Please sign in to continue.", 401)
    body = request.get_json(silent=True) or {}
    items = body.get("items") if isinstance(body.get("items"), list) else []
    address = str(body.get("address", "")).strip()
    if not items or len(items) > 30:
        return error("Your cart is empty.")
    if not 8 <= len(address) <= 300:
        return error("Enter a delivery address (8–300 characters).")
    quantities = {}
    for item in items:
        try:
            product_id, quantity = str(item.get("id", "")), int(item.get("quantity", 0))
        except (ValueError, TypeError, AttributeError):
            return error("One or more cart quantities are invalid.")
        if quantity < 1 or quantity > 20:
            return error("One or more cart quantities are invalid.")
        quantities[product_id] = quantities.get(product_id, 0) + quantity
    conn = get_db()
    order_items = []
    for product_id, quantity in quantities.items():
        product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if not product:
            return error("A product in your cart is no longer available.")
        if quantity > product["stock"]:
            return error(f"Only {product['stock']} × {product['name']} currently in stock.")
        order_items.append({"productId": product["id"], "name": product["name"], "price": product["price"], "quantity": quantity, "emoji": product["emoji"]})
    subtotal = round(sum(item["price"] * item["quantity"] for item in order_items), 2)
    shipping = 0 if subtotal >= 2500 else 99
    order_id = "SN-" + secrets.token_hex(4).upper()
    created_at = now()
    try:
        conn.execute("BEGIN IMMEDIATE")
        # Recheck stock under the write lock so concurrent checkouts cannot oversell.
        for item in order_items:
            product = conn.execute("SELECT stock FROM products WHERE id=?", (item["productId"],)).fetchone()
            if not product or item["quantity"] > product["stock"]:
                conn.rollback()
                return error("Stock changed while checking out. Please review your bag.")
        conn.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)", (order_id, user["id"], address, subtotal, shipping, round(subtotal + shipping, 2), "Confirmed", "Cash on delivery", created_at))
        for item in order_items:
            conn.execute("INSERT INTO order_items (order_id,product_id,name,price,quantity,emoji) VALUES (?,?,?,?,?,?)", (order_id, item["productId"], item["name"], item["price"], item["quantity"], item["emoji"]))
            conn.execute("UPDATE products SET stock=stock-? WHERE id=?", (item["quantity"], item["productId"]))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        return error("Could not place your order. Please try again.", 500)
    order = {"id": order_id, "userId": user["id"], "items": order_items, "address": address, "subtotal": subtotal, "shipping": shipping, "total": round(subtotal + shipping, 2), "status": "Confirmed", "paymentMethod": "Cash on delivery", "createdAt": created_at}
    return jsonify(order=order), 201


def orders_for_user(user_id):
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    result = []
    for order in orders:
        row = as_dict(order)
        row["userId"] = row.pop("user_id")
        row["paymentMethod"] = row.pop("payment_method")
        row["createdAt"] = row.pop("created_at")
        row["items"] = [dict(productId=item["product_id"], name=item["name"], price=item["price"], quantity=item["quantity"], emoji=item["emoji"]) for item in conn.execute("SELECT * FROM order_items WHERE order_id=?", (order["id"],))]
        result.append(row)
    return result


@app.get("/api/orders")
def list_orders():
    user = signed_in_user()
    if not user:
        return error("Please sign in to continue.", 401)
    return jsonify(orders_for_user(user["id"]))


@app.get("/api/admin/summary")
def admin_summary():
    if not admin_required():
        return error("Admin access required.", 403)
    conn = get_db()
    return jsonify(products=conn.execute("SELECT COUNT(*) FROM products").fetchone()[0], orders=conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0], customers=conn.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0], revenue=conn.execute("SELECT COALESCE(SUM(total),0) FROM orders").fetchone()[0])


@app.get("/api/admin/orders")
def admin_orders():
    if not admin_required():
        return error("Admin access required.", 403)
    conn = get_db()
    result = []
    for order in conn.execute("SELECT * FROM orders ORDER BY created_at DESC"):
        row = as_dict(order)
        row["userId"] = row.pop("user_id")
        row["paymentMethod"] = row.pop("payment_method")
        row["createdAt"] = row.pop("created_at")
        row["items"] = [dict(productId=item["product_id"], name=item["name"], price=item["price"], quantity=item["quantity"], emoji=item["emoji"]) for item in conn.execute("SELECT * FROM order_items WHERE order_id=?", (order["id"],))]
        customer = conn.execute("SELECT id,name,email,role FROM users WHERE id=?", (order["user_id"],)).fetchone()
        row["customer"] = public_user(customer)
        result.append(row)
    return jsonify(result)


@app.post("/api/admin/products")
def add_product():
    if not admin_required():
        return error("Admin access required.", 403)
    body = request.get_json(silent=True) or {}
    try:
        name, category = str(body.get("name", "")).strip(), str(body.get("category", ""))
        description = str(body.get("description", "")).strip()
        price, old_price, stock = float(body.get("price")), float(body.get("oldPrice", body.get("price"))), int(body.get("stock"))
    except (ValueError, TypeError):
        return error("Check the product name, category, description, prices and stock.")
    if not 3 <= len(name) <= 100 or not 10 <= len(description) <= 500 or category not in {"Electronics", "Accessories", "Home", "Fashion", "Beauty"} or not math.isfinite(price) or not math.isfinite(old_price) or not 1 <= price <= 1_000_000 or old_price < price or not 0 <= stock <= 10_000:
        return error("Check the product name, category, description, prices and stock.")
    emoji = str(body.get("emoji", "📦"))[:8]
    color = str(body.get("color", "#e9e7ff"))
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        color = "#e9e7ff"
    product_id = "p" + secrets.token_hex(12)
    product = (product_id, name, category, round(price, 2), round(old_price, 2), 5, 0, emoji, color, "NEW", description, stock)
    get_db().execute("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", product)
    get_db().commit()
    return jsonify(dict(zip(("id", "name", "category", "price", "oldPrice", "rating", "reviews", "emoji", "color", "badge", "description", "stock"), product))), 201


@app.patch("/api/admin/orders/<order_id>")
def change_order_status(order_id):
    if not admin_required():
        return error("Admin access required.", 403)
    body = request.get_json(silent=True) or {}
    status = body.get("status")
    allowed = {"Confirmed", "Packed", "Shipped", "Delivered", "Cancelled"}
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        return error("Order not found.", 404)
    if status not in allowed:
        return error("Invalid order status.")
    if order["status"] == "Cancelled" and status != "Cancelled":
        return error("A cancelled order cannot be reopened.")
    if status == "Cancelled" and order["status"] != "Cancelled":
        conn.execute("UPDATE products SET stock=stock+(SELECT quantity FROM order_items WHERE order_id=? AND product_id=products.id) WHERE id IN (SELECT product_id FROM order_items WHERE order_id=?)", (order_id, order_id))
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    return jsonify(id=order_id, status=status)


@app.get("/<path:filename>")
def static_files(filename):
    return send_from_directory(app.static_folder, filename)


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "3000")), debug=os.environ.get("FLASK_DEBUG") == "1")
