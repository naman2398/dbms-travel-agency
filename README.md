# Travel Agency Booking System

A full-stack travel booking web app (inspired by Kayak/Expedia) built with Flask and PostgreSQL. Users can search destinations, browse flights, hotels, and activities, then complete a multi-step booking with payment.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Flask 3.0.3 |
| Database | PostgreSQL, psycopg2-binary 2.9.9 |
| Frontend | HTML5, Jinja2, custom CSS |
| Data seeding | Faker 25.0.0 |

## Features

- **Multi-step booking wizard** — Search → Browse → Plan → Confirm → Success
- **Trip search** — Filter by origin/destination, dates, group size, and trip purpose
- **Browse options** — 10 cheapest flights, hotels, and all available activities at destination
- **Group bookings** — Supports 1–20 travelers per trip
- **My Bookings** — Look up all past trips by passenger email
- **Atomic transactions** — Full booking commits or rolls back on error

## Project Structure

```
travel_agency/
├── app.py              # Flask routes and DB logic
├── schema.sql          # PostgreSQL schema (13 tables)
├── seed_data.py        # Generates ~50 rows per table using Faker
├── queries.sql         # 10 complex analytical SQL queries
├── query_results.txt   # Sample output from queries.sql
├── requirements.txt    # Python dependencies
└── templates/
    ├── base.html       # Shared layout and styles
    ├── search.html     # Step 1: search form
    ├── browse.html     # Step 2: available options
    ├── plan.html       # Step 3: review selections
    ├── confirm.html    # Step 4: passenger details + payment
    └── my_bookings.html
```

## Database Schema

13 tables organized around a central `trip_group` entity:

**Core tables:** `location`, `passenger`, `employee`, `transportation`, `accommodation`, `activity`

**Junction tables:** `trip_group`, `group_passenger`, `group_transportation`, `group_accommodation`, `group_activity`

**Transactional:** `payment`, `review`

Notable design patterns:
- Polymorphic `transportation` table handles Flights, Cruises, Car Rentals, and Buses via a type discriminator with per-type CHECK constraints
- `review` uses an XOR constraint — a review targets either an accommodation or a transportation, never both
- `employee` has a self-referencing supervisor hierarchy
- PCI-DSS compliance: only last 4 card digits are stored
- 16 indexes on frequently-joined columns; all junction tables cascade-delete on parent removal

## Setup

### 1. Install PostgreSQL

**macOS (Homebrew)**
```bash
brew install postgresql@16
brew services start postgresql@16

# Add to PATH (add this line to ~/.zshrc or ~/.bash_profile)
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
```

**Ubuntu / Debian**
```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Windows**

1. Download the installer from [postgresql.org/download/windows](https://www.postgresql.org/download/windows)
2. Run the installer — keep the default port `5432` and set a password for the `postgres` user
3. When prompted, install **pgAdmin** and **Command Line Tools** (both checked by default)
4. Add PostgreSQL to your PATH so `psql` works from any terminal:
   - Search **Environment Variables** in the Start menu → **Edit the system environment variables**
   - Under **System variables**, find `Path` → **Edit** → **New**
   - Add: `C:\Program Files\PostgreSQL\16\bin` (adjust version number if different)
   - Click OK and restart your terminal

Verify it works by opening **Command Prompt** or **PowerShell**:
```powershell
psql -U postgres -c "SELECT version();"
```

---

### 2. Create the database

**macOS / Linux**
```bash
psql -U postgres -c "CREATE DATABASE travel_agency;"
```

**Windows (Command Prompt / PowerShell)**
```powershell
psql -U postgres -c "CREATE DATABASE travel_agency;"
```

> On Linux you may need to prefix with `sudo -u postgres` — e.g. `sudo -u postgres psql`.

Verify the connection works:

**macOS / Linux**
```bash
psql -U postgres -d travel_agency -c "SELECT version();"
```

**Windows**
```powershell
psql -U postgres -d travel_agency -c "SELECT version();"
```

---

### 3. Configure the connection

The connection is set in both `app.py` and `seed_data.py`. The defaults work out of the box if you used `postgres` as the username and password during installation:

```python
DB_CONFIG = {
    "dbname": "travel_agency",
    "user": "postgres",
    "password": "postgres",   # change if you set a different password
    "host": "localhost",
    "port": 5432,
}
```

If your password differs, update the `password` field in both files before proceeding.

---

### 4. Install Python dependencies

**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (Command Prompt)**
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once first.

---

### 5. Apply schema and seed data

**macOS / Linux**
```bash
psql -U postgres -d travel_agency -f schema.sql
python seed_data.py
```

**Windows**
```powershell
psql -U postgres -d travel_agency -f schema.sql
python seed_data.py
```

Re-running `seed_data.py` at any time truncates and regenerates all data from scratch.

---

### 6. Run the app

**macOS / Linux**
```bash
python app.py
```

**Windows**
```powershell
python app.py
```

App starts at [http://localhost:5000](http://localhost:5000).

## Booking Flow Walkthrough

1. **Search** (`/`) — Select origin (e.g. New York) and destination (e.g. London), pick travel dates and group size
2. **Browse** (`/browse`) — View the 10 cheapest transportation options, hotels, and all available activities
3. **Plan** (`/plan`) — Pick one transport (radio), one hotel (radio), and any activities (checkboxes)
4. **Confirm** (`/confirm`) — Enter each passenger's name and email, payment amount and card last 4 digits
5. **Success** — A Trip ID is returned; use it or any passenger email on `/my-bookings` to retrieve the itinerary

## Analytical Queries

`queries.sql` contains 10 complex queries used for business analysis:

| # | Query |
|---|---|
| 1 | Top 5 destinations by total revenue |
| 2 | Repeat customers (3+ trips) with total spend |
| 3 | Highly-rated accommodations (3+ reviews, avg ≥ 4) |
| 4 | Full employee hierarchy (recursive CTE) |
| 5 | Most popular activity per country (window function) |
| 6 | Underfunded trips (payment < estimated cost) |
| 7 | Passengers who reviewed both transport and accommodation |
| 8 | Monthly revenue trend (rolling window sum) |
| 9 | Most-booked flight routes |
| 10 | Full trip itinerary for a given group (6-table join) |
