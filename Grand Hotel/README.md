# 🏨 Grand Hotel - Professional Hotel Billing System

A modern, production-ready hotel management and billing system built with Flask, featuring an elegant UI with hotel-themed branding, room imagery, and customer feedback integration.

## ✨ Features

### 🎨 Professional Design
- **Hotel-Themed Branding**: Beautiful hotel exterior background with custom imagery
- **Room Showcase**: Interior photos for each room type (Presidential, Executive, Deluxe, Standard, Economy)
- **Customer Feedback**: Testimonials section showcasing guest experiences
- **Hotel Services**: Visual service cards with background images for key amenities
- **Responsive Design**: Fully mobile-friendly and adapts to all screen sizes
- **Modern UI/UX**: Clean interface with smooth animations and hover effects

### 🏨 Core Functionality
- **Dashboard**: Real-time overview with statistics, active bookings, quick actions, hotel services, and customer feedback
- **Room Management**: Visual catalog of 10 rooms with specific interior images
- **Guest Check-In**: Comprehensive form with validation for new guest registration
- **Guest Check-Out**: Process checkout with automated bill calculation
- **Billing System**: Professional invoice generation with itemized breakdowns
- **Service Management**: Add room service, laundry, dining, and other services to bookings

### 💎 Business Features
- **Room Inventory**: 10 pre-configured rooms (Single, Double, Deluxe, Executive, Presidential)
- **Dynamic Pricing**: Per-night, per-guest pricing with capacity management
- **Service Charges**: Track additional services with automatic bill calculation
- **Tax Calculation**: Automatic 12% tax on room and service charges
- **Payment Methods**: Support for Cash, Card, and UPI payments
- **Booking History**: Complete guest and booking records with timestamps

## 🚀 Technology Stack

- **Backend**: Python 3.11+ with Flask
- **Database**: MySQL (via `DATABASE_URL`)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Images**: Unsplash integration for high-quality hotel imagery
- **Fonts**: Inter (Google Fonts)

## 📦 Installation & Deployment

### Local Development

1. **Navigate to project directory**
```bash
cd "Grand Hotel"
```

2. **Create virtual environment**
```bash
python -m venv .venv
```

3. **Activate virtual environment**
   - Windows: `.venv\Scripts\Activate.ps1`
   - Linux/Mac: `source .venv/bin/activate`

4. **Install dependencies**
```bash
pip install -r requirements.txt
```

5. **Configure MySQL connection**
    ```
    DATABASE_URL=mysql://username:password@localhost:3306/grand_hotel
    ```

6. **Run the application**
```bash
python app.py
```

7. **Access the application**
```
http://127.0.0.1:5000
```

- **Desktop**: 1280px+ (full layout)
- **Tablet**: 768px - 1024px (adjusted grid)
- **Mobile**: 480px - 768px (single column)
- **Small Mobile**: < 480px (optimized for small screens)

## 🖨️ Print Optimization

The invoice page includes print-specific styles:
- Removes navigation, footer, and buttons
- Optimizes layout for paper
- Removes shadows and backgrounds
- Ensures all information is visible

## 🔧 Customization

### Change Color Scheme
Edit the CSS variables in `static/css/style.css`:
```css


### Production Deployment

#### Environment Configuration
1. **Create `.env` file** (copy from `.env.example`)
```bash
cp .env.example .env
```

2. **Generate secure SECRET_KEY**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

3. **Update `.env` with production values**
```
FLASK_ENV=production
SECRET_KEY=your_generated_secret_key_here
```

#### Deploy to Cloud Platforms

**Heroku:**
```bash
# Add Procfile
echo "web: gunicorn app:app" > Procfile

# Deploy
heroku create your-hotel-name
git push heroku main
```

**PythonAnywhere / DigitalOcean / AWS:**
- Upload project files
- Install requirements: `pip install -r requirements.txt`
- Configure WSGI server (Gunicorn/uWSGI)
- Set environment variables
- Point web server to `app.py`

#### Security Checklist for Production
- [ ] Change SECRET_KEY to a strong random value
- [ ] Set `FLASK_ENV=production`
- [ ] Enable HTTPS/SSL
- [ ] Set up database backups
- [ ] Configure firewall rules
- [ ] Use a production WSGI server (Gunicorn/uWSGI)
- [ ] Set up logging and monitoring
- [ ] Review and update hotel information in templates

## 📂 Project Structure

```
Grand Hotel/
├── app.py                  # Flask application and routes
├── database.py             # Database operations and models
├── mysql_schema.sql        # MySQL schema
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── README.md              # This file
├── static/
│   ├── css/
│   │   └── style.css      # Main stylesheet (v25.0)
│   └── js/
│       └── script.js      # Client-side JavaScript
└── templates/
    ├── base.html          # Base template with navigation
    ├── index.html         # Dashboard with stats and services
    ├── rooms.html         # Room catalog with images
    ├── checkin.html       # Guest check-in form
    ├── checkout.html      # Guest checkout form
    ├── booking_details.html # Booking information view
    ├── add_service.html   # Add services to booking
    ├── bills.html         # Bill history
    └── invoice.html       # Printable invoice
```

## 🔧 Configuration

### Room Inventory
Default rooms are configured in `database.py`:
- **Room 101**: Standard Single (1500/night, 1 guest)
- **Room 102**: Standard Double - City View (2500/night, 2 guests)
- **Room 103**: Standard Double - Garden View (2500/night, 2 guests)
- **Room 201**: Deluxe Suite - Living Area (4500/night, 3 guests)
- **Room 202**: Deluxe Suite - Balcony (4500/night, 3 guests)
- **Room 301**: Executive Suite - Jacuzzi (7000/night, 4 guests)
- **Room 302**: Presidential Suite (12000/night, 6 guests)
- **Room 303**: Executive Family Suite (8000/night, 5 guests)
- **Room 401**: Premium Double (3200/night, 2 guests)
- **Room 402**: Economy Single (1300/night, 1 guest)

### Customize Hotel Information
Update hotel details in [templates/invoice.html](templates/invoice.html):
```html
<h1>🏨 Grand Hotel</h1>
<p>📍 123 Hotel Street, City, Country</p>
<p>📞 Phone: +1-234-567-8900 | 📧 Email: info@grandhotel.com</p>
```

### Modify Theme Colors
Edit CSS variables in [static/css/style.css](static/css/style.css):
```css
:root {
    --primary-color: #6366f1;
    --primary-dark: #4f46e5;
    /* Modify these values to match your brand */
}
```

## 🎯 Usage Guide

### 1. Dashboard
- View real-time statistics (Total Rooms, Occupied, Available, Active Bookings)
- Monitor active bookings table
- Quick access to Check-In, Check-Out, View Rooms, View Bills
- Explore hotel services and customer testimonials

### 2. Check-In Process
1. Navigate to "Check-In" from dashboard or menu
2. Fill guest information (name, phone, ID proof, etc.)
3. Select available room and check-in date
4. Specify number of guests (validates against room capacity)
5. Add special requests (optional)
6. Submit to create booking

### 3. Managing Bookings
- View all active bookings from dashboard
- Click booking to see details and add services
- Services: Room Service, Laundry, Dining, Spa, etc.

### 4. Check-Out Process
1. Navigate to "Check-Out" from menu
2. Select booking from active list
3. Set check-out date
4. Review calculated bill (room + services + tax)
5. Apply discount if applicable
6. Select payment method (Cash/Card/UPI)
7. Generate and print invoice

## 🎨 Features Showcase

### Hotel Services (Dashboard)
- **Luxury Accommodations**: Premium rooms with modern amenities
- **24/7 Concierge**: Round-the-clock guest assistance
- **Room Service**: In-room dining and amenities delivery
- **Business Center**: Meeting rooms and business facilities
- **Spa & Wellness**: Relaxation and fitness services
- **Prime Location**: Accessible city center location

### Customer Feedback
- Real guest testimonials
- 5-star rating display
- Professional presentation

## 📊 Database Schema

- **customers**: Guest information (name, contact, ID proof)
- **rooms**: Room inventory (number, type, price, capacity, status)
- **bookings**: Reservation records with check-in/out dates

Schema files:
- `mysql_schema.sql` for MySQL
- **services**: Available hotel services catalog
- **booking_services**: Services added to specific bookings
- **bills**: Final billing records with payment details

## 🛠️ Troubleshooting

**Database Issues:**
- Ensure MySQL server is running and `DATABASE_URL` points to an existing database

**Port Already in Use:**
```bash
# Find and stop process using port 5000
Get-Process python | Stop-Process -Force  # Windows
kill $(lsof -t -i:5000)  # Linux/Mac
```

**CSS Not Updating:**
- Hard refresh browser (Ctrl+Shift+R)
- CSS version is auto-incremented (currently v=25.0)

## 📝 License

This project is open source and available for educational and commercial use.

## 🙏 Acknowledgments

- **Images**: Unsplash for high-quality hotel photography
- **Fonts**: Google Fonts (Inter)
- **Framework**: Flask (Python web framework)

---

**Version**: 2.5 (Production-Ready Edition)  
**Last Updated**: March 2026  
**Status**: ✅ Deployment Ready
