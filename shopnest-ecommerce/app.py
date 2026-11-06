import hashlib
import hmac
import math
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from flask import Flask, g, jsonify, request, session, send_from_directory
import mysql.connector
from mysql.connector import Error as MySQLError, IntegrityError as MySQLIntegrityError

app = Flask(__name__, static_folder="public", static_url_path="")
app.secret_key = os.environ.get("SHOPNEST_SECRET", "shopnest-college-demo-change-me")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7)

DEMO_PRODUCT_IDS = tuple(f"p{i}" for i in range(1, 13))


class Database:
    """Small adapter that keeps route SQL readable with MySQL Connector/Python."""
    def __init__(self):
        self.connection = mysql.connector.connect(
            host=os.environ.get("SHOPNEST_DB_HOST", "127.0.0.1"),
            port=int(os.environ.get("SHOPNEST_DB_PORT", "3306")),
            user=os.environ.get("SHOPNEST_DB_USER", "root"),
            password=os.environ.get("SHOPNEST_DB_PASSWORD", ""),
            database=os.environ.get("SHOPNEST_DB_NAME", "shopnest"),
            autocommit=False,
        )

    @staticmethod
    def _sql(query):
        query = query.replace("INSERT OR REPLACE INTO", "REPLACE INTO")
        query = query.replace("BEGIN IMMEDIATE", "START TRANSACTION")
        return query.replace("?", "%s")

    def execute(self, query, params=None):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(self._sql(query), params or ())
        return cursor

    def executemany(self, query, rows):
        cursor = self.connection.cursor()
        cursor.executemany(self._sql(query), rows)
        return cursor

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def connect_db():
    return Database()


def init_db():
    with connect_db() as conn:
        schema = [
            "CREATE TABLE IF NOT EXISTS users (id VARCHAR(64) PRIMARY KEY, name VARCHAR(100) NOT NULL, email VARCHAR(254) NOT NULL UNIQUE, phone VARCHAR(20) UNIQUE, role VARCHAR(16) NOT NULL, salt VARCHAR(64) NOT NULL, password_hash CHAR(128) NOT NULL, created_at VARCHAR(40) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
            "CREATE TABLE IF NOT EXISTS products (id VARCHAR(64) PRIMARY KEY, name VARCHAR(150) NOT NULL, brand VARCHAR(100) NOT NULL DEFAULT '', category VARCHAR(40) NOT NULL, price DECIMAL(12,2) NOT NULL, old_price DECIMAL(12,2) NOT NULL, rating DECIMAL(3,1) NOT NULL DEFAULT 0, reviews INT NOT NULL DEFAULT 0, emoji VARCHAR(16) NOT NULL DEFAULT '📦', color CHAR(7) NOT NULL DEFAULT '#e9e7ff', badge VARCHAR(40) NOT NULL DEFAULT 'PRODUCT', description TEXT NOT NULL, stock INT NOT NULL DEFAULT 0, image_url VARCHAR(1000) NOT NULL DEFAULT '', is_active TINYINT(1) NOT NULL DEFAULT 1, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
            "CREATE TABLE IF NOT EXISTS orders (id VARCHAR(32) PRIMARY KEY, user_id VARCHAR(64) NOT NULL, address VARCHAR(300) NOT NULL, subtotal DECIMAL(12,2) NOT NULL, shipping DECIMAL(12,2) NOT NULL, total DECIMAL(12,2) NOT NULL, status VARCHAR(20) NOT NULL, payment_method VARCHAR(40) NOT NULL, created_at VARCHAR(40) NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
            "CREATE TABLE IF NOT EXISTS order_items (id BIGINT AUTO_INCREMENT PRIMARY KEY, order_id VARCHAR(32) NOT NULL, product_id VARCHAR(64) NOT NULL, name VARCHAR(150) NOT NULL, price DECIMAL(12,2) NOT NULL, quantity INT NOT NULL, emoji VARCHAR(16) NOT NULL, FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE, FOREIGN KEY (product_id) REFERENCES products(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
            "CREATE TABLE IF NOT EXISTS otp_challenges (phone VARCHAR(20) PRIMARY KEY, code_hash CHAR(64) NOT NULL, expires_at VARCHAR(40) NOT NULL, attempts INT NOT NULL DEFAULT 0, name VARCHAR(100), email VARCHAR(254)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
        ]
        for statement in schema:
            conn.execute(statement)
        product_columns = {row["Field"] for row in conn.execute("SHOW COLUMNS FROM products")}
        if "brand" not in product_columns:
            conn.execute("ALTER TABLE products ADD COLUMN brand VARCHAR(100) NOT NULL DEFAULT ''")
        if "image_url" not in product_columns:
            conn.execute("ALTER TABLE products ADD COLUMN image_url VARCHAR(1000) NOT NULL DEFAULT ''")
        if "is_active" not in product_columns:
            conn.execute("ALTER TABLE products ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1")
        # Hide the previous demo catalog while preserving any order history that references it.
        demo_placeholders = ",".join("?" for _ in DEMO_PRODUCT_IDS)
        conn.execute(f"UPDATE products SET is_active=0 WHERE id IN ({demo_placeholders})", DEMO_PRODUCT_IDS)
        user_columns = {row["Field"] for row in conn.execute("SHOW COLUMNS FROM users")}
        if "phone" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(20) UNIQUE")
        if not conn.execute("SELECT 1 FROM users WHERE email=?", ("admin@shopnest.demo",)).fetchone():
            salt = "shopnest-demo-admin-salt"
            password_hash = hashlib.scrypt(b"Admin123!", salt=salt.encode(), n=2**14, r=8, p=1).hex()
            conn.execute("INSERT INTO users (id,name,email,phone,role,salt,password_hash,created_at) VALUES (?,?,?,?,?,?,?,?)", ("shopnest-demo-admin", "Shopnest Admin", "admin@shopnest.demo", None, "admin", salt, password_hash, now()))


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
    return {key: row[key] for key in ("id", "name", "email", "role", "phone")}


def public_product(row):
    result = as_dict(row)
    result["price"] = float(result["price"])
    result["oldPrice"] = float(result.pop("old_price"))
    result["rating"] = float(result["rating"])
    result["imageUrl"] = result.pop("image_url", "")
    result.pop("is_active", None)
    result.pop("created_at", None)
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
    rows = get_db().execute("SELECT * FROM products WHERE is_active=1 ORDER BY created_at DESC, id").fetchall()
    result = [public_product(row) for row in rows if (not query or query in f"{row['name']} {row['brand']} {row['category']} {row['description']}".lower()) and (category == "All" or row["category"] == category)]
    return jsonify(result)


@app.get("/api/products/<product_id>")
def get_product(product_id):
    row = get_db().execute("SELECT * FROM products WHERE id=? AND is_active=1", (product_id,)).fetchone()
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
    phone = re.sub(r"[\s()-]", "", str(body.get("phone", "")))
    password = str(body.get("password", ""))
    if not 2 <= len(name) <= 60:
        return error("Name must be between 2 and 60 characters.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return error("Enter a valid email address.")
    if not re.fullmatch(r"\+?[1-9]\d{9,14}", phone):
        return error("Enter a valid mobile number with country code, such as +91 98765 43210.")
    if not 8 <= len(password) <= 100:
        return error("Password must be at least 8 characters.")
    conn = get_db()
    if conn.execute("SELECT 1 FROM users WHERE email=? OR phone=?", (email, phone)).fetchone():
        return error("An account with that email or mobile number already exists.", 409)
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=2**14, r=8, p=1).hex()
    user_id = secrets.token_hex(16)
    try:
        conn.execute("INSERT INTO users (id,name,email,phone,role,salt,password_hash,created_at) VALUES (?,?,?,?,?,?,?,?)", (user_id, name, email, phone, "customer", salt, digest, now()))
        conn.commit()
    except MySQLIntegrityError:
        return error("An account with that email or mobile number already exists.", 409)
    session.clear()
    session["user_id"] = user_id
    return jsonify(user={"id": user_id, "name": name, "email": email, "role": "customer", "phone": phone}), 201


@app.post("/api/login")
def login():
    body = request.get_json(silent=True) or {}
    login_id = str(body.get("email", "")).strip().lower()
    if "@" not in login_id:
        login_id = re.sub(r"[\s()-]", "", login_id)
    password = str(body.get("password", ""))
    user = get_db().execute("SELECT * FROM users WHERE email=? OR phone=?", (login_id, login_id)).fetchone()
    if not user or len(password) > 100:
        return error("Email or password is incorrect.", 401)
    candidate = hashlib.scrypt(password.encode(), salt=user["salt"].encode(), n=2**14, r=8, p=1).hex()
    if not hmac.compare_digest(candidate, user["password_hash"]):
        return error("Email or password is incorrect.", 401)
    session.clear()
    session["user_id"] = user["id"]
    return jsonify(user=public_user(user))


def otp_digest(phone, code):
    return hashlib.sha256(f"{app.secret_key}:{phone}:{code}".encode()).hexdigest()


@app.post("/api/auth/request-otp")
def request_otp():
    body = request.get_json(silent=True) or {}
    phone = re.sub(r"[\s()-]", "", str(body.get("phone", "")))
    if not re.fullmatch(r"\+?[1-9]\d{9,14}", phone):
        return error("Enter a valid mobile number with country code, such as +91 98765 43210.")
    name = str(body.get("name", "")).strip()
    email = str(body.get("email", "")).strip().lower()
    conn = get_db()
    existing = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
    if not existing:
        if not 2 <= len(name) <= 60:
            return error("Enter your name to create an account.")
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            return error("Enter a valid email address to create an account.")
        if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            return error("That email belongs to another account. Sign in with that account or use another email.", 409)
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(timespec="seconds")
    conn.execute("INSERT OR REPLACE INTO otp_challenges(phone,code_hash,expires_at,attempts,name,email) VALUES (?,?,?,?,?,?)", (phone, otp_digest(phone, code), expires_at, 0, name, email))
    conn.commit()
    # Demo project: show the code in the response and terminal. Replace with an SMS provider for real use.
    print(f"[Shopnest demo OTP] {phone}: {code} (expires in 5 minutes)")
    result = {"ok": True, "message": "Demo verification code generated. It expires in 5 minutes."}
    if os.environ.get("SHOPNEST_DEMO_OTP", "1") != "0":
        result["demoCode"] = code
    return jsonify(result)


@app.post("/api/auth/verify-otp")
def verify_otp():
    body = request.get_json(silent=True) or {}
    phone = re.sub(r"[\s()-]", "", str(body.get("phone", "")))
    code = str(body.get("code", "")).strip()
    if not re.fullmatch(r"\+?[1-9]\d{9,14}", phone) or not re.fullmatch(r"\d{6}", code):
        return error("Enter your mobile number and six-digit verification code.")
    conn = get_db()
    challenge = conn.execute("SELECT * FROM otp_challenges WHERE phone=?", (phone,)).fetchone()
    if not challenge:
        return error("Request a new verification code first.", 404)
    if datetime.now(timezone.utc) > datetime.fromisoformat(challenge["expires_at"]):
        conn.execute("DELETE FROM otp_challenges WHERE phone=?", (phone,)); conn.commit()
        return error("That code expired. Request a new one.", 400)
    if challenge["attempts"] >= 5:
        conn.execute("DELETE FROM otp_challenges WHERE phone=?", (phone,)); conn.commit()
        return error("Too many attempts. Request a new code.", 429)
    if not hmac.compare_digest(otp_digest(phone, code), challenge["code_hash"]):
        conn.execute("UPDATE otp_challenges SET attempts=attempts+1 WHERE phone=?", (phone,)); conn.commit()
        return error("That code is not correct. Check it and try again.", 400)
    user = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
    created = False
    if not user:
        salt = secrets.token_hex(16)
        temporary_password = secrets.token_urlsafe(32)
        digest = hashlib.scrypt(temporary_password.encode(), salt=salt.encode(), n=2**14, r=8, p=1).hex()
        user_id = secrets.token_hex(16)
        conn.execute("INSERT INTO users (id,name,email,phone,role,salt,password_hash,created_at) VALUES (?,?,?,?,?,?,?,?)", (user_id, challenge["name"], challenge["email"], phone, "customer", salt, digest, now()))
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        created = True
    conn.execute("DELETE FROM otp_challenges WHERE phone=?", (phone,)); conn.commit()
    session.clear(); session["user_id"] = user["id"]
    return jsonify(user=public_user(user), created=created)


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
        order_items.append({"productId": product["id"], "name": product["name"], "price": float(product["price"]), "quantity": quantity, "emoji": product["emoji"]})
    subtotal = round(sum(item["price"] * item["quantity"] for item in order_items), 2)
    shipping = 0 if subtotal >= 2500 else 99
    order_id = "SN-" + secrets.token_hex(4).upper()
    created_at = now()
    try:
        conn.execute("BEGIN IMMEDIATE")
        # Recheck stock under the write lock so concurrent checkouts cannot oversell.
        for item in order_items:
            product = conn.execute("SELECT stock FROM products WHERE id=? FOR UPDATE", (item["productId"],)).fetchone()
            if not product or item["quantity"] > product["stock"]:
                conn.rollback()
                return error("Stock changed while checking out. Please review your bag.")
        conn.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)", (order_id, user["id"], address, subtotal, shipping, round(subtotal + shipping, 2), "Confirmed", "Cash on delivery", created_at))
        for item in order_items:
            changed = conn.execute("UPDATE products SET stock=stock-? WHERE id=? AND stock>=?", (item["quantity"], item["productId"], item["quantity"]))
            if changed.rowcount != 1:
                conn.rollback()
                return error("Stock changed while checking out. Please review your bag.")
            conn.execute("INSERT INTO order_items (order_id,product_id,name,price,quantity,emoji) VALUES (?,?,?,?,?,?)", (order_id, item["productId"], item["name"], item["price"], item["quantity"], item["emoji"]))
        conn.commit()
    except MySQLError:
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
        row["subtotal"] = float(row["subtotal"])
        row["shipping"] = float(row["shipping"])
        row["total"] = float(row["total"])
        row["items"] = [dict(productId=item["product_id"], name=item["name"], price=float(item["price"]), quantity=item["quantity"], emoji=item["emoji"]) for item in conn.execute("SELECT * FROM order_items WHERE order_id=?", (order["id"],))]
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
    return jsonify(products=conn.execute("SELECT COUNT(*) AS total FROM products WHERE is_active=1").fetchone()["total"], orders=conn.execute("SELECT COUNT(*) AS total FROM orders").fetchone()["total"], customers=conn.execute("SELECT COUNT(*) AS total FROM users WHERE role='customer'").fetchone()["total"], revenue=float(conn.execute("SELECT COALESCE(SUM(total),0) AS total FROM orders").fetchone()["total"]))


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
        row["subtotal"] = float(row["subtotal"])
        row["shipping"] = float(row["shipping"])
        row["total"] = float(row["total"])
        row["items"] = [dict(productId=item["product_id"], name=item["name"], price=float(item["price"]), quantity=item["quantity"], emoji=item["emoji"]) for item in conn.execute("SELECT * FROM order_items WHERE order_id=?", (order["id"],))]
        customer = conn.execute("SELECT id,name,email,role,phone FROM users WHERE id=?", (order["user_id"],)).fetchone()
        row["customer"] = public_user(customer)
        result.append(row)
    return jsonify(result)


@app.post("/api/admin/products")
def add_product():
    if not admin_required():
        return error("Admin access required.", 403)
    body = request.get_json(silent=True) or {}
    try:
        name, brand, category = str(body.get("name", "")).strip(), str(body.get("brand", "")).strip(), str(body.get("category", ""))
        description = str(body.get("description", "")).strip()
        price, old_price, stock = float(body.get("price")), float(body.get("oldPrice", body.get("price"))), int(body.get("stock"))
    except (ValueError, TypeError):
        return error("Check the product name, category, description, prices and stock.")
    if not 3 <= len(name) <= 100 or not 1 <= len(brand) <= 100 or not 10 <= len(description) <= 500 or category not in {"Electronics", "Accessories", "Home", "Fashion", "Clothes", "Beauty"} or not math.isfinite(price) or not math.isfinite(old_price) or not 1 <= price <= 1_000_000 or old_price < price or not 0 <= stock <= 10_000:
        return error("Check the product name, category, description, prices and stock.")
    emoji = str(body.get("emoji", "📦"))[:8]
    color = str(body.get("color", "#e9e7ff"))
    image_url = str(body.get("imageUrl", "")).strip()
    parsed_image_url = urlparse(image_url) if image_url else None
    if image_url and (parsed_image_url.scheme not in {"http", "https"} or not parsed_image_url.netloc):
        return error("Product image must be a complete http or https image URL.")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        color = "#e9e7ff"
    product_id = "p" + secrets.token_hex(12)
    product = (product_id, name, brand, category, round(price, 2), round(old_price, 2), 0, 0, emoji, color, "PRODUCT", description, stock, image_url)
    get_db().execute("INSERT INTO products (id,name,brand,category,price,old_price,rating,reviews,emoji,color,badge,description,stock,image_url) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", product)
    get_db().commit()
    return jsonify(dict(zip(("id", "name", "brand", "category", "price", "oldPrice", "rating", "reviews", "emoji", "color", "badge", "description", "stock", "imageUrl"), product))), 201


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
    # Listen on all interfaces so VS Code port forwarding / Dev Tunnels can reach Flask.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8082")), debug=os.environ.get("FLASK_DEBUG") == "1")
