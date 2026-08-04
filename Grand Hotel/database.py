from datetime import datetime, date
from decimal import Decimal
import os
import sqlite3
from urllib.parse import urlparse

try:
    import pymysql
except ImportError:
    pymysql = None

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


def _mysql_connection_config():
    if not DATABASE_URL:
        return None

    if DATABASE_URL.startswith('sqlite://'):
        return None

    if not (DATABASE_URL.startswith('mysql://') or DATABASE_URL.startswith('mysql+pymysql://')):
        return None

    parsed = urlparse(DATABASE_URL.replace('mysql+pymysql://', 'mysql://', 1))
    return {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 3306,
        'user': parsed.username or 'root',
        'password': parsed.password or '',
        'database': (parsed.path or '/').lstrip('/'),
    }


def _uses_sqlite_backend():
    return not DATABASE_URL or DATABASE_URL.startswith('sqlite://')


SQLITE_SCHEMA = '''
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
    service_date DATE DEFAULT (CURRENT_DATE),
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
        raise RuntimeError('MySQL backend requires DATABASE_URL to be set.')

    db_name = mysql_cfg['database']
    row = _execute(
        conn,
        'SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_schema = ? AND table_name = ?',
        (db_name, table_name),
    ).fetchone()
    return bool(row['cnt'])

def get_db_connection():
    """Create and return a MySQL database connection using DATABASE_URL."""
    if _uses_sqlite_backend():
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    if pymysql is None:
        raise RuntimeError('PyMySQL is not installed. Add it to requirements and reinstall dependencies.')

    cfg = _mysql_connection_config()
    if not cfg or not cfg['database']:
        raise RuntimeError('DATABASE_URL for MySQL must include a database name.')

    return pymysql.connect(
        host=cfg['host'],
        port=cfg['port'],
        user=cfg['user'],
        password=cfg['password'],
        database=cfg['database'],
        cursorclass=pymysql.cursors.DictCursor,
        charset='utf8mb4',
        autocommit=False,
    )

def init_database():
    """Initialize the database with schema"""
    conn = get_db_connection()
    try:
        should_initialize_schema = not _table_exists(conn, 'rooms')
    finally:
        conn.close()

    if should_initialize_schema:
        conn = get_db_connection()
        if isinstance(conn, sqlite3.Connection):
            _executescript(conn, SQLITE_SCHEMA)
        else:
            with open('mysql_schema.sql', 'r') as f:
                _executescript(conn, f.read())
        conn.commit()
        conn.close()

    ensure_default_rooms()
    ensure_default_services()

def ensure_default_rooms():
    """Ensure all default room numbers exist, including the new 10-room baseline."""
    conn = get_db_connection()
    existing_room_numbers = {
        row['room_number'] for row in _execute(conn, 'SELECT room_number FROM rooms').fetchall()
    }

    missing_rooms = [room for room in DEFAULT_ROOMS if room[0] not in existing_room_numbers]
    if missing_rooms:
        _executemany(
            conn,
            'INSERT INTO rooms (room_number, room_type, price_per_night, capacity, description) VALUES (?, ?, ?, ?, ?)',
            missing_rooms
        )
        conn.commit()

    conn.close()
    return len(missing_rooms)


def ensure_default_services():
    """Ensure seed services exist based on service name."""
    conn = get_db_connection()
    existing_service_names = {
        row['service_name'] for row in _execute(conn, 'SELECT service_name FROM services').fetchall()
    }

    missing_services = [service for service in DEFAULT_SERVICES if service[0] not in existing_service_names]
    if missing_services:
        _executemany(
            conn,
            'INSERT INTO services (service_name, service_price, description) VALUES (?, ?, ?)',
            missing_services,
        )
        conn.commit()

    conn.close()
    return len(missing_services)

def get_available_rooms():
    """Get all available rooms"""
    conn = get_db_connection()
    rooms = _execute(conn, 'SELECT * FROM rooms WHERE status = "Available"').fetchall()
    conn.close()
    return rooms

def get_all_rooms():
    """Get all rooms"""
    conn = get_db_connection()
    rooms = _execute(conn, 'SELECT * FROM rooms ORDER BY room_number').fetchall()
    conn.close()
    return rooms

def get_room_by_id(room_id):
    """Get room by ID"""
    conn = get_db_connection()
    room = _execute(conn, 'SELECT * FROM rooms WHERE room_id = ?', (room_id,)).fetchone()
    conn.close()
    return room

def add_customer(first_name, last_name, email, phone, id_proof_type, id_proof_number, address):
    """Add a new customer"""
    conn = get_db_connection()
    cursor = _execute(
        conn,
        'INSERT INTO customers (first_name, last_name, email, phone, id_proof_type, id_proof_number, address) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (first_name, last_name, email, phone, id_proof_type, id_proof_number, address)
    )
    customer_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return customer_id

def create_booking(customer_id, room_id, check_in_date, number_of_guests, special_requests=''):
    """Create a new booking"""
    conn = get_db_connection()
    cursor = _execute(
        conn,
        'INSERT INTO bookings (customer_id, room_id, check_in_date, number_of_guests, special_requests) VALUES (?, ?, ?, ?, ?)',
        (customer_id, room_id, check_in_date, number_of_guests, special_requests)
    )
    booking_id = cursor.lastrowid
    
    # Update room status
    _execute(conn, 'UPDATE rooms SET status = "Occupied" WHERE room_id = ?', (room_id,))
    conn.commit()
    conn.close()
    return booking_id

def get_active_bookings():
    """Get all active bookings"""
    conn = get_db_connection()
    bookings = _execute(conn, '''
        SELECT b.*, c.first_name, c.last_name, c.phone, r.room_number, r.room_type, r.price_per_night
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN rooms r ON b.room_id = r.room_id
        WHERE b.booking_status = "Active"
        ORDER BY b.check_in_date DESC
    ''').fetchall()
    conn.close()
    return bookings

def get_booking_by_id(booking_id):
    """Get booking details by ID"""
    conn = get_db_connection()
    booking = _execute(conn, '''
        SELECT b.*, c.*, r.room_number, r.room_type, r.price_per_night
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN rooms r ON b.room_id = r.room_id
        WHERE b.booking_id = ?
    ''', (booking_id,)).fetchone()
    conn.close()
    return booking

def get_all_services():
    """Get all available services"""
    conn = get_db_connection()
    services = _execute(conn, 'SELECT * FROM services ORDER BY service_name').fetchall()
    conn.close()
    return services

def add_service_to_booking(booking_id, service_id, quantity=1):
    """Add a service to a booking"""
    conn = get_db_connection()
    _execute(
        conn,
        'INSERT INTO booking_services (booking_id, service_id, quantity) VALUES (?, ?, ?)',
        (booking_id, service_id, quantity)
    )
    conn.commit()
    conn.close()

def get_booking_services(booking_id):
    """Get all services for a booking"""
    conn = get_db_connection()
    services = _execute(conn, '''
        SELECT bs.*, s.service_name, s.service_price
        FROM booking_services bs
        JOIN services s ON bs.service_id = s.service_id
        WHERE bs.booking_id = ?
    ''', (booking_id,)).fetchall()
    conn.close()
    return services

def calculate_bill(booking_id, check_out_date):
    """Calculate bill for a booking"""
    booking = get_booking_by_id(booking_id)
    
    if not booking:
        return None
    
    # Calculate number of nights
    check_in = _as_date(booking['check_in_date'])
    check_out = _as_date(check_out_date)
    nights = (check_out - check_in).days
    if nights <= 0:
        nights = 1
    
    # Calculate room charges (price per person per night × nights × number of guests)
    room_charges = booking['price_per_night'] * nights * booking['number_of_guests']
    
    # Calculate service charges
    services = get_booking_services(booking_id)
    service_charges = sum(s['service_price'] * s['quantity'] for s in services)
    
    # Calculate tax (12% GST)
    subtotal = room_charges + service_charges
    tax_amount = subtotal * Decimal('0.12')
    
    # Total amount
    total_amount = subtotal + tax_amount
    
    return {
        'nights': nights,
        'room_charges': float(room_charges),
        'service_charges': float(service_charges),
        'subtotal': float(subtotal),
        'tax_amount': float(tax_amount),
        'total_amount': float(total_amount)
    }

def create_bill(booking_id, room_charges, service_charges, tax_amount, discount, total_amount, payment_method):
    """Create a bill for checkout"""
    conn = get_db_connection()
    cursor = _execute(
        conn,
        'INSERT INTO bills (booking_id, room_charges, service_charges, tax_amount, discount, total_amount, payment_status, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (booking_id, room_charges, service_charges, tax_amount, discount, total_amount, 'Paid', payment_method)
    )
    bill_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return bill_id

def checkout_booking(booking_id, check_out_date, room_id):
    """Process checkout"""
    conn = get_db_connection()
    _execute(
        conn,
        'UPDATE bookings SET check_out_date = ?, booking_status = "Completed" WHERE booking_id = ?',
        (check_out_date, booking_id)
    )
    _execute(conn, 'UPDATE rooms SET status = "Available" WHERE room_id = ?', (room_id,))
    conn.commit()
    conn.close()

def get_bill_by_id(bill_id):
    """Get bill details"""
    conn = get_db_connection()
    bill = _execute(conn, '''
        SELECT b.*, bk.booking_id, bk.check_in_date, bk.check_out_date, bk.number_of_guests,
               c.first_name, c.last_name, c.email, c.phone, c.address, c.id_proof_type, c.id_proof_number,
               r.room_number, r.room_type, r.price_per_night
        FROM bills b
        JOIN bookings bk ON b.booking_id = bk.booking_id
        JOIN customers c ON bk.customer_id = c.customer_id
        JOIN rooms r ON bk.room_id = r.room_id
        WHERE b.bill_id = ?
    ''', (bill_id,)).fetchone()
    conn.close()
    return bill

def get_all_bills():
    """Get all bills"""
    conn = get_db_connection()
    bills = _execute(conn, '''
        SELECT b.*, c.first_name, c.last_name, r.room_number, bk.check_in_date, bk.check_out_date
        FROM bills b
        JOIN bookings bk ON b.booking_id = bk.booking_id
        JOIN customers c ON bk.customer_id = c.customer_id
        JOIN rooms r ON bk.room_id = r.room_id
        ORDER BY b.bill_date DESC
    ''').fetchall()
    conn.close()
    return bills
