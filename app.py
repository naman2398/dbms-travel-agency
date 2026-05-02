"""
Travel Agency System - Kayak/Expedia-style booking flow.
Run: python app.py
Then open http://localhost:5000

Pages:
  /             Search form (destination + dates + group size)
  /browse       Browse flights, hotels, activities for the chosen destination
  /plan         Pick which flight + hotel + activities to book (checkboxes)
  /confirm      Enter passenger info and confirm the booking (multi-table txn)
  /my-bookings  Look up bookings by passenger email
"""
from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "dbname": "travel_agency",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
}

app = Flask(__name__)
app.secret_key = "ise503-demo-secret-key"


def get_conn():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


@app.route("/", methods=["GET", "POST"])
def search():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT location_id, city, country FROM location ORDER BY country, city;")
    locations = cur.fetchall()
    cur.close()
    conn.close()

    if request.method == "POST":
        session["search"] = {
            "source_id": int(request.form["source_id"]),
            "dest_id": int(request.form["dest_id"]),
            "start_date": request.form["start_date"],
            "end_date": request.form["end_date"],
            "size": int(request.form["size"]),
            "purpose": request.form["purpose"],
        }
        return redirect(url_for("browse"))

    return render_template("search.html", locations=locations)


@app.route("/browse")
def browse():
    s = session.get("search")
    if not s:
        return redirect(url_for("search"))

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT t.transportation_id, t.type, t.fare, t.travel_class,
               t.carrier, t.flight_number, t.departure_time, t.arrival_time,
               ls.city AS source_city, ld.city AS dest_city
        FROM   transportation t
        JOIN   location ls ON t.source_location_id      = ls.location_id
        JOIN   location ld ON t.destination_location_id = ld.location_id
        WHERE  t.destination_location_id = %s
        ORDER BY t.fare ASC
        LIMIT 10;
        """,
        (s["dest_id"],),
    )
    transports = cur.fetchall()

    cur.execute(
        """
        SELECT a.accommodation_id, a.name, a.type, a.rate_per_night,
               a.facilities, a.discount_pct
        FROM   accommodation a
        WHERE  a.location_id = %s
        ORDER BY a.rate_per_night ASC
        LIMIT 10;
        """,
        (s["dest_id"],),
    )
    hotels = cur.fetchall()

    cur.execute(
        """
        SELECT a.activity_id, a.name, a.type, a.price, a.duration_hours
        FROM   activity a
        WHERE  a.location_id = %s
        ORDER BY a.price ASC;
        """,
        (s["dest_id"],),
    )
    activities = cur.fetchall()

    cur.execute("SELECT city, country FROM location WHERE location_id = %s;", (s["dest_id"],))
    dest = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "browse.html",
        search=s,
        dest=dest,
        transports=transports,
        hotels=hotels,
        activities=activities,
    )


@app.route("/plan", methods=["POST"])
def plan():
    if "search" not in session:
        return redirect(url_for("search"))

    session["plan"] = {
        "transport_id": int(request.form.get("transport_id", 0)) or None,
        "hotel_id": int(request.form.get("hotel_id", 0)) or None,
        "activity_ids": [int(x) for x in request.form.getlist("activity_ids")],
    }

    conn = get_conn()
    cur = conn.cursor()
    summary = {"transport": None, "hotel": None, "activities": []}

    if session["plan"]["transport_id"]:
        cur.execute(
            """
            SELECT t.type, t.carrier, t.flight_number, t.fare, t.travel_class,
                   ls.city AS source_city, ld.city AS dest_city
            FROM   transportation t
            JOIN   location ls ON t.source_location_id      = ls.location_id
            JOIN   location ld ON t.destination_location_id = ld.location_id
            WHERE  t.transportation_id = %s;
            """,
            (session["plan"]["transport_id"],),
        )
        summary["transport"] = cur.fetchone()

    if session["plan"]["hotel_id"]:
        cur.execute(
            """
            SELECT name, type, rate_per_night, discount_pct
            FROM   accommodation WHERE accommodation_id = %s;
            """,
            (session["plan"]["hotel_id"],),
        )
        summary["hotel"] = cur.fetchone()

    if session["plan"]["activity_ids"]:
        cur.execute(
            """
            SELECT activity_id, name, type, price
            FROM   activity
            WHERE  activity_id = ANY(%s);
            """,
            (session["plan"]["activity_ids"],),
        )
        summary["activities"] = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("plan.html", search=session["search"], summary=summary)


@app.route("/confirm", methods=["GET", "POST"])
def confirm():
    if "search" not in session or "plan" not in session:
        return redirect(url_for("search"))

    if request.method == "POST":
        payment_amount_raw = request.form.get("payment_amount")
        card_last4 = request.form.get("card_last4")
        if not payment_amount_raw or not card_last4:
            return redirect(url_for("confirm"))
        s = session["search"]
        p = session["plan"]

        names = request.form.getlist("passenger_name")
        emails = request.form.getlist("passenger_email")
        ages = request.form.getlist("passenger_age")
        genders = request.form.getlist("passenger_gender")
        payment_amount = float(payment_amount_raw)

        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO trip_group (size, source_location_id, destination_location_id,
                                        purpose, start_date, end_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING group_id;
                """,
                (s["size"], s["source_id"], s["dest_id"], s["purpose"], s["start_date"], s["end_date"]),
            )
            group_id = cur.fetchone()["group_id"]

            for name, email, age, gender in zip(names, emails, ages, genders):
                if not name.strip():
                    continue
                cur.execute(
                    """
                    INSERT INTO passenger (name, email, age, gender)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
                    RETURNING passenger_id;
                    """,
                    (name, email, int(age) if age else None, gender or None),
                )
                pid = cur.fetchone()["passenger_id"]

                cur.execute(
                    """
                    INSERT INTO group_passenger (group_id, passenger_id, ticket_number)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (group_id, pid, f"TKT-{group_id}-{pid}"),
                )

            if p["transport_id"]:
                cur.execute(
                    """
                    INSERT INTO group_transportation (group_id, transportation_id, leg_order)
                    VALUES (%s, %s, 1);
                    """,
                    (group_id, p["transport_id"]),
                )

            if p["hotel_id"]:
                cur.execute(
                    """
                    INSERT INTO group_accommodation (group_id, accommodation_id,
                                                     check_in, check_out, num_rooms)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (group_id, p["hotel_id"], s["start_date"], s["end_date"], max(1, s["size"] // 2)),
                )

            for aid in p["activity_ids"]:
                cur.execute(
                    """
                    INSERT INTO group_activity (group_id, activity_id,
                                                scheduled_date, num_participants)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (group_id, aid, s["start_date"], s["size"]),
                )

            cur.execute(
                """
                INSERT INTO payment (group_id, payment_type, card_last4,
                                     expiry_date, amount)
                VALUES (%s, 'Credit Card', %s, '12/2028', %s);
                """,
                (group_id, card_last4, payment_amount),
            )

            conn.commit()
            flash(f"Booking confirmed. Your trip ID is #{group_id}.", "success")
            session.pop("search", None)
            session.pop("plan", None)
            return redirect(url_for("my_bookings", email=emails[0] if emails else ""))

        except Exception as e:
            conn.rollback()
            flash(f"Booking failed: {e}", "error")
        finally:
            cur.close()
            conn.close()

    return render_template("confirm.html", search=session["search"], plan=session["plan"])


@app.route("/my-bookings")
def my_bookings():
    email = request.args.get("email", "").strip()
    bookings = []

    if email:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT  tg.group_id, tg.purpose, tg.start_date, tg.end_date,
                    ls.city || ', ' || ls.country AS source,
                    ld.city || ', ' || ld.country AS destination,
                    COALESCE(SUM(p.amount), 0)    AS total_paid,
                    STRING_AGG(DISTINCT acc.name, ', ') AS hotels,
                    STRING_AGG(DISTINCT act.name, ', ') AS activities
            FROM    passenger pas
            JOIN    group_passenger      gp  ON pas.passenger_id = gp.passenger_id
            JOIN    trip_group           tg  ON gp.group_id      = tg.group_id
            JOIN    location ls ON tg.source_location_id      = ls.location_id
            JOIN    location ld ON tg.destination_location_id = ld.location_id
            LEFT JOIN payment            p   ON tg.group_id = p.group_id
            LEFT JOIN group_accommodation ga ON tg.group_id = ga.group_id
            LEFT JOIN accommodation      acc ON ga.accommodation_id = acc.accommodation_id
            LEFT JOIN group_activity     gact ON tg.group_id = gact.group_id
            LEFT JOIN activity           act  ON gact.activity_id = act.activity_id
            WHERE   pas.email = %s
            GROUP BY tg.group_id, ls.city, ls.country, ld.city, ld.country
            ORDER BY tg.start_date DESC;
            """,
            (email,),
        )
        bookings = cur.fetchall()
        cur.close()
        conn.close()

    return render_template("my_bookings.html", email=email, bookings=bookings)


if __name__ == "__main__":
    app.run(debug=True)
