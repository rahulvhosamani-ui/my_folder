# Shopnest — Python and MySQL E-commerce Major Project

Shopnest is a responsive product catalogue built with Python, Flask, MySQL, HTML, CSS and JavaScript. Admins add the real products, brands, prices and image links they want to display. The public site has search and product details, with no cart or purchase flow.

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

The supplied `setup.sql` contains the same database creation statement. The app creates its tables automatically on first start. It does not add sample product listings.

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

- Responsive catalogue with search by product name, brand, category or description
- Working category filters, including a dedicated **Clothes** filter, and product detail dialogs
- Mobile search expands from the magnifying glass button
- Admin can add genuine products with brand, category, price, optional compare-at price, stock, description and direct photo URL
- No demo product listings are seeded; older demo products with IDs `p1`–`p12` are hidden on startup
- Mobile number registration and OTP sign-in, with a five-minute code and five-attempt limit
- Customer email/password sign-in remains available; admin demo login is listed below
- MySQL persistence for customers, product listings and OTP challenges
- Administrator dashboard to add and review catalogue listings
- Navigation menu and responsive layouts

## Demo administrator account

- Email: `admin@shopnest.demo`
- Password: `Admin123!`

The demo admin account uses email/password. Sign in, open the admin dashboard, select **Add a product**, then enter the product name, brand, category, real price and description. Paste a direct image URL if you want a product photo. Save it and the product appears in the catalogue. Search works against products you have added.

## OTP demo note

This college project does not connect to an SMS gateway. By default, the six-digit test code appears in the sign-in dialog and the Flask terminal, so the flow can be demonstrated locally. The code expires after five minutes and has five attempts. To hide the code in the page, set `SHOPNEST_DEMO_OTP=0`; connect an SMS provider before using OTP outside the demo.

## Project layout

```text
shopnest-ecommerce/
├── app.py                 # Flask API, account/OTP flow and MySQL data layer
├── public/
│   ├── app.js             # Storefront interactions and API client
│   ├── index.html         # Catalogue, sign-in, OTP and admin dialogs
│   └── styles.css         # Responsive design
├── requirements.txt       # Flask and MySQL Connector/Python
├── setup.sql              # Creates the shopnest database
└── README.md
```

## Security and presentation notes

This is a local academic demonstration, not a production deployment. The demo admin password is public by design, the OTP code is revealed in demo mode, and Flask's default signed-cookie sessions are used. For production, configure a private `SHOPNEST_SECRET`, add CSRF protection and rate limiting, use HTTPS and a production WSGI server, and integrate an SMS service.

Suggested viva topics: Flask routes, REST APIs, relational database design, password hashing with `scrypt`, OTP expiry and attempt limits, session authentication, inventory transactions, foreign keys, and admin role checks.
