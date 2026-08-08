from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date
import os

from dotenv import load_dotenv

load_dotenv()

from . import database as db



def _as_date(value):
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.strptime(value, '%Y-%m-%d').date()
    raise TypeError(f'Unsupported date value: {type(value)!r}')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'c8f9a2b6e4d1c7f5a3b8e9d2c6f4a1b7e5d3c9f2a6b4e8d1c7f5a3b9e2d6c4f1')
app.config['JSON_SORT_KEYS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 3600  # Cache static files for 1 hour

# Initialize database on first run
# Initialize database only when explicitly needed — schema already exists in Aiven,
# so skip 20 round-trips to the DB on every cold start.
if os.environ.get('INIT_DB') == 'true':
    db.init_database()

@app.route('/')
def index():
    """Home page with dashboard"""
    active_bookings = db.get_active_bookings()
    available_rooms = db.get_available_rooms()
    all_rooms = db.get_all_rooms()
    
    # Calculate statistics
    total_rooms = len(all_rooms)
    occupied_rooms = sum(1 for room in all_rooms if room['status'] == 'Occupied')
    available_count = sum(1 for room in all_rooms if room['status'] == 'Available')
    
    return render_template('index.html', 
                         active_bookings=active_bookings,
                         total_rooms=total_rooms,
                         occupied_rooms=occupied_rooms,
                         available_rooms=available_count)

@app.route('/rooms')
def rooms():
    """Display all rooms"""
    all_rooms = db.get_all_rooms()
    return render_template('rooms.html', rooms=all_rooms)

@app.route('/checkin', methods=['GET', 'POST'])
def checkin():
    """Check-in page"""
    if request.method == 'POST':
        try:
            # Validate required fields exist
            required_fields = ['first_name', 'last_name', 'phone', 'id_proof_type', 'id_proof_number', 'room_id', 'check_in_date', 'number_of_guests']
            for field in required_fields:
                if field not in request.form or not request.form[field]:
                    flash(f'Error: {field.replace("_", " ").title()} is required!', 'error')
                    available_rooms = db.get_available_rooms()
                    return render_template('checkin.html', rooms=available_rooms, today=date.today().strftime('%Y-%m-%d'))
            
            # Customer details
            first_name = request.form['first_name'].strip()
            last_name = request.form['last_name'].strip()
            email = request.form.get('email', '').strip()
            phone = request.form['phone'].strip()
            id_proof_type = request.form['id_proof_type'].strip()
            id_proof_number = request.form['id_proof_number'].strip()
            address = request.form.get('address', '').strip()
            
            # Booking details
            room_id = request.form['room_id']
            check_in_date = request.form['check_in_date']
            try:
                number_of_guests = int(request.form['number_of_guests'])
            except ValueError:
                flash('Error: Number of guests must be a valid number!', 'error')
                available_rooms = db.get_available_rooms()
                return render_template('checkin.html', rooms=available_rooms, today=date.today().strftime('%Y-%m-%d'))
            
            special_requests = request.form.get('special_requests', '').strip()
            
            # Validate room capacity
            room = db.get_room_by_id(room_id)
            if not room:
                flash('Selected room not found!', 'error')
                available_rooms = db.get_available_rooms()
                return render_template('checkin.html', rooms=available_rooms, today=date.today().strftime('%Y-%m-%d'))
            
            if number_of_guests > room['capacity']:
                flash(f'Error: Room {room["room_number"]} has a maximum capacity of {room["capacity"]} guests. You entered {number_of_guests} guests.', 'error')
                available_rooms = db.get_available_rooms()
                return render_template('checkin.html', rooms=available_rooms, today=date.today().strftime('%Y-%m-%d'))
            
            if number_of_guests < 1:
                flash('Error: At least 1 guest is required!', 'error')
                available_rooms = db.get_available_rooms()
                return render_template('checkin.html', rooms=available_rooms, today=date.today().strftime('%Y-%m-%d'))
            
            # Add customer
            customer_id = db.add_customer(first_name, last_name, email, phone, 
                                         id_proof_type, id_proof_number, address)
            
            # Create booking
            booking_id = db.create_booking(customer_id, room_id, check_in_date, 
                                          number_of_guests, special_requests)
            
            flash(f'Check-in successful! Booking ID: {booking_id}', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error during check-in: {str(e)}', 'error')
    
    available_rooms = db.get_available_rooms()
    today = date.today().strftime('%Y-%m-%d')
    return render_template('checkin.html', rooms=available_rooms, today=today)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Checkout page"""
    if request.method == 'POST':
        try:
            booking_id = request.form['booking_id']
            check_out_date = request.form['check_out_date']
            payment_method = request.form['payment_method']
            discount = float(request.form.get('discount', 0))
            
            # Get booking details
            booking = db.get_booking_by_id(booking_id)
            
            if not booking:
                flash('Booking not found!', 'error')
                return redirect(url_for('checkout'))
            
            # Calculate bill
            bill_details = db.calculate_bill(booking_id, check_out_date)
            
            if not bill_details:
                flash('Error calculating bill!', 'error')
                return redirect(url_for('checkout'))
            
            # Apply discount
            total_amount = bill_details['total_amount'] - discount
            
            # Create bill
            bill_id = db.create_bill(
                booking_id,
                bill_details['room_charges'],
                bill_details['service_charges'],
                bill_details['tax_amount'],
                discount,
                total_amount,
                payment_method
            )
            
            # Update booking status
            db.checkout_booking(booking_id, check_out_date, booking['room_id'])
            
            flash(f'Checkout successful! Bill ID: {bill_id}', 'success')
            return redirect(url_for('invoice', bill_id=bill_id))
        except Exception as e:
            flash(f'Error during checkout: {str(e)}', 'error')
    
    active_bookings = db.get_active_bookings()
    today = date.today().strftime('%Y-%m-%d')
    return render_template('checkout.html', bookings=active_bookings, today=today)

@app.route('/add_service/<int:booking_id>', methods=['GET', 'POST'])
def add_service(booking_id):
    """Add service to booking"""
    if request.method == 'POST':
        try:
            service_id = request.form['service_id']
            quantity = int(request.form.get('quantity', 1))
            
            db.add_service_to_booking(booking_id, service_id, quantity)
            flash('Service added successfully!', 'success')
            return redirect(url_for('booking_details', booking_id=booking_id))
        except Exception as e:
            flash(f'Error adding service: {str(e)}', 'error')
    
    booking = db.get_booking_by_id(booking_id)
    services = db.get_all_services()
    return render_template('add_service.html', booking=booking, services=services)

@app.route('/booking/<int:booking_id>')
def booking_details(booking_id):
    """View booking details"""
    booking = db.get_booking_by_id(booking_id)
    services = db.get_booking_services(booking_id)
    
    if not booking:
        flash('Booking not found!', 'error')
        return redirect(url_for('index'))
    
    # Calculate current charges
    check_in = _as_date(booking['check_in_date'])
    days = (date.today() - check_in).days
    if days <= 0:
        days = 1
    
    # Room charges per person per night × nights × number of guests
    room_charges = booking['price_per_night'] * days * booking['number_of_guests']
    service_charges = sum(s['service_price'] * s['quantity'] for s in services)
    
    return render_template('booking_details.html', 
                         booking=booking, 
                         services=services,
                         room_charges=room_charges,
                         service_charges=service_charges,
                         days=days)

@app.route('/invoice/<int:bill_id>')
def invoice(bill_id):
    """Display invoice"""
    bill = db.get_bill_by_id(bill_id)
    
    if not bill:
        flash('Bill not found!', 'error')
        return redirect(url_for('index'))
    
    services = db.get_booking_services(bill['booking_id'])
    
    # Calculate nights
    check_in = _as_date(bill['check_in_date'])
    check_out = _as_date(bill['check_out_date'])
    nights = (check_out - check_in).days
    if nights <= 0:
        nights = 1
    
    return render_template('invoice.html', bill=bill, services=services, nights=nights)

@app.route('/bills')
def bills():
    """View all bills"""
    all_bills = db.get_all_bills()
    return render_template('bills.html', bills=all_bills)

@app.route('/api/calculate_bill/<int:booking_id>')
def api_calculate_bill(booking_id):
    """API endpoint to calculate bill"""
    check_out_date = request.args.get('checkout_date', date.today().strftime('%Y-%m-%d'))
    bill_details = db.calculate_bill(booking_id, check_out_date)

    if bill_details:
        return jsonify(bill_details)
    else:
        return jsonify({'error': 'Unable to calculate bill'}), 404

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
