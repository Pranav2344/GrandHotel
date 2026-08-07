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


# Write Aiven CA certificate to /tmp at startup (Vercel filesystem is read-only
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


SQLITE_SCHEMA = '''
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number TEXT UNIQUE NOT NULL,
    room_type TEXT NOT NULL,
    price REAL NOT NULL,
    capacity INTEGER NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'available'
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers (id),
    FOREIGN KEY (room_id) REFERENCES rooms (id)
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    price REAL NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS booking_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings (id),
    FOREIGN KEY (service_id) REFERENCES services (id)
);

CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    room_charge REAL NOT NULL,
    service_charge REAL NOT NULL,
    total_amount REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings (id)
);
'''

MYSQL_SCHEMA = '''
CREATE TABLE IF NOT EXISTS rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_number VARCHAR(20) UNIQUE NOT NULL,
    room_type VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    capacity INT NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'available'
);

CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150),
    phone VARCHAR(30),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    room_id INT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers (id),
    FOREIGN KEY (room_id) REFERENCES rooms (id)
);

CREATE TABLE IF NOT EXISTS services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS booking_services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    service_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings (id),
    FOREIGN KEY (service_id) REFERENCES services (id)
);

CREATE TABLE IF NOT EXISTS bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    room_charge DECIMAL(10,2) NOT NULL,
    service_charge DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings (id)
);
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


def _table_exists(conn, table_name):
    if isinstance(conn, sqlite3.Connection):
        row = _execute(
            conn,
            'SELECT COUNT(*) AS cnt FROM sqlite_master WHERE type = ? AND name = ?',
            ('table', table_name),
        ).fetchone()
        return bool(row['cnt'])
    mysql_cfg = _mysql_connection_config()
    if mysql_cfg is None:
        raise RuntimeError('MySQL backend requires DATABASE_URL or DB_* env vars to be set.')
    db_name = mysql_cfg['database']
    row = _execute(
        conn,
        'SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_schema = ? AND table_name = ?',
        (db_name, table_name),
    ).fetchone()
    return bool(row['cnt'])


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
    """Create all tables if they don't already exist, then seed defaults."""
    conn = get_db_connection()
    try:
        schema = SQLITE_SCHEMA if isinstance(conn, sqlite3.Connection) else MYSQL_SCHEMA
        _executescript(conn, schema)
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
        count = row['cnt']
        if not count:
            _executemany(
                conn,
                'INSERT INTO rooms (room_number, room_type, price, capacity, description) '
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
        count = row['cnt']
        if not count:
            _executemany(
                conn,
                'INSERT INTO services (name, price, description) VALUES (?, ?, ?)',
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
            "SELECT * FROM rooms WHERE status = 'available' ORDER BY room_number",
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_customer(name, email=None, phone=None, address=None):
    conn = get_db_connection()
    try:
        cursor = _execute(
            conn,
            'INSERT INTO customers (name, email, phone, address) VALUES (?, ?, ?, ?)',
            (name, email, phone, address),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def create_booking(customer_id, room_id, check_in, check_out=None):
    conn = get_db_connection()
    try:
        check_in = _as_date(check_in)
        if check_out:
            check_out = _as_date(check_out)
        cursor = _execute(
            conn,
            'INSERT INTO bookings (customer_id, room_id, check_in, check_out, status) '
            "VALUES (?, ?, ?, ?, 'active')",
            (customer_id, room_id, check_in.isoformat(), check_out.isoformat() if check_out else None),
        )
        booking_id = cursor.lastrowid
        _execute(conn, "UPDATE rooms SET status = 'occupied' WHERE id = ?", (room_id,))
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
            SELECT b.*, c.name AS customer_name, c.email AS customer_email,
                   r.room_number, r.room_type, r.price AS room_price
            FROM bookings b
            JOIN customers c ON b.customer_id = c.id
            JOIN rooms r ON b.room_id = r.id
            WHERE b.status = 'active'
            ORDER BY b.check_in
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
            SELECT b.*, c.name AS customer_name, c.email AS customer_email,
                   r.room_number, r.room_type, r.price AS room_price
            FROM bookings b
            JOIN customers c ON b.customer_id = c.id
            JOIN rooms r ON b.room_id = r.id
            WHERE b.id = ?
            ''',
            (booking_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_services():
    conn = get_db_connection()
    try:
        rows = _execute(conn, 'SELECT * FROM services ORDER BY name').fetchall()
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
            SELECT bs.*, s.name, s.price, s.description
            FROM booking_services bs
            JOIN services s ON bs.service_id = s.id
            WHERE bs.booking_id = ?
            ''',
            (booking_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def calculate_bill(booking_id):
    """Compute room charge and service charge for a booking without saving it."""
    booking = get_booking_by_id(booking_id)
    if not booking:
        raise ValueError(f'Booking {booking_id} not found')

    check_in = _as_date(booking['check_in'])
    check_out = _as_date(booking['check_out']) if booking.get('check_out') else date.today()
    nights = max((check_out - check_in).days, 1)

    room_price = _to_float(booking['room_price'])
    room_charge = room_price * nights

    services = get_booking_services(booking_id)
    service_charge = sum(_to_float(s['price']) * s['quantity'] for s in services)

    total_amount = room_charge + service_charge
    return {
        'booking_id': booking_id,
        'nights': nights,
        'room_charge': room_charge,
        'service_charge': service_charge,
        'total_amount': total_amount,
        'services': services,
    }


def create_bill(booking_id):
    """Calculate and persist a bill for a booking."""
    bill_data = calculate_bill(booking_id)
    conn = get_db_connection()
    try:
        cursor = _execute(
            conn,
            'INSERT INTO bills (booking_id, room_charge, service_charge, total_amount) '
            'VALUES (?, ?, ?, ?)',
            (
                booking_id,
                bill_data['room_charge'],
                bill_data['service_charge'],
                bill_data['total_amount'],
            ),
        )
        conn.commit()
        bill_id = cursor.lastrowid
        bill_data['id'] = bill_id
        return bill_data
    finally:
        conn.close()


def checkout_booking(booking_id, check_out=None):
    """Mark a booking as checked out, free the room, and generate its final bill."""
    conn = get_db_connection()
    try:
        booking = get_booking_by_id(booking_id)
        if not booking:
            raise ValueError(f'Booking {booking_id} not found')

        check_out_date = _as_date(check_out) if check_out else date.today()
        _execute(
            conn,
            "UPDATE bookings SET status = 'checked_out', check_out = ? WHERE id = ?",
            (check_out_date.isoformat(), booking_id),
        )
        _execute(
            conn,
            "UPDATE rooms SET status = 'available' WHERE id = ?",
            (booking['room_id'],),
        )
        conn.commit()
    finally:
        conn.close()

    return create_bill(booking_id)


def get_bill_by_id(bill_id):
    conn = get_db_connection()
    try:
        row = _execute(
            conn,
            '''
            SELECT bl.*, b.customer_id, c.name AS customer_name, r.room_number
            FROM bills bl
            JOIN bookings b ON bl.booking_id = b.id
            JOIN customers c ON b.customer_id = c.id
            JOIN rooms r ON b.room_id = r.id
            WHERE bl.id = ?
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
            SELECT bl.*, c.name AS customer_name, r.room_number
            FROM bills bl
            JOIN bookings b ON bl.booking_id = b.id
            JOIN customers c ON b.customer_id = c.id
            JOIN rooms r ON b.room_id = r.id
            ORDER BY bl.created_at DESC
            ''',
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
