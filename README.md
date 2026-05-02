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

### Prerequisites

- Python 3.12+
- PostgreSQL running on `localhost:5432`

### Install

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Database

```bash
# Create the database
createdb travel_agency

# Apply schema
psql -U postgres -d travel_agency -f schema.sql

# Seed with sample data (~50 rows per table, deterministic seed)
python seed_data.py
```

The database connection is configured in both `app.py` and `seed_data.py`:

```python
DB_CONFIG = {
    "dbname": "travel_agency",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
}
```

### Run

```bash
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
