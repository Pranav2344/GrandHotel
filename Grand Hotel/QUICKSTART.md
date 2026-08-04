# 🏨 Grand Hotel - Quick Start Guide

## 🚀 5-Minute Setup

### For Local Development

```bash
# 1. Navigate to project
cd "Grand Hotel"

# 2. Create virtual environment
python -m venv .venv

# 3. Activate (Windows)
.venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure MySQL in .env
# DATABASE_URL=mysql://username:password@localhost:3306/grand_hotel
# and create DB once:
# mysql -u username -p -e "CREATE DATABASE IF NOT EXISTS grand_hotel;"

# 6. Run application
python app.py

# 7. Open browser
# http://127.0.0.1:5000
```

### For Production (Heroku)

```bash
# 1. Login to Heroku
heroku login

# 2. Create app
heroku create your-hotel-name

# 3. Set SECRET_KEY
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# 4. Deploy
git init
git add .
git commit -m "Deploy Grand Hotel"
git push heroku main

# 5. Open app
heroku open
```

## 📋 Quick Reference

### Default Credentials
- No authentication required (add if needed)

### Default Rooms (10 Total)
- **101**: Standard Single (₹1500/night)
- **102-103**: Standard Double (₹2500/night)
- **201-202**: Deluxe Suite (₹4500/night)
- **301**: Executive Suite (₹7000/night)
- **302**: Presidential Suite (₹12000/night)
- **303**: Executive Family (₹8000/night)
- **401**: Premium Double (₹3200/night)
- **402**: Economy Single (₹1300/night)

### Key Features
- ✅ Real-time dashboard with statistics
- ✅ Room management with interior images
- ✅ Guest check-in/checkout
- ✅ Service management
- ✅ Automated billing with tax
- ✅ Printable invoices
- ✅ Hotel services showcase
- ✅ Customer testimonials

### Important URLs
- **Dashboard**: /
- **Rooms**: /rooms
- **Check-In**: /checkin
- **Check-Out**: /checkout
- **Bills**: /bills

## ⚙️ Configuration

### Environment Variables (.env)
```
FLASK_ENV=production
SECRET_KEY=your_secret_key_here
```

### Customize Hotel Info
Edit `templates/invoice.html`:
- Hotel name
- Address
- Phone & Email

### Modify Room Prices
Edit `database.py` → `DEFAULT_ROOMS` list

## 🛠️ Troubleshooting

**Port in use:**
```bash
# Windows
Get-Process python | Stop-Process -Force

# Linux/Mac
kill $(lsof -t -i:5000)
```

**Database reset:**
```bash
# Create a fresh MySQL database, then restart app
# mysql -u username -p -e "DROP DATABASE IF EXISTS grand_hotel; CREATE DATABASE grand_hotel;"
python app.py
```

**CSS not updating:**
- Hard refresh: Ctrl+Shift+R
- Clear browser cache

## 📚 Documentation

- **Full Guide**: See [README.md](README.md)
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Issues**: Check logs and error messages

## 🎯 Next Steps

1. ✅ Test all features locally
2. ✅ Customize hotel information
3. ✅ Generate production SECRET_KEY
4. ✅ Deploy to hosting platform
5. ✅ Set up SSL/HTTPS
6. ✅ Configure backups

---

**Status**: Ready for Production ✅  
**Version**: 2.5  
**Support**: See README.md for details
