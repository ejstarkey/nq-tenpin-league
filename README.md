# NQ Tenpin Bowling League Attendance Tracking System

## Version 1.0

A comprehensive web-based Flask application for managing bowling league attendance, payment tracking, and locker rentals for NQ Tenpin Atherton.

## Features

### Core Functionality
- **League Management**: Create and manage multiple concurrent leagues (singles/teams)
- **Bowler Registration**: Import bowlers via CSV or manual entry
- **TBA Verification**: Automated registration status checking
- **Interactive Payment Grid**: Visual attendance and payment tracking
- **Locker Management**: Rental tracking with automated reminders
- **Comprehensive Reporting**: Financial and attendance reports
- **Audit Trail**: Complete logging of all system actions

### User Interface
- Modern dark theme with NQ Tenpin branding (Pink #e91e8c, Blue #52b3d9)
- Responsive design optimized for tablets and desktop
- Interactive spreadsheet-like payment grid
- Real-time balance calculations

## Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager
- SQLite (included with Python)

### Setup Instructions

1. **Clone or extract the application files**
```bash
cd nq_tenpin
```

2. **Create a virtual environment (recommended)**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install required packages**
```bash
pip install -r requirements.txt
```

4. **Initialize the database**
```bash
python app.py
```
This will create the database and a default admin user.

5. **Run the application**
```bash
python app.py
```

The application will be available at: `http://localhost:2019`

## Default Login Credentials

- **Username**: admin
- **Password**: admin123

⚠️ **IMPORTANT**: Change the default password immediately after first login!

## Usage Guide

### Getting Started
1. Login with the default credentials
2. Create staff user accounts from Users menu (admin only)
3. Import bowlers using CSV or add manually
4. Create leagues using the League Creation Wizard
5. Assign bowlers to leagues
6. Track attendance and payments using the interactive grid

### Payment Grid Instructions
- **Left Click**: Mark week as PAID (green ✓)
- **Right Click**: Mark week as MISSED (red X)
- **Double Click**: Enter custom payment amount
- **FIX Button**: Mark fine as paid (appears after marking missed)

### CSV Import Format
The CSV file should have the following columns:
- Registration#
- First Name
- Surname
- SEX
- Email
- Birthday (DD/MM/YYYY format)
- Address
- Suburb
- State
- P/C (Postcode)
- Phone

### TBA Registration Status
- **Green**: Valid registration
- **Red**: Invalid/expired registration
- **Amber**: Verification pending

## Production Deployment

### Using Gunicorn (Recommended)
```bash
gunicorn -w 4 -b 0.0.0.0:2019 app:app
```

### Nginx Configuration (Optional)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:2019;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Environment Variables
Create a `.env` file for production:
```
SECRET_KEY=your-secure-secret-key-here
DATABASE_URL=sqlite:///nq_tenpin.db
```

## Backup Procedures

### Database Backup
```bash
# Create backup
cp nq_tenpin.db backups/nq_tenpin_$(date +%Y%m%d).db

# Restore backup
cp backups/nq_tenpin_20251015.db nq_tenpin.db
```

### Automated Daily Backups
Add to crontab:
```bash
0 2 * * * cd /path/to/nq_tenpin && cp nq_tenpin.db backups/nq_tenpin_$(date +\%Y\%m\%d).db
```

## Security Considerations

1. **Change default passwords immediately**
2. **Use HTTPS in production** (SSL certificate required)
3. **Keep the SECRET_KEY secure and unique**
4. **Regular backups of the database**
5. **Keep Python packages updated**
6. **Implement firewall rules for port 2019**

## Troubleshooting

### Common Issues

**Port 2019 Already in Use**
```bash
# Find process using port
lsof -i :2019
# Kill process if needed
kill -9 [PID]
```

**Database Locked Error**
- Ensure only one instance of the application is running
- Check file permissions on database file

**TBA Verification Not Working**
- Check internet connectivity
- Verify tenpinresults.com.au is accessible
- Check logs in nq_tenpin.log

## Support & Maintenance

### Log Files
- Application logs: `nq_tenpin.log`
- Contains all user actions and system events

### Database Management
- Database file: `nq_tenpin.db`
- SQLite database browser recommended for direct access

### Updates
Check for updates regularly and backup before upgrading.

## Technical Stack

- **Backend**: Python Flask 2.3.3
- **Database**: SQLAlchemy with SQLite
- **Frontend**: Bootstrap 5, jQuery, Chart.js
- **Authentication**: Flask-Login
- **Port**: 2019

## License

© 2025 NQ Tenpin Atherton - All Rights Reserved

## Contact

For technical support or questions about the system, please contact the system administrator.

---

**Version**: 1.0  
**Release Date**: October 15, 2025  
**Developer**: Custom Solution for NQ Tenpin Atherton
