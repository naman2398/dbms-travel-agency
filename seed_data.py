"""
Travel Agency System - Faker-based data generator.
Inserts data in dependency order:
  location -> passenger -> employee -> transportation
  -> accommodation -> activity -> trip_group
  -> group_passenger / group_transportation / group_accommodation / group_activity
  -> payment -> review
"""

import random
from datetime import date, timedelta, datetime
from decimal import Decimal

import psycopg2
from faker import Faker

# ----- CONFIG -----
DB_CONFIG = {
    "dbname": "travel_agency",
    "user": "postgres",
    "password": "postgres",  # <-- CHANGE THIS
    "host": "localhost",
    "port": 5432,
}

# Row counts (all >= 30 to satisfy rubric)
N_LOCATIONS = 40
N_PASSENGERS = 60
N_EMPLOYEES = 30
N_TRANSPORTATION = 50
N_ACCOMMODATIONS = 40
N_ACTIVITIES = 35
N_TRIP_GROUPS = 40
N_PAYMENTS = 60
N_REVIEWS = 50

fake = Faker()
Faker.seed(42)
random.seed(42)


def truncate_all(cur):
    """Wipe all tables; RESTART IDENTITY resets SERIAL counters."""
    cur.execute(
        """
        TRUNCATE TABLE
            review, payment,
            group_activity, group_accommodation, group_transportation, group_passenger,
            trip_group, activity, accommodation, transportation,
            employee, passenger, location
        RESTART IDENTITY CASCADE;
        """
    )


def seed_locations(cur):
    cities = [
        ("New York", "NY", "USA"), ("Los Angeles", "CA", "USA"),
        ("Chicago", "IL", "USA"), ("Miami", "FL", "USA"),
        ("Las Vegas", "NV", "USA"), ("San Francisco", "CA", "USA"),
        ("Seattle", "WA", "USA"), ("Boston", "MA", "USA"),
        ("Honolulu", "HI", "USA"), ("Denver", "CO", "USA"),
        ("London", None, "UK"), ("Paris", None, "France"),
        ("Rome", None, "Italy"), ("Barcelona", None, "Spain"),
        ("Berlin", None, "Germany"), ("Amsterdam", None, "Netherlands"),
        ("Vienna", None, "Austria"), ("Prague", None, "Czech Republic"),
        ("Athens", None, "Greece"), ("Lisbon", None, "Portugal"),
        ("Tokyo", None, "Japan"), ("Seoul", None, "South Korea"),
        ("Bangkok", None, "Thailand"), ("Singapore", None, "Singapore"),
        ("Hong Kong", None, "China"), ("Mumbai", "MH", "India"),
        ("Delhi", "DL", "India"), ("Dubai", None, "UAE"),
        ("Istanbul", None, "Turkey"), ("Bali", None, "Indonesia"),
        ("Sydney", "NSW", "Australia"), ("Melbourne", "VIC", "Australia"),
        ("Auckland", None, "New Zealand"), ("Toronto", "ON", "Canada"),
        ("Vancouver", "BC", "Canada"), ("Mexico City", None, "Mexico"),
        ("Cancun", None, "Mexico"), ("Rio de Janeiro", None, "Brazil"),
        ("Buenos Aires", None, "Argentina"), ("Cape Town", None, "South Africa"),
    ]
    cur.executemany(
        "INSERT INTO location (city, state, country) VALUES (%s, %s, %s);",
        cities[:N_LOCATIONS],
    )
    print(f"  OK {N_LOCATIONS} locations")


def seed_passengers(cur):
    genders = ["Male", "Female", "Other", "Prefer not to say"]
    rows = []
    for _ in range(N_PASSENGERS):
        rows.append(
            (
                fake.name(),
                random.choices(genders, weights=[45, 45, 5, 5])[0],
                random.randint(18, 75),
                fake.unique.email(),
                fake.phone_number()[:30],
            )
        )
    cur.executemany(
        "INSERT INTO passenger (name, gender, age, email, phone) VALUES (%s, %s, %s, %s, %s);",
        rows,
    )
    print(f"  OK {N_PASSENGERS} passengers")


def seed_employees(cur):
    roles = ["Travel Agent", "Senior Agent", "Manager", "Director", "Customer Support"]
    # Insert managers first (no supervisor), then agents (with supervisor).
    # Top 5 are managers/directors; rest report to one of them.
    rows_top = []
    for _ in range(5):
        rows_top.append(
            (
                fake.name(),
                random.choice(["Manager", "Director"]),
                fake.date_between(start_date="-10y", end_date="-2y"),
                None,
            )
        )
    cur.executemany(
        "INSERT INTO employee (name, role, join_date, supervisor_id) VALUES (%s, %s, %s, %s);",
        rows_top,
    )
    cur.execute("SELECT employee_id FROM employee;")
    manager_ids = [r[0] for r in cur.fetchall()]

    rows_rest = []
    for _ in range(N_EMPLOYEES - 5):
        rows_rest.append(
            (
                fake.name(),
                random.choice(["Travel Agent", "Senior Agent", "Customer Support"]),
                fake.date_between(start_date="-5y", end_date="today"),
                random.choice(manager_ids),
            )
        )
    cur.executemany(
        "INSERT INTO employee (name, role, join_date, supervisor_id) VALUES (%s, %s, %s, %s);",
        rows_rest,
    )
    print(f"  OK {N_EMPLOYEES} employees")


def seed_transportation(cur):
    cur.execute("SELECT location_id FROM location;")
    loc_ids = [r[0] for r in cur.fetchall()]

    rows = []
    classes = ["Economy", "Business", "First"]
    carriers = ["Delta", "United", "American", "Lufthansa", "Emirates", "JAL", "Qantas"]

    for _ in range(N_TRANSPORTATION):
        ttype = random.choice(["Flight", "Flight", "Flight", "CarRental", "Cruise", "Bus"])
        src, dst = random.sample(loc_ids, 2)
        depart = fake.date_time_between(start_date="-90d", end_date="+180d")
        arrive = depart + timedelta(hours=random.randint(2, 18))
        fare = round(random.uniform(50, 2000), 2)

        carrier = flight_no = cruise_no = car_type = rental_days = conf_id = None
        tcls = None

        if ttype == "Flight":
            carrier = random.choice(carriers)
            flight_no = f"{carrier[:2].upper()}{random.randint(100, 9999)}"
            tcls = random.choice(classes)
        elif ttype == "Cruise":
            cruise_no = f"CR{random.randint(1000, 9999)}"
            tcls = random.choice(classes)
        elif ttype == "CarRental":
            car_type = random.choice(["Economy", "SUV", "Sedan", "Luxury", "Van"])
            rental_days = random.randint(1, 14)
            conf_id = fake.uuid4()[:8].upper()

        rows.append(
            (
                ttype,
                src,
                dst,
                depart,
                arrive,
                fare,
                tcls,
                carrier,
                flight_no,
                cruise_no,
                car_type,
                rental_days,
                conf_id,
            )
        )

    cur.executemany(
        """
        INSERT INTO transportation (
            type, source_location_id, destination_location_id,
            departure_time, arrival_time, fare, travel_class,
            carrier, flight_number, cruise_number,
            car_type, rental_days, confirmation_id
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
        """,
        rows,
    )
    print(f"  OK {N_TRANSPORTATION} transportation rows")


def seed_accommodations(cur):
    cur.execute("SELECT location_id FROM location;")
    loc_ids = [r[0] for r in cur.fetchall()]

    types = ["Hotel", "Resort", "Hostel", "Airbnb", "Lodge", "Motel"]
    facility_pool = [
        "Pool",
        "Gym",
        "Wi-Fi",
        "Spa",
        "Restaurant",
        "Parking",
        "Beach Access",
        "Bar",
        "Concierge",
    ]

    rows = []
    for _ in range(N_ACCOMMODATIONS):
        rows.append(
            (
                random.choice(loc_ids),
                f"{fake.last_name()} {random.choice(['Hotel', 'Inn', 'Resort', 'Suites', 'Lodge'])}",
                random.choice(types),
                round(random.uniform(40, 800), 2),
                ", ".join(random.sample(facility_pool, random.randint(2, 5))),
                round(random.uniform(0, 25), 2),
            )
        )
    cur.executemany(
        """
        INSERT INTO accommodation (location_id, name, type, rate_per_night, facilities, discount_pct)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        rows,
    )
    print(f"  OK {N_ACCOMMODATIONS} accommodations")


def seed_activities(cur):
    cur.execute("SELECT location_id FROM location;")
    loc_ids = [r[0] for r in cur.fetchall()]

    catalog = [
        ("Scuba Diving", "Water Sport", 4),
        ("Snorkeling Tour", "Water Sport", 3),
        ("Hiking Trail", "Outdoor", 6),
        ("City Walking Tour", "Sightseeing", 2),
        ("Museum Pass", "Cultural", 3),
        ("Cooking Class", "Cultural", 3),
        ("Wine Tasting", "Food & Drink", 2),
        ("Helicopter Tour", "Adventure", 1),
        ("Zipline", "Adventure", 2),
        ("Yoga Retreat", "Wellness", 5),
        ("Surfing Lesson", "Water Sport", 2),
        ("Safari Tour", "Wildlife", 8),
    ]
    rows = []
    for _ in range(N_ACTIVITIES):
        name, atype, dur = random.choice(catalog)
        rows.append(
            (
                random.choice(loc_ids),
                name,
                atype,
                round(random.uniform(20, 500), 2),
                dur + round(random.uniform(-0.5, 1.5), 2),
            )
        )
    cur.executemany(
        """
        INSERT INTO activity (location_id, name, type, price, duration_hours)
        VALUES (%s, %s, %s, %s, %s);
        """,
        rows,
    )
    print(f"  OK {N_ACTIVITIES} activities")


def seed_trip_groups(cur):
    cur.execute("SELECT location_id FROM location;")
    loc_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT employee_id FROM employee;")
    emp_ids = [r[0] for r in cur.fetchall()]

    purposes = [
        "Leisure",
        "Business",
        "Honeymoon",
        "Family Vacation",
        "Adventure",
        "Conference",
        "Wedding",
    ]
    rows = []
    for _ in range(N_TRIP_GROUPS):
        src, dst = random.sample(loc_ids, 2)
        start = fake.date_between(start_date="-60d", end_date="+90d")
        end = start + timedelta(days=random.randint(2, 21))
        rows.append(
            (
                random.randint(1, 8),
                src,
                dst,
                random.choice(purposes),
                start,
                end,
                random.choice(emp_ids) if random.random() > 0.2 else None,
            )
        )
    cur.executemany(
        """
        INSERT INTO trip_group (size, source_location_id, destination_location_id,
                                purpose, start_date, end_date, booked_by_employee_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """,
        rows,
    )
    print(f"  OK {N_TRIP_GROUPS} trip groups")


def seed_junctions(cur):
    cur.execute("SELECT group_id, size, start_date, end_date FROM trip_group;")
    groups = cur.fetchall()
    cur.execute("SELECT passenger_id FROM passenger;")
    pax_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT transportation_id FROM transportation;")
    trans_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT accommodation_id FROM accommodation;")
    accom_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT activity_id FROM activity;")
    act_ids = [r[0] for r in cur.fetchall()]

    gp_rows, gt_rows, ga_rows, gact_rows = [], [], [], []

    for gid, size, sd, ed in groups:
        # group_passenger: pick `size` distinct passengers
        for pax in random.sample(pax_ids, k=min(size, len(pax_ids))):
            gp_rows.append(
                (
                    gid,
                    pax,
                    f"{random.randint(1, 30)}{random.choice('ABCDEF')}",
                    fake.uuid4()[:10].upper(),
                    random.choice([None, None, "Vegetarian meal", "Window seat", "Wheelchair access"]),
                )
            )

        # group_transportation: 1-3 legs
        for leg, tid in enumerate(random.sample(trans_ids, k=random.randint(1, 3)), start=1):
            gt_rows.append((gid, tid, leg))

        # group_accommodation: 1-2 stays
        for aid in random.sample(accom_ids, k=random.randint(1, 2)):
            ga_rows.append((gid, aid, sd, ed, random.randint(1, 3)))

        # group_activity: 0-3 activities
        chosen_acts = random.sample(act_ids, k=random.randint(0, 3))
        used_pairs = set()
        for aid in chosen_acts:
            sched = sd + timedelta(days=random.randint(0, max(0, (ed - sd).days)))
            key = (gid, aid, sched)
            if key in used_pairs:
                continue
            used_pairs.add(key)
            gact_rows.append((gid, aid, sched, random.randint(1, size)))

    cur.executemany(
        """
        INSERT INTO group_passenger (group_id, passenger_id, seat_number,
                                     ticket_number, special_requests)
        VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;
        """,
        gp_rows,
    )
    cur.executemany(
        """
        INSERT INTO group_transportation (group_id, transportation_id, leg_order)
        VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;
        """,
        gt_rows,
    )
    cur.executemany(
        """
        INSERT INTO group_accommodation (group_id, accommodation_id, check_in,
                                         check_out, num_rooms)
        VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;
        """,
        ga_rows,
    )
    cur.executemany(
        """
        INSERT INTO group_activity (group_id, activity_id, scheduled_date, num_participants)
        VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;
        """,
        gact_rows,
    )
    print(
        f"  OK junctions: {len(gp_rows)} GP, {len(gt_rows)} GT, {len(ga_rows)} GA, "
        f"{len(gact_rows)} GAct"
    )


def seed_payments(cur):
    cur.execute("SELECT group_id FROM trip_group;")
    gids = [r[0] for r in cur.fetchall()]

    types = ["Credit Card", "Debit Card", "PayPal", "Bank Transfer", "Cash"]
    rows = []
    for _ in range(N_PAYMENTS):
        ptype = random.choice(types)
        last4 = f"{random.randint(0, 9999):04d}" if "Card" in ptype else None
        expiry = f"{random.randint(1,12):02d}/{random.randint(2026, 2030)}" if "Card" in ptype else None
        rows.append(
            (
                random.choice(gids),
                ptype,
                last4,
                expiry,
                round(random.uniform(100, 5000), 2),
                fake.date_time_between(start_date="-90d", end_date="now"),
            )
        )
    cur.executemany(
        """
        INSERT INTO payment (group_id, payment_type, card_last4, expiry_date,
                             amount, payment_date)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        rows,
    )
    print(f"  OK {N_PAYMENTS} payments")


def seed_reviews(cur):
    # Only review accom/transport that's actually been booked by some group
    cur.execute(
        """
        SELECT DISTINCT gp.passenger_id, ga.accommodation_id
        FROM group_passenger gp
        JOIN group_accommodation ga ON gp.group_id = ga.group_id;
        """
    )
    accom_pairs = cur.fetchall()
    cur.execute(
        """
        SELECT DISTINCT gp.passenger_id, gt.transportation_id
        FROM group_passenger gp
        JOIN group_transportation gt ON gp.group_id = gt.group_id;
        """
    )
    trans_pairs = cur.fetchall()

    rows = []
    for _ in range(N_REVIEWS):
        if random.random() < 0.5 and accom_pairs:
            pax, aid = random.choice(accom_pairs)
            rows.append(
                (
                    pax,
                    random.randint(1, 5),
                    fake.sentence(nb_words=12),
                    fake.date_between(start_date="-90d", end_date="today"),
                    aid,
                    None,
                )
            )
        elif trans_pairs:
            pax, tid = random.choice(trans_pairs)
            rows.append(
                (
                    pax,
                    random.randint(1, 5),
                    fake.sentence(nb_words=12),
                    fake.date_between(start_date="-90d", end_date="today"),
                    None,
                    tid,
                )
            )

    cur.executemany(
        """
        INSERT INTO review (passenger_id, rating, review_text, review_date,
                            accommodation_id, transportation_id)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        rows,
    )
    print(f"  OK {len(rows)} reviews")


def main():
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Truncating existing data...")
        truncate_all(cur)

        print("Seeding data...")
        seed_locations(cur)
        seed_passengers(cur)
        seed_employees(cur)
        seed_transportation(cur)
        seed_accommodations(cur)
        seed_activities(cur)
        seed_trip_groups(cur)
        seed_junctions(cur)
        seed_payments(cur)
        seed_reviews(cur)

        conn.commit()
        print("\nDONE All data inserted and committed.")
    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
