# Demo Login Credentials for SA PACS Testing

## Available Test Accounts

### 1. Administrator Account
- **Username**: `admin`
- **Password**: `admin123`
- **Role**: System Administrator
- **Facility**: Gauteng Provincial Hospital
- **Email**: admin@hospital.co.za

### 2. Doctor/Radiologist Account
- **Username**: `doctor`
- **Password**: `doctor123`
- **Role**: Radiologist
- **Name**: Dr. Sarah Mthembu
- **Facility**: Chris Hani Baragwanath Hospital
- **Email**: sarah.mthembu@hospital.co.za

### 3. Nurse Account
- **Username**: `nurse`
- **Password**: `nurse123`
- **Role**: Nursing Sister
- **Name**: Sister Nomsa Dlamini
- **Facility**: Soweto Community Clinic
- **Email**: nomsa.dlamini@clinic.co.za

## Testing Instructions

1. **Start the Backend Server**:
   ```bash
   cd "orthanc-source/NASIntegration"
   python run_server.py
   ```

2. **Start the React Frontend**:
   ```bash
   cd "orthanc-source/NASIntegration/web_interfaces"
   npm run dev
   ```

3. **Access the Application**:
   - Frontend: http://localhost:3001
   - Backend API: http://localhost:5000

## Authentication Flow

1. Navigate to the login page
2. Enter one of the username/password combinations above
3. The system will create a session and redirect to the dashboard
4. Different roles have different permissions and UI elements

## API Testing

You can also test the authentication API directly:

```bash
# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Check session
curl -X GET http://localhost:5000/api/auth/session \
  --cookie-jar cookies.txt --cookie cookies.txt
```

## Security Notes

⚠️ **These are demo credentials for development/testing only!**
- Never use these passwords in production
- In production, passwords should be properly hashed
- Implement proper password policies
- Use secure session management

## Features to Test by Role

### Admin
- Full system access
- User management
- System configuration
- All DICOM operations

### Doctor/Radiologist
- Patient data access
- DICOM viewing and analysis
- Reporting features
- Consultation tools

### Nurse
- Basic patient data
- Limited DICOM access
- Patient care documentation
- Workflow management
