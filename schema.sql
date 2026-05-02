DROP TABLE IF EXISTS review              CASCADE;
DROP TABLE IF EXISTS payment             CASCADE;
DROP TABLE IF EXISTS group_activity      CASCADE;
DROP TABLE IF EXISTS group_accommodation CASCADE;
DROP TABLE IF EXISTS group_transportation CASCADE;
DROP TABLE IF EXISTS group_passenger     CASCADE;
DROP TABLE IF EXISTS trip_group          CASCADE;
DROP TABLE IF EXISTS activity            CASCADE;
DROP TABLE IF EXISTS accommodation       CASCADE;
DROP TABLE IF EXISTS transportation      CASCADE;
DROP TABLE IF EXISTS employee            CASCADE;
DROP TABLE IF EXISTS passenger           CASCADE;
DROP TABLE IF EXISTS location            CASCADE;

-- 1. LOCATION
CREATE TABLE location (
    location_id SERIAL      PRIMARY KEY,
    city        VARCHAR(80) NOT NULL,
    state       VARCHAR(80),
    country     VARCHAR(80) NOT NULL,
    CONSTRAINT uq_location_city UNIQUE (city, state, country)
);

-- 2. PASSENGER
CREATE TABLE passenger (
    passenger_id SERIAL       PRIMARY KEY,
    name         VARCHAR(120) NOT NULL,
    gender       VARCHAR(20),
    age          INT,
    email        VARCHAR(120) UNIQUE,
    phone        VARCHAR(30),
    CONSTRAINT chk_passenger_age    CHECK (age IS NULL OR (age >= 0 AND age <= 120)),
    CONSTRAINT chk_passenger_gender CHECK (gender IS NULL OR gender IN
        ('Male', 'Female', 'Other', 'Prefer not to say'))
);

-- 3. EMPLOYEE (self-referencing supervisor)
CREATE TABLE employee (
    employee_id   SERIAL       PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    role          VARCHAR(60)  NOT NULL,
    join_date     DATE         NOT NULL,
    supervisor_id INT,
    CONSTRAINT fk_employee_supervisor FOREIGN KEY (supervisor_id)
        REFERENCES employee(employee_id) ON DELETE SET NULL
);

-- 4. TRANSPORTATION (single-table inheritance)
CREATE TABLE transportation (
    transportation_id       SERIAL         PRIMARY KEY,
    type                    VARCHAR(20)    NOT NULL,
    source_location_id      INT            NOT NULL,
    destination_location_id INT            NOT NULL,
    departure_time          TIMESTAMP,
    arrival_time            TIMESTAMP,
    fare                    NUMERIC(10, 2) NOT NULL,
    travel_class            VARCHAR(20),
    carrier                 VARCHAR(80),
    flight_number           VARCHAR(20),
    cruise_number           VARCHAR(20),
    car_type                VARCHAR(40),
    rental_days             INT,
    confirmation_id         VARCHAR(40),
    CONSTRAINT fk_trans_source FOREIGN KEY (source_location_id) REFERENCES location(location_id),
    CONSTRAINT fk_trans_dest   FOREIGN KEY (destination_location_id) REFERENCES location(location_id),
    CONSTRAINT chk_trans_type  CHECK (type IN ('Flight', 'Cruise', 'CarRental', 'Bus')),
    CONSTRAINT chk_trans_fare  CHECK (fare >= 0),
    CONSTRAINT chk_trans_route CHECK (source_location_id <> destination_location_id),
    CONSTRAINT chk_trans_flight_cols CHECK (
        type <> 'Flight' OR (carrier IS NOT NULL AND flight_number IS NOT NULL)),
    CONSTRAINT chk_trans_cruise_cols CHECK (
        type <> 'Cruise' OR cruise_number IS NOT NULL),
    CONSTRAINT chk_trans_car_cols CHECK (
        type <> 'CarRental' OR (car_type IS NOT NULL AND rental_days IS NOT NULL))
);

-- 5. ACCOMMODATION
CREATE TABLE accommodation (
    accommodation_id SERIAL         PRIMARY KEY,
    location_id      INT            NOT NULL,
    name             VARCHAR(150)   NOT NULL,
    type             VARCHAR(30)    NOT NULL,
    rate_per_night   NUMERIC(10, 2) NOT NULL,
    facilities       TEXT,
    discount_pct     NUMERIC(5, 2)  DEFAULT 0,
    CONSTRAINT fk_accom_location FOREIGN KEY (location_id) REFERENCES location(location_id),
    CONSTRAINT chk_accom_type     CHECK (type IN ('Hotel', 'Resort', 'Hostel', 'Airbnb', 'Lodge', 'Motel')),
    CONSTRAINT chk_accom_rate     CHECK (rate_per_night >= 0),
    CONSTRAINT chk_accom_discount CHECK (discount_pct >= 0 AND discount_pct <= 100)
);

-- 6. ACTIVITY
CREATE TABLE activity (
    activity_id    SERIAL         PRIMARY KEY,
    location_id    INT            NOT NULL,
    name           VARCHAR(120)   NOT NULL,
    type           VARCHAR(50)    NOT NULL,
    price          NUMERIC(10, 2) NOT NULL,
    duration_hours NUMERIC(5, 2)  NOT NULL,
    CONSTRAINT fk_activity_location FOREIGN KEY (location_id) REFERENCES location(location_id),
    CONSTRAINT chk_activity_price    CHECK (price >= 0),
    CONSTRAINT chk_activity_duration CHECK (duration_hours > 0)
);

-- 7. TRIP_GROUP (central booking unit; "group" is reserved in SQL)
CREATE TABLE trip_group (
    group_id                SERIAL PRIMARY KEY,
    size                    INT    NOT NULL,
    source_location_id      INT    NOT NULL,
    destination_location_id INT    NOT NULL,
    purpose                 VARCHAR(60),
    start_date              DATE   NOT NULL,
    end_date                DATE   NOT NULL,
    booked_by_employee_id   INT,
    CONSTRAINT fk_group_source   FOREIGN KEY (source_location_id) REFERENCES location(location_id),
    CONSTRAINT fk_group_dest     FOREIGN KEY (destination_location_id) REFERENCES location(location_id),
    CONSTRAINT fk_group_employee FOREIGN KEY (booked_by_employee_id) REFERENCES employee(employee_id) ON DELETE SET NULL,
    CONSTRAINT chk_group_size  CHECK (size > 0),
    CONSTRAINT chk_group_dates CHECK (end_date >= start_date),
    CONSTRAINT chk_group_route CHECK (source_location_id <> destination_location_id)
);

-- 8. GROUP_PASSENGER (junction with per-passenger detail)
CREATE TABLE group_passenger (
    group_id         INT NOT NULL,
    passenger_id     INT NOT NULL,
    seat_number      VARCHAR(10),
    ticket_number    VARCHAR(40),
    special_requests TEXT,
    PRIMARY KEY (group_id, passenger_id),
    CONSTRAINT fk_gp_group     FOREIGN KEY (group_id)     REFERENCES trip_group(group_id) ON DELETE CASCADE,
    CONSTRAINT fk_gp_passenger FOREIGN KEY (passenger_id) REFERENCES passenger(passenger_id) ON DELETE CASCADE
);

-- 9. GROUP_TRANSPORTATION
CREATE TABLE group_transportation (
    group_id          INT NOT NULL,
    transportation_id INT NOT NULL,
    leg_order         INT NOT NULL,
    PRIMARY KEY (group_id, transportation_id),
    CONSTRAINT fk_gt_group FOREIGN KEY (group_id)          REFERENCES trip_group(group_id) ON DELETE CASCADE,
    CONSTRAINT fk_gt_trans FOREIGN KEY (transportation_id) REFERENCES transportation(transportation_id),
    CONSTRAINT chk_gt_order CHECK (leg_order > 0)
);

-- 10. GROUP_ACCOMMODATION
CREATE TABLE group_accommodation (
    group_id         INT  NOT NULL,
    accommodation_id INT  NOT NULL,
    check_in         DATE NOT NULL,
    check_out        DATE NOT NULL,
    num_rooms        INT  NOT NULL DEFAULT 1,
    PRIMARY KEY (group_id, accommodation_id),
    CONSTRAINT fk_ga_group FOREIGN KEY (group_id)         REFERENCES trip_group(group_id) ON DELETE CASCADE,
    CONSTRAINT fk_ga_accom FOREIGN KEY (accommodation_id) REFERENCES accommodation(accommodation_id),
    CONSTRAINT chk_ga_dates CHECK (check_out > check_in),
    CONSTRAINT chk_ga_rooms CHECK (num_rooms > 0)
);

-- 11. GROUP_ACTIVITY
CREATE TABLE group_activity (
    group_id         INT  NOT NULL,
    activity_id      INT  NOT NULL,
    scheduled_date   DATE NOT NULL,
    num_participants INT  NOT NULL,
    PRIMARY KEY (group_id, activity_id, scheduled_date),
    CONSTRAINT fk_gact_group    FOREIGN KEY (group_id)    REFERENCES trip_group(group_id) ON DELETE CASCADE,
    CONSTRAINT fk_gact_activity FOREIGN KEY (activity_id) REFERENCES activity(activity_id),
    CONSTRAINT chk_gact_participants CHECK (num_participants > 0)
);

-- 12. PAYMENT (only last 4 of card stored; PCI-DSS compliant)
CREATE TABLE payment (
    payment_id   SERIAL         PRIMARY KEY,
    group_id     INT            NOT NULL,
    payment_type VARCHAR(30)    NOT NULL,
    card_last4   CHAR(4),
    expiry_date  VARCHAR(7),
    amount       NUMERIC(10, 2) NOT NULL,
    payment_date TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pay_group FOREIGN KEY (group_id) REFERENCES trip_group(group_id) ON DELETE CASCADE,
    CONSTRAINT chk_pay_type CHECK (payment_type IN
        ('Credit Card', 'Debit Card', 'PayPal', 'Bank Transfer', 'Cash')),
    CONSTRAINT chk_pay_amount     CHECK (amount > 0),
    CONSTRAINT chk_pay_card_last4 CHECK (card_last4 IS NULL OR card_last4 ~ '^[0-9]{4}$')
);

-- 13. REVIEW (polymorphic: exactly one of accommodation_id / transportation_id)
CREATE TABLE review (
    review_id         SERIAL PRIMARY KEY,
    passenger_id      INT    NOT NULL,
    rating            INT    NOT NULL,
    review_text       TEXT,
    review_date       DATE   NOT NULL DEFAULT CURRENT_DATE,
    accommodation_id  INT,
    transportation_id INT,
    CONSTRAINT fk_rev_passenger FOREIGN KEY (passenger_id)      REFERENCES passenger(passenger_id) ON DELETE CASCADE,
    CONSTRAINT fk_rev_accom     FOREIGN KEY (accommodation_id)  REFERENCES accommodation(accommodation_id) ON DELETE CASCADE,
    CONSTRAINT fk_rev_trans     FOREIGN KEY (transportation_id) REFERENCES transportation(transportation_id) ON DELETE CASCADE,
    CONSTRAINT chk_rev_rating CHECK (rating BETWEEN 1 AND 5),
    CONSTRAINT chk_rev_target_xor CHECK (
        (accommodation_id IS NOT NULL AND transportation_id IS NULL) OR
        (accommodation_id IS NULL     AND transportation_id IS NOT NULL))
);

-- Indexes on frequently-joined columns
CREATE INDEX idx_trans_source      ON transportation(source_location_id);
CREATE INDEX idx_trans_dest        ON transportation(destination_location_id);
CREATE INDEX idx_accom_location    ON accommodation(location_id);
CREATE INDEX idx_activity_location ON activity(location_id);
CREATE INDEX idx_group_dest        ON trip_group(destination_location_id);
CREATE INDEX idx_group_employee    ON trip_group(booked_by_employee_id);
CREATE INDEX idx_payment_group     ON payment(group_id);
CREATE INDEX idx_review_accom      ON review(accommodation_id);
CREATE INDEX idx_review_trans      ON review(transportation_id);
CREATE INDEX idx_review_passenger  ON review(passenger_id);
