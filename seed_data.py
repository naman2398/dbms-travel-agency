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
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
}

N_LOCATIONS     = 40
N_PASSENGERS    = 60
N_EMPLOYEES     = 30
N_TRANSPORTATION = 50
N_ACCOMMODATIONS = 40
N_ACTIVITIES    = 35
N_TRIP_GROUPS   = 40
N_PAYMENTS      = 60
N_REVIEWS       = 50

fake = Faker()
Faker.seed(42)
random.seed(42)

# ------------------------------------------------------------------
# Location metadata: continent + whether city is coastal/island
# (used to decide valid transport types between two cities)
# ------------------------------------------------------------------
CITY_META = {
    "New York":       ("North America", False),
    "Los Angeles":    ("North America", True),
    "Chicago":        ("North America", False),
    "Miami":          ("North America", True),
    "Las Vegas":      ("North America", False),
    "San Francisco":  ("North America", True),
    "Seattle":        ("North America", True),
    "Boston":         ("North America", True),
    "Honolulu":       ("North America", True),   # island
    "Denver":         ("North America", False),
    "London":         ("Europe",        True),
    "Paris":          ("Europe",        False),
    "Rome":           ("Europe",        True),
    "Barcelona":      ("Europe",        True),
    "Berlin":         ("Europe",        False),
    "Amsterdam":      ("Europe",        True),
    "Vienna":         ("Europe",        False),
    "Prague":         ("Europe",        False),
    "Athens":         ("Europe",        True),
    "Lisbon":         ("Europe",        True),
    "Tokyo":          ("Asia",          True),
    "Seoul":          ("Asia",          True),
    "Bangkok":        ("Asia",          True),
    "Singapore":      ("Asia",          True),   # island
    "Hong Kong":      ("Asia",          True),
    "Mumbai":         ("Asia",          True),
    "Delhi":          ("Asia",          False),
    "Dubai":          ("Middle East",   True),
    "Istanbul":       ("Europe/Asia",   True),
    "Bali":           ("Asia",          True),   # island
    "Sydney":         ("Oceania",       True),
    "Melbourne":      ("Oceania",       True),
    "Auckland":       ("Oceania",       True),   # island
    "Toronto":        ("North America", False),
    "Vancouver":      ("North America", True),
    "Mexico City":    ("Latin America", False),
    "Cancun":         ("Latin America", True),
    "Rio de Janeiro": ("Latin America", True),
    "Buenos Aires":   ("Latin America", True),
    "Cape Town":      ("Africa",        True),
}

# Regions where overland travel (CarRental / Bus) is geographically plausible
OVERLAND_REGION_PAIRS = {
    frozenset(["North America", "North America"]),
    frozenset(["Europe", "Europe"]),
    frozenset(["Asia", "Asia"]),
    frozenset(["Latin America", "Latin America"]),
    frozenset(["Europe/Asia", "Europe"]),
    frozenset(["Europe/Asia", "Asia"]),
    frozenset(["Middle East", "Asia"]),
}

# Coastal/island city pairs where a Cruise is realistic
def cruise_ok(meta_a, meta_b):
    return meta_a[1] and meta_b[1]  # both coastal/island

def valid_transport_types(city_a, city_b):
    """Return a weighted list of transport types valid for this route."""
    meta_a = CITY_META.get(city_a, ("Unknown", False))
    meta_b = CITY_META.get(city_b, ("Unknown", False))
    reg_a, reg_b = meta_a[0], meta_b[0]

    same_region = frozenset([reg_a, reg_b]) in OVERLAND_REGION_PAIRS or reg_a == reg_b

    types = ["Flight", "Flight", "Flight"]  # always possible
    if same_region:
        types += ["CarRental", "CarRental", "Bus"]
    if cruise_ok(meta_a, meta_b):
        types += ["Cruise"]
    return types


def truncate_all(cur):
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
        ("New York",       "NY",  "USA"),
        ("Los Angeles",    "CA",  "USA"),
        ("Chicago",        "IL",  "USA"),
        ("Miami",          "FL",  "USA"),
        ("Las Vegas",      "NV",  "USA"),
        ("San Francisco",  "CA",  "USA"),
        ("Seattle",        "WA",  "USA"),
        ("Boston",         "MA",  "USA"),
        ("Honolulu",       "HI",  "USA"),
        ("Denver",         "CO",  "USA"),
        ("London",         None,  "UK"),
        ("Paris",          None,  "France"),
        ("Rome",           None,  "Italy"),
        ("Barcelona",      None,  "Spain"),
        ("Berlin",         None,  "Germany"),
        ("Amsterdam",      None,  "Netherlands"),
        ("Vienna",         None,  "Austria"),
        ("Prague",         None,  "Czech Republic"),
        ("Athens",         None,  "Greece"),
        ("Lisbon",         None,  "Portugal"),
        ("Tokyo",          None,  "Japan"),
        ("Seoul",          None,  "South Korea"),
        ("Bangkok",        None,  "Thailand"),
        ("Singapore",      None,  "Singapore"),
        ("Hong Kong",      None,  "China"),
        ("Mumbai",         "MH",  "India"),
        ("Delhi",          "DL",  "India"),
        ("Dubai",          None,  "UAE"),
        ("Istanbul",       None,  "Turkey"),
        ("Bali",           None,  "Indonesia"),
        ("Sydney",         "NSW", "Australia"),
        ("Melbourne",      "VIC", "Australia"),
        ("Auckland",       None,  "New Zealand"),
        ("Toronto",        "ON",  "Canada"),
        ("Vancouver",      "BC",  "Canada"),
        ("Mexico City",    None,  "Mexico"),
        ("Cancun",         None,  "Mexico"),
        ("Rio de Janeiro", None,  "Brazil"),
        ("Buenos Aires",   None,  "Argentina"),
        ("Cape Town",      None,  "South Africa"),
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
        rows.append((
            fake.name(),
            random.choices(genders, weights=[45, 45, 5, 5])[0],
            random.randint(18, 75),
            fake.unique.email(),
            fake.phone_number()[:30],
        ))
    cur.executemany(
        "INSERT INTO passenger (name, gender, age, email, phone) VALUES (%s, %s, %s, %s, %s);",
        rows,
    )
    print(f"  OK {N_PASSENGERS} passengers")


def seed_employees(cur):
    rows_top = []
    for _ in range(5):
        rows_top.append((
            fake.name(),
            random.choice(["Manager", "Director"]),
            fake.date_between(start_date="-10y", end_date="-2y"),
            None,
        ))
    cur.executemany(
        "INSERT INTO employee (name, role, join_date, supervisor_id) VALUES (%s, %s, %s, %s);",
        rows_top,
    )
    cur.execute("SELECT employee_id FROM employee;")
    manager_ids = [r[0] for r in cur.fetchall()]

    rows_rest = []
    for _ in range(N_EMPLOYEES - 5):
        rows_rest.append((
            fake.name(),
            random.choice(["Travel Agent", "Senior Agent", "Customer Support"]),
            fake.date_between(start_date="-5y", end_date="today"),
            random.choice(manager_ids),
        ))
    cur.executemany(
        "INSERT INTO employee (name, role, join_date, supervisor_id) VALUES (%s, %s, %s, %s);",
        rows_rest,
    )
    print(f"  OK {N_EMPLOYEES} employees")


def seed_transportation(cur):
    cur.execute("SELECT location_id, city FROM location;")
    loc_rows = cur.fetchall()
    loc_map = {r[0]: r[1] for r in loc_rows}   # id -> city name
    loc_ids = list(loc_map.keys())

    carriers = ["Delta", "United", "American Airlines", "Lufthansa",
                "Emirates", "JAL", "Qantas", "Singapore Airlines",
                "British Airways", "Air France"]
    cruise_lines = ["Royal Caribbean", "Norwegian Cruise Line",
                    "Carnival", "MSC Cruises", "Celebrity Cruises"]

    # Fare ranges by type and distance class
    fare_ranges = {
        "Flight":    {"intercontinental": (400, 2500), "regional": (80, 600)},
        "Cruise":    (800, 4000),
        "CarRental": (30, 120),   # per-day rate; total = rate * rental_days
        "Bus":       (15, 120),
    }

    rows = []
    attempts = 0
    while len(rows) < N_TRANSPORTATION and attempts < N_TRANSPORTATION * 10:
        attempts += 1
        src_id, dst_id = random.sample(loc_ids, 2)
        src_city = loc_map[src_id]
        dst_city = loc_map[dst_id]

        ttypes = valid_transport_types(src_city, dst_city)
        ttype = random.choice(ttypes)

        depart = fake.date_time_between(start_date="-90d", end_date="+180d")

        carrier = flight_no = cruise_no = car_type = rental_days = conf_id = None
        tcls = None
        fare = 0.0
        arrive = depart + timedelta(hours=2)

        src_meta = CITY_META.get(src_city, ("Unknown", False))
        dst_meta = CITY_META.get(dst_city, ("Unknown", False))
        same_region = src_meta[0] == dst_meta[0]

        if ttype == "Flight":
            is_intercontinental = not same_region
            lo, hi = fare_ranges["Flight"]["intercontinental" if is_intercontinental else "regional"]
            fare = round(random.uniform(lo, hi), 2)
            flight_hours = random.randint(10, 17) if is_intercontinental else random.randint(1, 5)
            arrive = depart + timedelta(hours=flight_hours, minutes=random.randint(0, 59))
            carrier = random.choice(carriers)
            flight_no = f"{carrier[:2].upper()}{random.randint(100, 9999)}"
            tcls = random.choices(
                ["Economy", "Business", "First"],
                weights=[70, 22, 8]
            )[0]
            # Business/First cost more
            if tcls == "Business":
                fare = round(fare * random.uniform(2.0, 3.5), 2)
            elif tcls == "First":
                fare = round(fare * random.uniform(4.0, 7.0), 2)

        elif ttype == "Cruise":
            lo, hi = fare_ranges["Cruise"]
            fare = round(random.uniform(lo, hi), 2)
            cruise_days = random.randint(5, 14)
            arrive = depart + timedelta(days=cruise_days)
            cruise_no = f"CR{random.randint(1000, 9999)}"
            carrier = random.choice(cruise_lines)
            tcls = random.choice(["Interior", "Oceanview", "Balcony", "Suite"])

        elif ttype == "CarRental":
            rental_days = random.randint(2, 14)
            daily_rate = round(random.uniform(*fare_ranges["CarRental"]), 2)
            fare = round(daily_rate * rental_days, 2)
            arrive = depart + timedelta(days=rental_days)
            car_type = random.choice(["Economy", "SUV", "Sedan", "Luxury", "Van", "Convertible"])
            conf_id = fake.uuid4()[:8].upper()

        elif ttype == "Bus":
            lo, hi = fare_ranges["Bus"]
            fare = round(random.uniform(lo, hi), 2)
            bus_hours = random.randint(2, 12)
            arrive = depart + timedelta(hours=bus_hours, minutes=random.randint(0, 30))

        rows.append((
            ttype, src_id, dst_id,
            depart, arrive, fare, tcls,
            carrier, flight_no, cruise_no,
            car_type, rental_days, conf_id,
        ))

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
    print(f"  OK {len(rows)} transportation rows")


def seed_accommodations(cur):
    cur.execute("SELECT location_id, city, country FROM location;")
    loc_rows = cur.fetchall()

    # Realistic nightly rate ranges by city tier
    luxury_cities = {"New York", "London", "Paris", "Tokyo", "Dubai",
                     "Singapore", "Hong Kong", "Sydney", "Zurich"}
    budget_cities = {"Bangkok", "Bali", "Mexico City", "Cancun",
                     "Mumbai", "Delhi", "Istanbul", "Prague", "Buenos Aires"}

    types = ["Hotel", "Resort", "Hostel", "Airbnb", "Lodge", "Motel"]
    type_weights = [40, 20, 15, 15, 5, 5]
    facility_pool = ["Pool", "Gym", "Wi-Fi", "Spa", "Restaurant",
                     "Parking", "Beach Access", "Bar", "Concierge", "Room Service"]

    # Accommodation type -> rate multiplier
    type_multiplier = {
        "Hotel": 1.0, "Resort": 1.6, "Hostel": 0.2,
        "Airbnb": 0.7, "Lodge": 0.8, "Motel": 0.4,
    }

    rows = []
    for _ in range(N_ACCOMMODATIONS):
        loc_id, city, _ = random.choice(loc_rows)
        atype = random.choices(types, weights=type_weights)[0]

        if city in luxury_cities:
            base = random.uniform(150, 700)
        elif city in budget_cities:
            base = random.uniform(25, 150)
        else:
            base = random.uniform(60, 300)

        rate = round(base * type_multiplier[atype], 2)
        discount = round(random.uniform(0, 20), 2) if random.random() < 0.3 else 0.0

        rows.append((
            loc_id,
            f"{fake.last_name()} {random.choice(['Hotel', 'Inn', 'Resort', 'Suites', 'Lodge', 'Hostel'])}",
            atype,
            max(rate, 10.0),
            ", ".join(random.sample(facility_pool, random.randint(2, 6))),
            discount,
        ))
    cur.executemany(
        """
        INSERT INTO accommodation (location_id, name, type, rate_per_night, facilities, discount_pct)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        rows,
    )
    print(f"  OK {N_ACCOMMODATIONS} accommodations")


def seed_activities(cur):
    cur.execute("SELECT location_id, city, country FROM location;")
    loc_rows = cur.fetchall()

    # Activity catalog: (name, type, base_duration_hrs, base_price_range, suitable_cities)
    # suitable_cities=None means available anywhere
    catalog = [
        ("City Walking Tour",     "Sightseeing",   2,  (15,  60),   None),
        ("Museum Pass",           "Cultural",      3,  (20,  80),   None),
        ("Cooking Class",         "Cultural",      3,  (50, 150),   None),
        ("Wine Tasting",          "Food & Drink",  2,  (40, 120),   None),
        ("Helicopter Tour",       "Adventure",     1,  (150, 500),  None),
        ("Yoga Retreat",          "Wellness",      5,  (30, 100),   None),
        ("Scuba Diving",          "Water Sport",   4,  (80, 200),   "coastal"),
        ("Snorkeling Tour",       "Water Sport",   3,  (40, 120),   "coastal"),
        ("Surfing Lesson",        "Water Sport",   2,  (50, 150),   "coastal"),
        ("Sunset Cruise",         "Water Sport",   3,  (60, 180),   "coastal"),
        ("Safari Tour",           "Wildlife",      8,  (200, 600),  {"Cape Town"}),
        ("Zipline Adventure",     "Adventure",     2,  (60, 200),   None),
        ("Hiking Trail",          "Outdoor",       6,  (20,  80),   None),
        ("Ski Resort Day Pass",   "Outdoor",       8,  (80, 250),   {"Denver", "Vancouver"}),
        ("Gondola Ride",          "Sightseeing",   1,  (30,  90),   {"Venice", "Rome"}),
        ("Temple Tour",           "Cultural",      4,  (20,  70),   {"Bangkok", "Bali", "Tokyo", "Delhi", "Istanbul"}),
        ("Night Market Tour",     "Food & Drink",  3,  (15,  50),   {"Bangkok", "Singapore", "Hong Kong", "Bali"}),
        ("Desert Safari",         "Adventure",     5,  (100, 350),  {"Dubai"}),
        ("Hot Air Balloon",       "Adventure",     2,  (150, 400),  None),
        ("Whale Watching",        "Wildlife",      4,  (80, 200),   "coastal"),
    ]

    coastal_cities = {c for c, (_, coastal) in CITY_META.items() if coastal}

    rows = []
    for _ in range(N_ACTIVITIES):
        loc_id, city, _ = random.choice(loc_rows)
        # Filter catalog to activities suitable for this city
        suitable = []
        for entry in catalog:
            name, atype, _dur, _price_range, restrict = entry
            if restrict is None:
                suitable.append(entry)
            elif restrict == "coastal" and city in coastal_cities:
                suitable.append(entry)
            elif isinstance(restrict, set) and city in restrict:
                suitable.append(entry)
        if not suitable:
            suitable = [e for e in catalog if e[4] is None]

        name, atype, base_dur, (lo, hi), _ = random.choice(suitable)
        price = round(random.uniform(lo, hi), 2)
        duration = round(base_dur + random.uniform(-0.5, 1.5), 2)
        duration = max(duration, 0.5)

        rows.append((loc_id, name, atype, price, duration))

    cur.executemany(
        "INSERT INTO activity (location_id, name, type, price, duration_hours) VALUES (%s, %s, %s, %s, %s);",
        rows,
    )
    print(f"  OK {N_ACTIVITIES} activities")


def seed_trip_groups(cur):
    cur.execute("SELECT location_id FROM location;")
    loc_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT employee_id FROM employee;")
    emp_ids = [r[0] for r in cur.fetchall()]

    purposes = ["Leisure", "Business", "Honeymoon", "Family Vacation",
                "Adventure", "Conference", "Wedding"]
    rows = []
    for _ in range(N_TRIP_GROUPS):
        src, dst = random.sample(loc_ids, 2)
        start = fake.date_between(start_date="-60d", end_date="+90d")
        # Honeymooners/leisure → longer trips; Business → shorter
        purpose = random.choice(purposes)
        if purpose in ("Honeymoon", "Family Vacation", "Leisure"):
            nights = random.randint(5, 21)
        elif purpose in ("Business", "Conference"):
            nights = random.randint(2, 7)
        else:
            nights = random.randint(3, 14)
        end = start + timedelta(days=nights)
        rows.append((
            random.randint(1, 8),
            src, dst, purpose, start, end,
            random.choice(emp_ids) if random.random() > 0.2 else None,
        ))
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
    # Fetch groups with location city names for transport-type validation
    cur.execute("""
        SELECT tg.group_id, tg.size, tg.start_date, tg.end_date,
               ls.city AS src_city, ld.city AS dst_city
        FROM   trip_group tg
        JOIN   location ls ON tg.source_location_id      = ls.location_id
        JOIN   location ld ON tg.destination_location_id = ld.location_id;
    """)
    groups = cur.fetchall()

    cur.execute("SELECT passenger_id FROM passenger;")
    pax_ids = [r[0] for r in cur.fetchall()]

    # Load transportation with city names so we can match route type
    cur.execute("""
        SELECT t.transportation_id, t.type,
               ls.city AS src_city, ld.city AS dst_city
        FROM   transportation t
        JOIN   location ls ON t.source_location_id      = ls.location_id
        JOIN   location ld ON t.destination_location_id = ld.location_id;
    """)
    trans_rows = cur.fetchall()

    # Index: (src_city, dst_city) -> list of transport_ids
    # Also keep a fallback list of all flights
    from collections import defaultdict
    trans_by_route = defaultdict(list)
    all_flights = []
    for tid, ttype, src, dst in trans_rows:
        trans_by_route[(src, dst)].append((tid, ttype))
        if ttype == "Flight":
            all_flights.append(tid)

    cur.execute("SELECT accommodation_id, location_id FROM accommodation;")
    accom_rows = cur.fetchall()
    accom_by_loc = defaultdict(list)
    for aid, lid in accom_rows:
        accom_by_loc[lid].append(aid)
    all_accom = [r[0] for r in accom_rows]

    cur.execute("SELECT activity_id, location_id FROM activity;")
    act_rows = cur.fetchall()
    act_by_loc = defaultdict(list)
    for aid, lid in act_rows:
        act_by_loc[lid].append(aid)

    # We need destination location_id for accommodation/activity lookup
    cur.execute("SELECT group_id, destination_location_id FROM trip_group;")
    group_dest = {r[0]: r[1] for r in cur.fetchall()}

    gp_rows, gt_rows, ga_rows, gact_rows = [], [], [], []

    for row in groups:
        gid, size, sd, ed, src_city, dst_city = row
        dest_loc_id = group_dest[gid]

        # ---- Passengers ----
        for pax in random.sample(pax_ids, k=min(size, len(pax_ids))):
            gp_rows.append((
                gid, pax,
                f"{random.randint(1,30)}{random.choice('ABCDEF')}",
                fake.uuid4()[:10].upper(),
                random.choice([None, None, "Vegetarian meal", "Window seat", "Wheelchair access"]),
            ))

        # ---- Transportation: pick a realistic option for this route ----
        valid_ttypes = set(valid_transport_types(src_city, dst_city))
        candidates = [
            tid for tid, ttype in trans_by_route.get((src_city, dst_city), [])
            if ttype in valid_ttypes
        ]
        # Fallback: any transport whose type is valid for this route
        if not candidates:
            candidates = [
                tid for tid, ttype, sc, dc in trans_rows
                if ttype in valid_ttypes
            ]
        # Final fallback: any flight
        if not candidates:
            candidates = all_flights

        if candidates:
            chosen_trans = random.sample(candidates, k=min(random.randint(1, 2), len(candidates)))
            for leg, tid in enumerate(chosen_trans, start=1):
                gt_rows.append((gid, tid, leg))

        # ---- Accommodation: at destination ----
        dest_accoms = accom_by_loc.get(dest_loc_id, [])
        if not dest_accoms:
            dest_accoms = random.sample(all_accom, k=min(3, len(all_accom)))
        chosen_accoms = random.sample(dest_accoms, k=min(random.randint(1, 2), len(dest_accoms)))
        for aid in chosen_accoms:
            ga_rows.append((gid, aid, sd, ed, max(1, size // 2)))

        # ---- Activities: at destination ----
        dest_acts = act_by_loc.get(dest_loc_id, [])
        if dest_acts:
            chosen_acts = random.sample(dest_acts, k=min(random.randint(0, 3), len(dest_acts)))
            used_pairs = set()
            for act_id in chosen_acts:
                sched = sd + timedelta(days=random.randint(0, max(0, (ed - sd).days)))
                key = (gid, act_id, sched)
                if key in used_pairs:
                    continue
                used_pairs.add(key)
                gact_rows.append((gid, act_id, sched, random.randint(1, size)))

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
        f"  OK junctions: {len(gp_rows)} GP, {len(gt_rows)} GT, "
        f"{len(ga_rows)} GA, {len(gact_rows)} GAct"
    )


def seed_payments(cur):
    cur.execute("""
        SELECT tg.group_id, tg.size, tg.start_date, tg.end_date,
               COALESCE(SUM(t.fare), 0)              AS trans_cost,
               COALESCE(AVG(a.rate_per_night), 0)    AS nightly_rate,
               COALESCE(SUM(act.price), 0)           AS act_cost
        FROM   trip_group tg
        LEFT JOIN group_transportation gt  ON tg.group_id = gt.group_id
        LEFT JOIN transportation        t  ON gt.transportation_id = t.transportation_id
        LEFT JOIN group_accommodation   ga ON tg.group_id = ga.group_id
        LEFT JOIN accommodation         a  ON ga.accommodation_id = a.accommodation_id
        LEFT JOIN group_activity        gact ON tg.group_id = gact.group_id
        LEFT JOIN activity              act  ON gact.activity_id = act.activity_id
        GROUP BY tg.group_id, tg.size, tg.start_date, tg.end_date;
    """)
    groups = cur.fetchall()

    types = ["Credit Card", "Debit Card", "PayPal", "Bank Transfer", "Cash"]
    rows = []
    for g in groups:
        gid, size, sd, ed, trans_cost, nightly_rate, act_cost = g
        nights = max((ed - sd).days, 1)
        estimated = float(trans_cost) * size + float(nightly_rate) * nights + float(act_cost) * size
        # Payment is 80-110% of estimated cost — realistic variance
        amount = round(max(estimated * random.uniform(0.8, 1.1), 50.0), 2)

        ptype = random.choices(types, weights=[45, 25, 15, 10, 5])[0]
        last4  = f"{random.randint(0, 9999):04d}" if "Card" in ptype else None
        expiry = f"{random.randint(1,12):02d}/{random.randint(2026,2030)}" if "Card" in ptype else None
        pay_date = fake.date_time_between(start_date=sd - timedelta(days=30), end_date=sd)

        rows.append((gid, ptype, last4, expiry, amount, pay_date))

    # Add extra payments to hit N_PAYMENTS target
    cur.execute("SELECT group_id FROM trip_group;")
    gids = [r[0] for r in cur.fetchall()]
    while len(rows) < N_PAYMENTS:
        ptype = random.choices(types, weights=[45, 25, 15, 10, 5])[0]
        last4  = f"{random.randint(0, 9999):04d}" if "Card" in ptype else None
        expiry = f"{random.randint(1,12):02d}/{random.randint(2026,2030)}" if "Card" in ptype else None
        rows.append((
            random.choice(gids), ptype, last4, expiry,
            round(random.uniform(50, 3000), 2),
            fake.date_time_between(start_date="-90d", end_date="now"),
        ))

    cur.executemany(
        """
        INSERT INTO payment (group_id, payment_type, card_last4, expiry_date,
                             amount, payment_date)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        rows,
    )
    print(f"  OK {len(rows)} payments")


def seed_reviews(cur):
    cur.execute("""
        SELECT DISTINCT gp.passenger_id, ga.accommodation_id
        FROM group_passenger gp
        JOIN group_accommodation ga ON gp.group_id = ga.group_id;
    """)
    accom_pairs = cur.fetchall()
    cur.execute("""
        SELECT DISTINCT gp.passenger_id, gt.transportation_id
        FROM group_passenger gp
        JOIN group_transportation gt ON gp.group_id = gt.group_id;
    """)
    trans_pairs = cur.fetchall()

    # Realistic review text templates
    positive = [
        "Absolutely loved it — exceeded all expectations.",
        "Fantastic experience, would highly recommend.",
        "Great value for money, very comfortable.",
        "Staff were incredibly helpful and friendly.",
        "Smooth and pleasant from start to finish.",
    ]
    mixed = [
        "Decent overall but a few minor hiccups.",
        "Good experience but slightly overpriced.",
        "Fine for the price, nothing extraordinary.",
        "Mostly good but the service was slow.",
    ]
    negative = [
        "Disappointing — did not match the description.",
        "Would not recommend, many issues throughout.",
        "Poor quality for the price paid.",
    ]

    def review_text(rating):
        if rating >= 4:
            return random.choice(positive)
        elif rating == 3:
            return random.choice(mixed)
        else:
            return random.choice(negative)

    rows = []
    for _ in range(N_REVIEWS):
        # Ratings skewed positive (realistic distribution)
        rating = random.choices([1, 2, 3, 4, 5], weights=[5, 8, 17, 35, 35])[0]
        if random.random() < 0.5 and accom_pairs:
            pax, aid = random.choice(accom_pairs)
            rows.append((pax, rating, review_text(rating),
                         fake.date_between(start_date="-90d", end_date="today"),
                         aid, None))
        elif trans_pairs:
            pax, tid = random.choice(trans_pairs)
            rows.append((pax, rating, review_text(rating),
                         fake.date_between(start_date="-90d", end_date="today"),
                         None, tid))

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
        print("\nDONE — all data inserted and committed.")
    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
