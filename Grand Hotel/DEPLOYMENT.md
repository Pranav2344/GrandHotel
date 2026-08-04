# 🚀 Deployment Guide - Grand Hotel

## ✅ Pre-Deployment Checklist

- [x] Removed test files (`test_checkin.py`)
- [x] Cleaned `__pycache__` directory
- [x] Removed debug print statements
- [x] Updated `.gitignore` for production
- [x] Created comprehensive README.md
- [x] Added Procfile for Heroku deployment
- [x] Environment variables documented

## 📋 Files Ready for Deployment

### Core Application Files
- `app.py` - Main Flask application (production-ready)
- `database.py` - Database operations (debug prints removed)
- `mysql_schema.sql` - Database schema
- `requirements.txt` - Python dependencies

### Configuration Files
- `.env.example` - Environment variables template
- `.gitignore` - Git ignore rules (includes cache, db, env files)
- `Procfile` - Heroku deployment configuration
- `README.md` - Complete documentation
- `DEPLOYMENT.md` - This file

### Static Assets
- `static/css/style.css` - Optimized stylesheet (v25.0)
- `static/js/script.js` - Client-side JavaScript
- `static/favicon.svg` - Hotel favicon

### Templates (9 HTML files)
- `base.html` - Base template with navigation
- `index.html` - Dashboard with hotel services & feedback
- `rooms.html` - Room catalog with interior images
- `checkin.html` - Guest check-in form
- `checkout.html` - Guest checkout form
- `booking_details.html` - Booking details view
- `add_service.html` - Service management
- `bills.html` - Billing history
- `invoice.html` - Printable invoice

## 🔐 Security Configuration

### Before Deployment - MANDATORY

1. **Generate SECRET_KEY**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

2. **Create `.env` file**
```bash
cp .env.example .env
```

3. **Update `.env` with production values**
```
FLASK_ENV=production
SECRET_KEY=<your_generated_key_here>
DATABASE_URL=mysql://username:password@db-host:3306/grand_hotel
```

## 🌐 Deployment Options

### Option 1: Heroku (Recommended)

```bash
# Login to Heroku
heroku login

# Create app
heroku create grand-hotel-billing

# Set environment variables
heroku config:set SECRET_KEY=your_secret_key_here
heroku config:set FLASK_ENV=production

# If you want the quickest deployment without a hosted database,
# leave DATABASE_URL unset so the app uses SQLite automatically.

# Deploy
git init
git add .
git commit -m "Initial deployment"
git push heroku main

# Open app
heroku open
```

### Option 2: PythonAnywhere

1. Upload files via Files tab
2. Create virtual environment: `mkvirtualenv grand-hotel`
3. Install requirements: `pip install -r requirements.txt`
4. Configure WSGI file to point to `app.py`
5. Set environment variables in WSGI file
6. Reload web app

### Option 3: DigitalOcean / AWS / VPS

1. **Setup Server**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install nginx
sudo apt install nginx -y
```

2. **Deploy Application**
```bash
# Upload files to /var/www/grand-hotel
cd /var/www/grand-hotel

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Create .env file with production settings
```

3. **Configure Gunicorn**
```bash
# Create systemd service
sudo nano /etc/systemd/system/grandhotel.service
```

```ini
[Unit]
Description=Grand Hotel Billing System
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/grand-hotel
Environment="PATH=/var/www/grand-hotel/.venv/bin"
ExecStart=/var/www/grand-hotel/.venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
```

4. **Configure Nginx**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /var/www/grand-hotel/static;
    }
}
```

5. **Start Services**
```bash
sudo systemctl start grandhotel
sudo systemctl enable grandhotel
sudo systemctl restart nginx
```

### Option 4: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
```

Deploy:
```bash
docker-compose up -d
```

## 📊 Post-Deployment Tasks

### 1. Verify Application
- [ ] Homepage loads correctly
- [ ] All navigation links work
- [ ] Database tables created
- [ ] Default rooms populated (10 rooms)
- [ ] Check-in form works
- [ ] Checkout process completes
- [ ] Invoice generation works
- [ ] Images load correctly

### 2. Performance Optimization
- [ ] Enable gzip compression
- [ ] Configure static file caching
- [ ] Set up CDN for images (optional)
- [ ] Enable HTTPS/SSL
- [ ] Configure database backups

### 3. Monitoring Setup
- [ ] Set up error logging
- [ ] Configure uptime monitoring
- [ ] Enable performance tracking
- [ ] Set up backup automation

### 4. Customization
- [ ] Update hotel name in templates
- [ ] Update contact information
- [ ] Customize invoice header
- [ ] Configure email notifications (if needed)
- [ ] Add custom branding/logo

## 🔧 Troubleshooting

### Database Not Initializing
```bash
# Recreate database and restart
# mysql -u username -p -e "DROP DATABASE IF EXISTS grand_hotel; CREATE DATABASE grand_hotel;"
python app.py
```

### Static Files Not Loading
- Check nginx/apache configuration for static file serving
- Verify file permissions (644 for files, 755 for directories)
- Clear browser cache

### Application Crashes
- Check logs: `heroku logs --tail` or `sudo journalctl -u grandhotel`
- Verify all environment variables are set
- Ensure SECRET_KEY is configured

## 📞 Support

For deployment issues or questions:
- Review README.md for configuration details
- Check application logs for specific errors
- Verify all dependencies installed: `pip list`

---

**Deployment Status**: ✅ Ready for Production  
**Last Cleaned**: March 10, 2026  
**Version**: 2.5
