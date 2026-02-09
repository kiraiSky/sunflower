Restaurant Supply Manager
=========================

Lightweight web app for managing supplier orders, basic stock tracking, and a market list.
Designed for phone and computer use.

Features (initial)
------------------
- Users, suppliers, and admin roles (basic role checks)
- Suppliers list and contact details
- Orders per supplier (status, dates, totals)
- Simple stock items with low-stock flag
- Market list for daily purchases

Quick start
-----------
1. Create and activate a virtual environment.
2. Install dependencies.
3. Run the app.

PowerShell:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python -m app.main
```

Open http://127.0.0.1:8000

Notes
-----
- This is a minimal starter. Data is stored in a local SQLite file `data.db`.
- Default admin user is created on first run:
  - username: admin
  - password: admin
