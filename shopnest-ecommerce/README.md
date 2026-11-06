# Shopnest — Python E-commerce Major Project

Shopnest is a full-stack, responsive e-commerce web app built with **Python, Flask, SQLite, HTML, CSS and JavaScript**. It is designed as a locally runnable college project. The storefront, API, accounts, inventory and orders run locally without paid services or an external database.

## Requirements

- Python 3.10 or newer. If `py --version` says **No installed Python found**, install Python from [python.org](https://www.python.org/downloads/) and enable **Add python.exe to PATH**, then restart VS Code.
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

6. The server listens on port **8082**. Open **http://127.0.0.1:8082** locally. In VS Code, open the **Ports** panel and forward port `8082`; use the forwarded URL for a Dev Tunnel. Stop the server with **Ctrl+C**.

If the browser shows **502 Bad Gateway**, first confirm the terminal still shows Flask running. The tunnel must forward port `8082`, and Python plus Flask must be installed. `python app.py` should print that it is listening on port `8082`.

## Git push message: `src refspec main does not match any`

This Git error is separate from running the website. It means your local repository does not have a branch named `main` (or has no commit on that branch). In the supplied screenshot, VS Code shows the current branch is `feature-monitor`. To push that current branch, commit your changes if needed, then run:

```bash
git add .
git commit -m "Add Shopnest e-commerce project"
git push -u origin feature-monitor
```

If the commit was already created, skip the first two commands and run only the `git push` command. You can check the current branch with `git branch --show-current`.

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
