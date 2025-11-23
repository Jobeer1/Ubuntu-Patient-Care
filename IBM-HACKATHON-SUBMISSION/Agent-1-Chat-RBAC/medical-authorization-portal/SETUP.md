# INSTALLATION & DEPLOYMENT GUIDE

## Quick Start (Windows)

### Option 1: Using PowerShell Script
```powershell
cd medical-authorization-portal
.\start.ps1
```

### Option 2: Using Command Prompt
```bash
cd medical-authorization-portal
setup.bat
python app.py
```

### Option 3: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## Access the Application

Once running, open your browser and navigate to:
```
http://localhost:5000
```

## Default Port

The application runs on **port 5000** by default.

To use a different port, modify `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5001, threaded=True)
```

## Database

The application uses SQLite for data storage:
- **Database file**: `users.db` (auto-created in the application directory)
- **Tables**: 
  - `users` - User accounts and credentials
  - `chat_history` - AI chat conversations
  - `authorizations` - Medical pre-authorizations

### Reset Database

To start fresh with a clean database:
```bash
# Delete the existing database
del users.db

# Restart the application
python app.py
```

## Dependencies

All required packages are listed in `requirements.txt`:
- **Flask** 2.3.2 - Web framework
- **Flask-Session** 0.4.0 - Server-side session management
- **Werkzeug** 2.3.6 - WSGI utilities and security

## System Requirements

- **Python**: 3.8 or higher
- **OS**: Windows, macOS, or Linux
- **RAM**: 512MB minimum
- **Disk**: 100MB free space
- **Browser**: Modern browser with HTML5 support

## File Structure

```
medical-authorization-portal/
├── app.py                    # Main Flask application (650+ lines)
├── requirements.txt          # Python dependencies
├── setup.bat                 # Windows batch setup script
├── start.ps1                 # PowerShell startup script
├── README.md                 # User documentation
├── SETUP.md                  # This file
├── templates/                # HTML templates
│   ├── base.html            # Base layout
│   ├── login.html           # Login page
│   ├── register.html        # Registration page
│   ├── dashboard.html       # Dashboard
│   ├── chat.html            # Copilot chat
│   ├── patients.html        # Patient search
│   ├── authorizations.html  # Pre-authorizations
│   ├── 404.html             # Error page
│   └── 500.html             # Error page
├── static/                   # Static assets
│   ├── css/
│   │   └── style.css        # Global stylesheet (700+ lines)
│   └── js/                  # JavaScript files (future)
└── users.db                 # SQLite database (auto-created)
```

## Troubleshooting

### Issue: Port 5000 Already in Use

**Solution**: Either stop the other process or use a different port

```bash
# Use port 5001 instead
python -c "from app import app; app.run(port=5001)"
```

### Issue: ModuleNotFoundError for Flask or Flask-Session

**Solution**: Install dependencies

```bash
pip install -r requirements.txt
```

### Issue: Database Lock Error

**Solution**: The database is being accessed by another process

```bash
# Close all running instances of the application
# Then restart
python app.py
```

### Issue: Template Not Found

**Solution**: Ensure `templates/` folder exists and contains all HTML files

```bash
ls templates/
```

Should show:
- base.html
- login.html
- register.html
- dashboard.html
- chat.html
- patients.html
- authorizations.html
- 404.html
- 500.html

### Issue: CSS/Static Files Not Loading

**Solution**: Verify `static/css/style.css` exists

```bash
ls static/css/
```

Should show `style.css` file

### Issue: Python Version Mismatch

**Solution**: Use Python 3.8 or higher

```bash
python --version
# Should show Python 3.8.0 or higher
```

## Security Considerations

### Authentication
- All passwords are hashed with SHA-256
- Session timeout is set to 24 hours
- Change the SECRET_KEY in production

### To Change Secret Key:
```python
# In app.py, line 43
app.config['SECRET_KEY'] = 'YOUR-UNIQUE-SECRET-KEY-HERE'
```

### Environment Variables
Create a `.env` file for sensitive settings:
```
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secure-key-here
```

## Production Deployment

### Using Gunicorn (Linux/macOS)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Waitress (Windows)
```bash
pip install waitress
waitress-serve --port=5000 app:app
```

### Using Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

## Performance Optimization

### Enable Caching
```python
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year
```

### Database Connection Pooling
```python
# For production, use connection pooling
pip install PyMySQL
# Then modify database connection
```

### Static File Compression
Use a reverse proxy like Nginx for gzip compression

## Logging

To enable detailed logging:

```python
# Add to app.py after Flask initialization
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

## Backup

### Backup Database
```bash
# Windows
copy users.db users.db.backup

# Linux/macOS
cp users.db users.db.backup
```

### Backup All Application Files
```bash
# Windows
xcopy medical-authorization-portal backup /E /I

# Linux/macOS
cp -r medical-authorization-portal backup
```

## Updating Dependencies

To update all packages:
```bash
pip install --upgrade -r requirements.txt
```

## Testing

### Test API Endpoints
```bash
# Using curl
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"test\", \"password\": \"password\"}"
```

### Test Database
```bash
python -c "
import sqlite3
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
print('Tables:', cursor.fetchall())
conn.close()
"
```

## Support & Documentation

- **Main README**: See `README.md` for user guide
- **Flask Documentation**: https://flask.palletsprojects.com/
- **Issue Tracking**: Check application logs in console

## Version Information

- **Application**: v1.0.0
- **Flask**: 2.3.2
- **Python**: 3.8+
- **Last Updated**: January 2024

## Next Steps

1. ✅ Install and run the application
2. 📝 Create a user account via registration
3. 🔐 Login with your credentials
4. 📊 Explore the dashboard
5. 👥 Search for patients
6. 💬 Chat with the AI assistant

Enjoy using the Medical Authorization Portal!
