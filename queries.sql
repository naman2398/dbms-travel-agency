-- =============================================================================
-- ISE 503 Project 3 - 10 Complex Queries
-- Each query labeled with the SQL concept it demonstrates.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Q1. Top 5 destinations by total revenue
-- Concepts: 4-table join, GROUP BY, ORDER BY, LIMIT, SUM
-- -----------------------------------------------------------------------------
SELECT  l.city,
        l.country,
        COUNT(DISTINCT tg.group_id) AS total_trips,
        SUM(p.amount)               AS total_revenue
FROM    trip_group tg
JOIN    location  l ON tg.destination_location_id = l.location_id
JOIN    payment   p ON tg.group_id                = p.group_id
GROUP BY l.city, l.country
ORDER BY total_revenue DESC
LIMIT 5;


-- -----------------------------------------------------------------------------
-- Q2. Passengers who have booked more than 2 trips, with their total spend
-- Concepts: aggregation, HAVING, multi-table join through junction
-- -----------------------------------------------------------------------------
SELECT  pas.passenger_id,
        pas.name,
        COUNT(DISTINCT gp.group_id) AS trip_count,
        COALESCE(SUM(p.amount), 0)  AS total_spent
FROM    passenger       pas
JOIN    group_passenger gp ON pas.passenger_id = gp.passenger_id
LEFT JOIN payment       p  ON gp.group_id      = p.group_id
GROUP BY pas.passenger_id, pas.name
HAVING  COUNT(DISTINCT gp.group_id) > 2
ORDER BY total_spent DESC;


-- -----------------------------------------------------------------------------
-- Q3. Average rating per accommodation, only those with 3+ reviews
-- Concepts: LEFT JOIN, aggregation, HAVING, ROUND
-- -----------------------------------------------------------------------------
SELECT  a.accommodation_id,
        a.name,
        a.type,
        l.city,
        ROUND(AVG(r.rating), 2) AS avg_rating,
        COUNT(r.review_id)      AS review_count
FROM    accommodation a
JOIN    location      l ON a.location_id = l.location_id
JOIN    review        r ON r.accommodation_id = a.accommodation_id
GROUP BY a.accommodation_id, a.name, a.type, l.city
HAVING  COUNT(r.review_id) >= 3
ORDER BY avg_rating DESC;


-- -----------------------------------------------------------------------------
-- Q4. Employee org chart - supervisor hierarchy
-- Concepts: RECURSIVE CTE, self-join
-- -----------------------------------------------------------------------------
WITH RECURSIVE org_chart AS (
    -- Anchor: top-level employees (no supervisor)
    SELECT  employee_id, name, role, supervisor_id, 1 AS level,
        name::text AS path
    FROM    employee
    WHERE   supervisor_id IS NULL

    UNION ALL

    -- Recursive: each employee under their supervisor
    SELECT  e.employee_id, e.name, e.role, e.supervisor_id, oc.level + 1,
            oc.path || ' > ' || e.name::text
    FROM    employee   e
    JOIN    org_chart  oc ON e.supervisor_id = oc.employee_id
)
SELECT  level, employee_id, name, role, path
FROM    org_chart
ORDER BY level, name;


-- -----------------------------------------------------------------------------
-- Q5. Most popular activity type per destination country
-- Concepts: window function (ROW_NUMBER), partitioning, subquery
-- -----------------------------------------------------------------------------
WITH activity_counts AS (
    SELECT  l.country,
            a.type           AS activity_type,
            COUNT(*)         AS bookings,
            ROW_NUMBER() OVER (PARTITION BY l.country
                               ORDER BY COUNT(*) DESC) AS rnk
    FROM    group_activity ga
    JOIN    activity a ON ga.activity_id = a.activity_id
    JOIN    location l ON a.location_id  = l.location_id
    GROUP BY l.country, a.type
)
SELECT  country, activity_type, bookings
FROM    activity_counts
WHERE   rnk = 1
ORDER BY country;


-- -----------------------------------------------------------------------------
-- Q6. Trip groups whose total payments DON'T cover their accommodation cost
-- Concepts: subqueries, set comparison, calculated columns
-- -----------------------------------------------------------------------------
SELECT  tg.group_id,
        tg.purpose,
        tg.start_date,
        accom_cost.total_cost AS accommodation_cost,
        COALESCE(pay.total_paid, 0) AS total_paid,
        accom_cost.total_cost - COALESCE(pay.total_paid, 0) AS shortfall
FROM    trip_group tg
JOIN (
    SELECT  ga.group_id,
            SUM(a.rate_per_night * (ga.check_out - ga.check_in) * ga.num_rooms
                * (1 - a.discount_pct / 100.0)) AS total_cost
    FROM    group_accommodation ga
    JOIN    accommodation a ON ga.accommodation_id = a.accommodation_id
    GROUP BY ga.group_id
) accom_cost ON tg.group_id = accom_cost.group_id
LEFT JOIN (
    SELECT group_id, SUM(amount) AS total_paid
    FROM   payment
    GROUP BY group_id
) pay ON tg.group_id = pay.group_id
WHERE accom_cost.total_cost > COALESCE(pay.total_paid, 0)
ORDER BY shortfall DESC;


-- -----------------------------------------------------------------------------
-- Q7. Passengers who reviewed both accommodation AND transportation
-- Concepts: INTERSECT (set operation)
-- -----------------------------------------------------------------------------
SELECT pas.passenger_id, pas.name, pas.email
FROM   passenger pas
WHERE  pas.passenger_id IN (
    SELECT passenger_id FROM review WHERE accommodation_id IS NOT NULL
    INTERSECT
    SELECT passenger_id FROM review WHERE transportation_id IS NOT NULL
)
ORDER BY pas.name;


-- -----------------------------------------------------------------------------
-- Q8. Monthly revenue trend with running total
-- Concepts: DATE_TRUNC, window function (SUM OVER)
-- -----------------------------------------------------------------------------
SELECT  DATE_TRUNC('month', payment_date)::date AS month,
        SUM(amount)                              AS monthly_revenue,
        SUM(SUM(amount)) OVER (
            ORDER BY DATE_TRUNC('month', payment_date)
        )                                        AS running_total
FROM    payment
GROUP BY DATE_TRUNC('month', payment_date)
ORDER BY month;


-- -----------------------------------------------------------------------------
-- Q9. Most-flown routes (Flight only) with average fare
-- Concepts: WHERE on type discriminator, self-aliased location join (twice),
--           grouping
-- -----------------------------------------------------------------------------
SELECT  ls.city || ', ' || ls.country AS source,
        ld.city || ', ' || ld.country AS destination,
        COUNT(*)                       AS num_flights,
        ROUND(AVG(t.fare), 2)          AS avg_fare
FROM    transportation t
JOIN    location ls ON t.source_location_id      = ls.location_id
JOIN    location ld ON t.destination_location_id = ld.location_id
WHERE   t.type = 'Flight'
GROUP BY ls.city, ls.country, ld.city, ld.country
ORDER BY num_flights DESC, avg_fare ASC;


-- -----------------------------------------------------------------------------
-- Q10. Full passenger itinerary for a specific trip group (use any group_id)
-- Concepts: 6-table join, string aggregation, real-world reporting query
-- -----------------------------------------------------------------------------
SELECT  tg.group_id,
        tg.purpose,
        tg.start_date,
        tg.end_date,
        STRING_AGG(DISTINCT pas.name, ', ' ORDER BY pas.name)         AS passengers,
        STRING_AGG(DISTINCT t.type || ' (' || t.fare || ')', '; ')    AS transports,
        STRING_AGG(DISTINCT acc.name, '; ')                           AS hotels,
        STRING_AGG(DISTINCT act.name, ', ')                           AS activities
FROM    trip_group tg
LEFT JOIN group_passenger      gp  ON tg.group_id = gp.group_id
LEFT JOIN passenger            pas ON gp.passenger_id = pas.passenger_id
LEFT JOIN group_transportation gt  ON tg.group_id = gt.group_id
LEFT JOIN transportation       t   ON gt.transportation_id = t.transportation_id
LEFT JOIN group_accommodation  ga  ON tg.group_id = ga.group_id
LEFT JOIN accommodation        acc ON ga.accommodation_id = acc.accommodation_id
LEFT JOIN group_activity       gact ON tg.group_id = gact.group_id
LEFT JOIN activity             act  ON gact.activity_id = act.activity_id
WHERE   tg.group_id = 1   -- change to any group_id
GROUP BY tg.group_id, tg.purpose, tg.start_date, tg.end_date;
