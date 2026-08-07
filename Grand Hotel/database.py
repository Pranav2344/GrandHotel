from datetime import datetime, date
from decimal import Decimal
import os
import sqlite3
from urllib.parse import urlparse

try:
    import pymysql
except ImportError:
    pymysql = None

# Environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')
SQLITE_DB_PATH = os.environ.get('SQLITE_DB_PATH', '/tmp/grand_hotel.db')

# Tax rate applied to (room_charges + service_charges) when calculating a bill.
# Override by setting the TAX_RATE env var, e.g. TAX_RATE=0.12 for 12%.
TAX_RATE = float(os.environ.get('TAX_RATE', '0.18'))

DEFAULT_ROOMS = [
    ('101', 'Standard Single', 1500.00, 1, 'Cozy single room with basic amenities'),
    ('102', 'Standard Double', 2500.00, 2, 'Comfortable double room with city view'),
    ('103', 'Standard Double', 2500.00, 2, 'Comfortable double room with garden view'),
    ('201', 'Deluxe Suite', 4500.00, 3, 'Spacious suite with living area and premium amenities'),
    ('202', 'Deluxe Suite', 4500.00, 3, 'Luxurious suite with balcony'),
    ('301', 'Executive Suite', 7000.00, 4, 'Premium suite with jacuzzi and panoramic view'),
    ('302', 'Presidential Suite', 12000.00, 6, 'Ultimate luxury with private terrace and dining area'),
    ('303', 'Executive Family Suite', 8000.00, 5, 'Large family suite with lounge and two queen beds'),
    ('401', 'Premium Double', 3200.00, 2, 'Elegant double room with work desk and minibar'),
    ('402', 'Economy Single', 1300.00, 1, 'Budget-friendly single room with essential amenities')
]

DEFAULT_SERVICES = [
    ('Room Service - Breakfast', 500.00, 'Continental breakfast delivered to room'),
    ('Room Service - Lunch', 800.00, 'Lunch meal service'),
    ('Room Service - Dinner', 1000.00, 'Dinner meal service'),
    ('Laundry Service', 300.00, 'Per piece laundry service'),
    ('Spa & Massage', 2000.00, 'One hour spa and massage session'),
    ('Airport Pickup', 1500.00, 'Airport to hotel transfer'),
    ('Mini Bar', 500.00, 'Mini bar consumption'),
    ('Extra Bed', 800.00, 'Additional bed in room'),
    ('Wi-Fi Premium', 200.00, 'High-speed internet access per day'),
    ('Conference Room', 5000.00, 'Conference room rental per hour')
]


def _as_date(value):
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.strptime(value, '%Y-%m-%d').date()
    raise TypeError(f'Unsupported date value: {type(value)!r}')


def _to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


# Write Aiven CA certificate to /tmp at startup (Vercel's filesystem is read-only
# except /tmp, so the cert content is stored in an env var and written out here).
def _write_ssl_ca_if_needed():
    """Write Aiven CA cert from env var content to /tmp so pymysql can read it."""
    ca_content = os.getenv("DB_SSL_CA_CONTENT")
    if ca_content and not os.getenv("DB_SSL_CA_PATH"):
        ca_path = '/tmp/aiven-ca.pem'
        with open(ca_path, 'w') as f:
            f.write(ca_content)
        os.environ["DB_SSL_CA_PATH"] = ca_path


_write_ssl_ca_if_needed()


def _mysql_connection_config():
    """Parse DATABASE_URL or fallback to individual DB_* environment variables."""
    if not DATABASE_URL:
        return {
            'host': os.getenv("DB_HOST", "localhost"),
            'port': int(os.getenv("DB_PORT", 3306)),
            'user': os.getenv("DB_USER", "root"),
            'password': os.getenv("DB_PASSWORD", ""),
            'database': os.getenv("DB_NAME", ""),
            'ssl_ca': os.getenv("DB_SSL_CA_PATH"),
        }

    if DATABASE_URL.startswith('sqlite://'):
        return None

    if not (DATABASE_URL.startswith('mysql://') or DATABASE_URL.startswith('mysql+pymysql://')):
        return None

    parsed = urlparse(DATABASE_URL.replace('mysql+pymysql://', 'mysql://', 1))
    return {
        'host': parsed.hostname or os.getenv("DB_HOST", "localhost"),
        'port': parsed.port or int(os.getenv("DB_PORT", 3306)),
        'user': parsed.username or os.getenv("DB_USER", "root"),
        'password': parsed.password or os.getenv("DB_PASSWORD", ""),
        'database': (parsed.path or '/').lstrip('/') or os.getenv("DB_NAME", ""),
        'ssl_ca': os.getenv("DB_SSL_CA_PATH"),
    }


def _uses_sqlite_backend():
    return not DATABASE_URL or DATABASE_URL.startswith('sqlite://')


# ---------------------------------------------------------------------------
# Schema — matches mysql_schema.sql exactly (table/column names preserved)
# ---------------------------------------------------------------------------

MYSQL_TABLES = '''
CREATE TABLE IF NOT EXISTS rooms (
    room_id INT PRIMARY KEY AUTO_INCREMENT,
    room_number VARCHAR(10) UNIQUE NOT NULL,
    room_type VARCHAR(50) NOT NULL,
    price_per_night DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'Available',
    capacity INT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20) NOT NULL,
    id_proof_type VARCHAR(50) NOT NULL,
    id_proof_number VARCHAR(50) NOT NULL,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    room_id INT NOT NULL,
    check_in_date DATE NOT NULL,
    check_out_date DATE,
    number_of_guests INT NOT NULL,
    booking_status VARCHAR(20) DEFAULT 'Active',
    special_requests TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bookings_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_bookings_room
        FOREIGN KEY (room_id) REFERENCES rooms(room_id)
);

CREATE TABLE IF NOT EXISTS services (
    service_id INT PRIMARY KEY AUTO_INCREMENT,
    service_name VARCHAR(100) NOT NULL,
    service_price DECIMAL(10, 2) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS booking_services (
    id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    service_id INT NOT NULL,
    quantity INT DEFAULT 1,
    service_date DATE DEFAULT (CURRENT_DATE),
    CONSTRAINT fk_booking_services_booking
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    CONSTRAINT fk_booking_services_service
        FOREIGN KEY (service_id) REFERENCES services(service_id)
);

CREATE TABLE IF NOT EXISTS bills (
    bill_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    room_charges DECIMAL(10, 2) NOT NULL,
    service_charges DECIMAL(10, 2) DEFAULT 0,
    tax_amount DECIMAL(10, 2) NOT NULL,
    discount DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'Pending',
    payment_method VARCHAR(50),
    bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bills_booking
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);
'''

MYSQL_INDEXES = [
    'CREATE INDEX idx_rooms_status ON rooms(status)',
    'CREATE INDEX idx_bookings_customer_id ON bookings(customer_id)',
    'CREATE INDEX idx_bookings_room_id ON bookings(room_id)',
    'CREATE INDEX idx_bookings_status ON bookings(booking_status)',
    'CREATE INDEX idx_bookings_check_in ON bookings(check_in_date)',
    'CREATE INDEX idx_bookings_check_out ON bookings(check_out_date)',
    'CREATE INDEX idx_booking_services_booking_id ON booking_services(booking_id)',
    'CREATE INDEX idx_booking_services_service_id ON booking_services(service_id)',
    'CREATE INDEX idx_bills_booking_id ON bills(booking_id)',
    'CREATE INDEX idx_bills_status ON bills(payment_status)',
    'CREATE INDEX idx_bills_date ON bills(bill_date)',
    'CREATE INDEX idx_customers_phone ON customers(phone)',
]

SQLITE_TABLES = '''
CREATE TABLE IF NOT EXISTS rooms (
    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number TEXT UNIQUE NOT NULL,
    room_type TEXT NOT NULL,
    price_per_night REAL NOT NULL,
    status TEXT DEFAULT 'Available',
    capacity INTEGER NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT NOT NULL,
    id_proof_type TEXT NOT NULL,
    id_proof_number TEXT NOT NULL,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    check_in_date DATE NOT NULL,
    check_out_date DATE,
    number_of_guests INTEGER NOT NULL,
    booking_status TEXT DEFAULT 'Active',
    special_requests TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id)
);

CREATE TABLE IF NOT EXISTS services (
    service_id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    service_price REAL NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS booking_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    service_date DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    FOREIGN KEY (service_id) REFERENCES services(service_id)
);

CREATE TABLE IF NOT EXISTS bills (
    bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    room_charges REAL NOT NULL,
    service_charges REAL DEFAULT 0,
    tax_amount REAL NOT NULL,
    discount REAL DEFAULT 0,
    total_amount REAL NOT NULL,
    payment_status TEXT DEFAULT 'Pending',
    payment_method TEXT,
    bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);

CREATE INDEX IF NOT EXISTS idx_rooms_status ON rooms(status);
CREATE INDEX IF NOT EXISTS idx_bookings_customer_id ON bookings(customer_id);
CREATE INDEX IF NOT EXISTS idx_bookings_room_id ON bookings(room_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(booking_status);
CREATE INDEX IF NOT EXISTS idx_bookings_check_in ON bookings(check_in_date);
CREATE INDEX IF NOT EXISTS idx_bookings_check_out ON bookings(check_out_date);
CREATE INDEX IF NOT EXISTS idx_booking_services_booking_id ON booking_services(booking_id);
CREATE INDEX IF NOT EXISTS idx_booking_services_service_id ON booking_services(service_id);
CREATE INDEX IF NOT EXISTS idx_bills_booking_id ON bills(booking_id);
CREATE INDEX IF NOT EXISTS idx_bills_status ON bills(payment_status);
CREATE INDEX IF NOT EXISTS idx_bills_date ON bills(bill_date);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
'''


def _adapt_query(query, conn=None):
    if conn is not None and isinstance(conn, sqlite3.Connection):
        return query
    return query.replace('?', '%s')


def _execute(conn, query, params=()):
    cursor = conn.cursor()
    cursor.execute(_adapt_query(query, conn), params)
    return cursor


def _executemany(conn, query, params_seq):
    cursor = conn.cursor()
    cursor.executemany(_adapt_query(query, conn), params_seq)
    return cursor


def _executescript(conn, script_text):
    if isinstance(conn, sqlite3.Connection):
        conn.executescript(script_text)
        return conn.cursor()
    cursor = conn.cursor()
    statements = [stmt.strip() for stmt in script_text.split(';') if stmt.strip()]
    for statement in statements:
        cursor.execute(statement)
    return cursor


def get_db_connection():
    """Create and return a database connection (SQLite or MySQL)."""
    if _uses_sqlite_backend():
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    if pymysql is None:
        raise RuntimeError('PyMySQL is not installed. Add it to requirements.txt.')
    cfg = _mysql_connection_config()
    if not cfg or not cfg['database']:
        raise RuntimeError('MySQL configuration missing: set DATABASE_URL or DB_* environment variables.')

    connect_kwargs = dict(
        host=cfg['host'],
        port=cfg['port'],
        user=cfg['user'],
        password=cfg['password'],
        database=cfg['database'],
        cursorclass=pymysql.cursors.DictCursor,
        charset='utf8mb4',
        autocommit=False,
    )
    if cfg.get('ssl_ca'):
        connect_kwargs['ssl'] = {'ca': cfg['ssl_ca']}  # enforce SSL for Aiven

    return pymysql.connect(**connect_kwargs)


def init_database():
    """Create all tables (and indexes) if they don't already exist, then seed defaults."""
    conn = get_db_connection()
    try:
        if isinstance(conn, sqlite3.Connection):
            _executescript(conn, SQLITE_TABLES)
            conn.commit()
        else:
            _executescript(conn, MYSQL_TABLES)
            conn.commit()
            cursor = conn.cursor()
            for stmt in MYSQL_INDEXES:
                try:
                    cursor.execute(stmt)
                except pymysql.err.OperationalError as exc:
                    # 1061 = duplicate key name (index already exists) — safe to ignore
                    if exc.args and exc.args[0] == 1061:
                        continue
                    raise
            conn.commit()

        ensure_default_rooms(conn)
        ensure_default_services(conn)
        conn.commit()
    finally:
        conn.close()


def ensure_default_rooms(conn=None):
    """Insert default rooms if the rooms table is empty."""
    own_conn = conn is None
    if own_conn:
        conn = get_db_connection()
    try:
        row = _execute(conn, 'SELECT COUNT(*) AS cnt FROM rooms').fetchone()
        if not row['cnt']:
            _executemany(
                conn,
                'INSERT INTO rooms (room_number, room_type, price_per_night, capacity, description) '
                'VALUES (?, ?, ?, ?, ?)',
                DEFAULT_ROOMS,
            )
        if own_conn:
            conn.commit()
    finally:
        if own_conn:
            conn.close()


def ensure_default_services(conn=None):
    """Insert default services if the services table is empty."""
    own_conn = conn is None
    if own_conn:
        conn = get_db_connection()
    try:
        row = _execute(conn, 'SELECT COUNT(*) AS cnt FROM services').fetchone()
        if not row['cnt']:
            _executemany(
                conn,
                'INSERT INTO services (service_name, service_price, description) VALUES (?, ?, ?)',
                DEFAULT_SERVICES,
            )
        if own_conn:
            conn.commit()
    finally:
        if own_conn:
            conn.close()


def get_all_rooms():
    conn = get_db_connection()
    try:
        rows = _execute(conn, 'SELECT * FROM rooms ORDER BY room_number').fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_available_rooms():
    conn = get_db_connection()
    try:
        rows = _execute(
            conn,
            "SELECT * FROM rooms WHERE status = 'Available' ORDER BY room_number",
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_room_by_id(room_id):
    conn = get_db_connection()
    try:
        row = _execute(conn, 'SELECT * FROM rooms WHERE room_id = ?', (room_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_customer(first_name, last_name, email, phone, id_proof_type, id_proof_number, address=None):
    conn = get_db_connection()
    try:
        cursor = _execute(
            conn,
            'INSERT INTO customers (first_name, last_name, email, phone, id_proof_type, '
            'id_proof_number, address) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (first_name, last_name, email, phone, id_proof_type, id_proof_number, address),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def create_booking(customer_id, room_id, check_in_date, number_of_guests, special_requests=None):
    """Create a new active booking and mark the room Occupied. No check-out date yet."""
    conn = get_db_connection()
    try:
        check_in_date = _as_date(check_in_date)
        cursor = _execute(
            conn,
            'INSERT INTO bookings (customer_id, room_id, check_in_date, check_out_date, '
            "number_of_guests, booking_status, special_requests) VALUES (?, ?, ?, NULL, ?, 'Active', ?)",
            (customer_id, room_id, check_in_date.isoformat(), number_of_guests, special_requests),
        )
        booking_id = cursor.lastrowid
        _execute(conn, "UPDATE rooms SET status = 'Occupied' WHERE room_id = ?", (room_id,))
        conn.commit()
        return booking_id
    finally:
        conn.close()


def get_active_bookings():
    conn = get_db_connection()
    try:
        rows = _execute(
            conn,
            '''
            SELECT b.*, c.first_name, c.last_name, c.email AS customer_email, c.phone,
                   r.room_number, r.room_type, r.price_per_night
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN rooms r ON b.room_id = r.room_id
            WHERE b.booking_status = 'Active'
            ORDER BY b.check_in_date
            ''',
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_booking_by_id(booking_id):
    conn = get_db_connection()
    try:
        row = _execute(
            conn,
            '''
            SELECT b.*, c.first_name, c.last_name, c.email AS customer_email, c.phone,
                   c.id_proof_type, c.id_proof_number, c.address,
                   r.room_number, r.room_type, r.price_per_night, r.capacity
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN rooms r ON b.room_id = r.room_id
            WHERE b.booking_id = ?
            ''',
            (booking_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_services():
    conn = get_db_connection()
    try:
        rows = _execute(conn, 'SELECT * FROM services ORDER BY service_name').fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_service_to_booking(booking_id, service_id, quantity=1):
    conn = get_db_connection()
    try:
        cursor = _execute(
            conn,
            'INSERT INTO booking_services (booking_id, service_id, quantity) VALUES (?, ?, ?)',
            (booking_id, service_id, quantity),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_booking_services(booking_id):
    conn = get_db_connection()
    try:
        rows = _execute(
            conn,
            '''
            SELECT bs.*, s.service_name, s.service_price, s.description
            FROM booking_services bs
            JOIN services s ON bs.service_id = s.service_id
            WHERE bs.booking_id = ?
            ''',
            (booking_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def calculate_bill(booking_id, check_out_date):
    """Compute room/service/tax charges for a booking as of a given check-out date.

    Room charges are price_per_night x nights x number_of_guests, matching the
    per-person-per-night model used in the booking_details view in app.py.
    Does not persist anything — see create_bill for that.
    """
    booking = get_booking_by_id(booking_id)
    if not booking:
        return None

    check_in = _as_date(booking['check_in_date'])
    check_out = _as_date(check_out_date)
    nights = (check_out - check_in).days
    if nights <= 0:
        nights = 1

    price_per_night = _to_float(booking['price_per_night'])
    number_of_guests = booking['number_of_guests']
    room_charges = price_per_night * nights * number_of_guests

    services = get_booking_services(booking_id)
    service_charges = sum(_to_float(s['service_price']) * s['quantity'] for s in services)

    tax_amount = (room_charges + service_charges) * TAX_RATE
    total_amount = room_charges + service_charges + tax_amount

    return {
        'booking_id': booking_id,
        'nights': nights,
        'room_charges': room_charges,
        'service_charges': service_charges,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'services': services,
    }


def create_bill(booking_id, room_charges, service_charges, tax_amount, discount, total_amount, payment_method):
    """Persist a bill with precomputed charges (as calculated by calculate_bill)
    and any discount already applied by the caller. Returns the new bill_id."""
    conn = get_db_connection()
    try:
        cursor = _execute(
            conn,
            'INSERT INTO bills (booking_id, room_charges, service_charges, tax_amount, '
            "discount, total_amount, payment_status, payment_method) "
            "VALUES (?, ?, ?, ?, ?, ?, 'Paid', ?)",
            (booking_id, room_charges, service_charges, tax_amount, discount, total_amount, payment_method),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def checkout_booking(booking_id, check_out_date, room_id):
    """Mark a booking Checked Out and free the room. Does not create a bill —
    call create_bill first, as app.py's /checkout route does."""
    conn = get_db_connection()
    try:
        checkout_date = _as_date(check_out_date)
        _execute(
            conn,
            "UPDATE bookings SET booking_status = 'Checked Out', check_out_date = ? WHERE booking_id = ?",
            (checkout_date.isoformat(), booking_id),
        )
        _execute(
            conn,
            "UPDATE rooms SET status = 'Available' WHERE room_id = ?",
            (room_id,),
        )
        conn.commit()
    finally:
        conn.close()


def get_bill_by_id(bill_id):
    conn = get_db_connection()
    try:
        row = _execute(
            conn,
            '''
            SELECT bl.*, b.customer_id, b.room_id, b.check_in_date, b.check_out_date,
                   b.number_of_guests, c.first_name, c.last_name, c.email AS customer_email,
                   c.phone, r.room_number, r.room_type, r.price_per_night
            FROM bills bl
            JOIN bookings b ON bl.booking_id = b.booking_id
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN rooms r ON b.room_id = r.room_id
            WHERE bl.bill_id = ?
            ''',
            (bill_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_bills():
    conn = get_db_connection()
    try:
        rows = _execute(
            conn,
            '''
            SELECT bl.*, c.first_name, c.last_name, r.room_number
            FROM bills bl
            JOIN bookings b ON bl.booking_id = b.booking_id
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN rooms r ON b.room_id = r.room_id
            ORDER BY bl.bill_date DESC
            ''',
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
