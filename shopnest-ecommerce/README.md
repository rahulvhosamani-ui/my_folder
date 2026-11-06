# Shopnest — Python E-commerce Major Project

Shopnest is a full-stack, responsive e-commerce web app built with **Python, Flask, SQLite, HTML, CSS and JavaScript**. It is designed as a locally runnable college project. The storefront, API, accounts, inventory and orders run locally without paid services or an external database.

## Requirements

- Python 3.10 or newer
- VS Code (recommended)

## Run in VS Code on Windows

1. Extract the ZIP, then open the extracted `shopnest-ecommerce` folder in VS Code.
2. Open **Terminal → New Terminal**.
3. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt in VS Code and run:

   ```bat
   .venv\Scripts\activate.bat
   ```

4. Install the Python package:

   ```bash
   python -m pip install -r requirements.txt
   ```

5. Start the app:

   ```bash
   python app.py
   ```

6. Open **http://127.0.0.1:3000** in your browser. Stop the server with **Ctrl+C**.

## Demo administrator

- Email: `admin@shopnest.demo`
- Password: `Admin123!`

Sign in with this account to open the admin dashboard. You can inspect orders, update order status and add products. New customers can create accounts from the sign-in dialog.

## Features

- Responsive storefront with search, category filters, product ratings and sale prices
- Shopping bag with quantity controls, stock checks and free-shipping progress
- Customer registration and sign-in with salted `scrypt` password hashes
- Checkout with delivery address and cash-on-delivery selection
- Persistent SQLite database at `data/shopnest.db`, created automatically on first run
- Admin dashboard with sales summary, order status changes and product creation
- Inventory reduction after checkout and restoration if an order is cancelled
- No payment gateway or external database needed for the local demonstration

## Project layout

```text
shopnest-ecommerce/
├── app.py                 # Flask app, REST API, authentication and SQLite data layer
├── data/                  # SQLite database is created here on first run
├── public/
│   ├── app.js             # Storefront interactions and API client
│   ├── index.html         # Storefront and account/admin dialogs
│   └── styles.css         # Responsive design
├── requirements.txt       # Python dependencies
└── README.md
```

## Notes for a college presentation

This is an academic demonstration, not a production commerce deployment. The demo administrator password is public by design, and Flask's default signed-cookie session is used. Before real deployment, configure a private `SHOPNEST_SECRET`, use HTTPS and production hosting, add CSRF protection and rate limiting, and connect a real payment provider. The app can use a different database file by setting `SHOPNEST_DB`.

### Suggested viva topics

- Flask routes and client/server architecture
- Password hashing with `hashlib.scrypt` and signed cookie sessions
- Product search and category filtering
- Cart calculation, shipping rules and inventory validation
- SQLite relational tables, foreign keys and transactions
- Order lifecycle and admin role checks
- How the local database can be hosted or extended
