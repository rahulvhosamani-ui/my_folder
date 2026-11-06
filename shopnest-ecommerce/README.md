# Shopnest — Python and MySQL E-commerce Major Project

Shopnest is a responsive full-stack e-commerce project built with Python, Flask, MySQL, HTML, CSS and JavaScript. It includes a customer storefront, mobile OTP demo sign-in, shopping cart, checkout, inventory and an administrator dashboard.

## Requirements

- Python 3.10 or newer
- MySQL Server 8 or newer, running on this computer
- VS Code (recommended)

## 1. Create the MySQL database

Open MySQL Shell and connect to your local server. `roothost` is not the local hostname. Use your MySQL account name and the host `localhost`, for example:

```text
\connect root@localhost
```

Enter the MySQL password when prompted. Then create the app database:

```sql
CREATE DATABASE shopnest CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

The supplied `setup.sql` contains the same database creation statement. The app creates its tables and demo products automatically on first start.

## 2. Start the Flask app from VS Code (Windows PowerShell)

Open the extracted `shopnest-ecommerce` folder in VS Code, then open **Terminal → New Terminal**. Run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SHOPNEST_DB_HOST = "127.0.0.1"
$env:SHOPNEST_DB_PORT = "3306"
$env:SHOPNEST_DB_USER = "root"
$env:SHOPNEST_DB_PASSWORD = Read-Host "MySQL password"
$env:SHOPNEST_DB_NAME = "shopnest"
.\.venv\Scripts\python.exe app.py
```

Then open **http://127.0.0.1:8082**. Keep the terminal open while using the site. Stop Flask with **Ctrl+C**. For a VS Code Dev Tunnel, forward port `8082` in the Ports panel.

If the site reports a database connection error, make sure MySQL Server is running, the `shopnest` database exists, and the username/password environment variables match your MySQL login.

## Features

- Responsive storefront with product search, working categories and product detail dialogs
- Working quick-add buttons, cart drawer, quantity controls and stock validation
- Mobile number registration and OTP sign-in, with a five-minute code and five-attempt limit
- Customer email/password sign-in remains available; admin demo login is listed below
- Checkout with delivery address and cash on delivery
- MySQL persistence for customers, products, OTP challenges and orders
- Administrator dashboard with sales summary, inventory, order status updates and product creation
- Inventory locking and stock updates during checkout
- Navigation menu, newsletter demo subscription and responsive layouts

## Demo administrator account

- Email: `admin@shopnest.demo`
- Password: `Admin123!`

The seeded admin account uses email/password. For normal customers, create an account or sign in with a mobile OTP.

## OTP demo note

This college project does not connect to an SMS gateway. By default, the six-digit test code appears in the sign-in dialog and the Flask terminal, so the flow can be demonstrated locally. The code expires after five minutes and has five attempts. To hide the code in the page, set `SHOPNEST_DEMO_OTP=0`; connect an SMS provider before using OTP outside the demo.

## Project layout

```text
shopnest-ecommerce/
├── app.py                 # Flask API, account/OTP flow and MySQL data layer
├── public/
│   ├── app.js             # Storefront interactions and API client
│   ├── index.html         # Storefront, sign-in, OTP, checkout and admin dialogs
│   └── styles.css         # Responsive design
├── requirements.txt       # Flask and MySQL Connector/Python
├── setup.sql              # Creates the shopnest database
└── README.md
```

## Security and presentation notes

This is a local academic demonstration, not a production deployment. The demo admin password is public by design, the OTP code is revealed in demo mode, and Flask's default signed-cookie sessions are used. For production, configure a private `SHOPNEST_SECRET`, add CSRF protection and rate limiting, use HTTPS and a production WSGI server, and integrate an SMS service and payment gateway.

Suggested viva topics: Flask routes, REST APIs, relational database design, password hashing with `scrypt`, OTP expiry and attempt limits, session authentication, inventory transactions, foreign keys, and admin role checks.
