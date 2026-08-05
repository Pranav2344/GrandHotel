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

# ✅ Updated connection config
def _mysql_connection_config():
    """Parse DATABASE_URL or fallback to individual DB_* environment variables."""
    if not DATABASE_URL:
        return {
            'host': os.getenv("DB_HOST", "localhost"),
            'port': int(os.getenv("DB_PORT", 3306)),
            'user': os.getenv("DB_USER", "root"),
            'password': os.getenv("DB_PASSWORD", ""),
            'database': os.getenv("DB_NAME", ""),
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
    }

def _uses_sqlite_backend():
    return not DATABASE_URL or DATABASE_URL.startswith('sqlite://')

SQLITE_SCHEMA = '''
-- your full schema (unchanged)
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

# ✅ Updated get_db_connection
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

# 🔽 All your other functions (init_database, ensure_default_rooms, ensure_default_services,
# get_available_rooms, get_all_rooms, add_customer, create_booking, get_active_bookings,
# get_booking_by_id, get_all_services, add_service_to_booking, get_booking_services,
# calculate_bill, create_bill, checkout_booking, get_bill_by_id, get_all_bills)
# remain unchanged below.
