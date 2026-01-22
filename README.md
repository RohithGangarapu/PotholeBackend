# Pothole Detection System - Backend API

Django REST Framework backend with Firebase Firestore integration for pothole detection and management system.

## Features

- 🔥 **Firebase Firestore Integration** - Real-time database with automatic synchronization
- 📡 **RESTful APIs** - Complete CRUD operations for all entities
- 📚 **Swagger Documentation** - Interactive API documentation at `/api/docs/`
- 🖼️ **Image Upload** - Firebase Storage integration for pothole images
- 🔍 **Advanced Filtering** - Filter by severity, status, device, user, etc.
- 🛡️ **Data Validation** - Comprehensive validation using DRF serializers

## Tech Stack

- **Django 4.2** - Web framework
- **Django REST Framework** - API framework
- **Firebase Admin SDK** - Firestore & Storage integration
- **drf-spectacular** - OpenAPI/Swagger documentation
- **Python 3.8+** - Programming language

## Project Structure

```
backend/
├── app/                          # Main application
│   ├── models.py                 # Django models (for validation)
│   ├── serializers.py            # DRF serializers
│   ├── views.py                  # API ViewSets
│   ├── urls.py                   # App URL configuration
│   ├── admin.py                  # Django admin configuration
│   ├── firebase_config.py        # Firebase initialization
│   └── firebase_service.py       # Firebase CRUD operations
├── backend/                      # Project configuration
│   ├── settings.py               # Django settings
│   └── urls.py                   # Main URL configuration
├── .env                          # Environment variables (create from .env.example)
├── .env.example                  # Example environment configuration
├── requirements.txt              # Python dependencies
└── manage.py                     # Django management script
```

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- Firebase project with Firestore enabled
- Firebase service account JSON file

### 2. Clone and Navigate

```bash
cd /Users/rohith/Desktop/PotholeDetection/backend
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` and update the following:
   - `SECRET_KEY` - Django secret key (keep secure in production)
   - `FIREBASE_CREDENTIALS_PATH` - Path to your Firebase service account JSON
   - `FIREBASE_STORAGE_BUCKET` - Your Firebase storage bucket (e.g., `your-project.appspot.com`)
   - `CORS_ALLOWED_ORIGINS` - Allowed origins for CORS

### 6. Add Firebase Credentials

1. Download your Firebase service account JSON from Firebase Console:
   - Go to Project Settings → Service Accounts
   - Click "Generate New Private Key"
   
2. Save the file as `firebase-credentials.json` in the `backend/` directory

3. Update `.env` file:
```env
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
```

### 7. Run Migrations (Optional)

Although data is stored in Firebase, run migrations for Django's internal tables:

```bash
python manage.py migrate
```

### 8. Create Superuser (Optional)

For Django admin access:

```bash
python manage.py createsuperuser
```

### 9. Start Development Server

```bash
python manage.py runserver
```

The server will start at `http://localhost:8000`

## API Documentation

### Swagger UI (Interactive)
- **URL**: http://localhost:8000/api/docs/
- Interactive API testing interface
- Try out endpoints directly from the browser

### ReDoc (Alternative)
- **URL**: http://localhost:8000/api/redoc/
- Clean, readable API documentation

### OpenAPI Schema
- **URL**: http://localhost:8000/api/schema/
- Raw OpenAPI 3.0 schema in JSON format

## API Endpoints

### Users
- `GET /api/users/` - List all users
- `POST /api/users/` - Create new user
- `GET /api/users/{id}/` - Get user details
- `PUT /api/users/{id}/` - Update user (full)
- `PATCH /api/users/{id}/` - Update user (partial)
- `DELETE /api/users/{id}/` - Delete user

### IOT Devices
- `GET /api/devices/` - List all devices
- `POST /api/devices/` - Register new device
- `GET /api/devices/{id}/` - Get device details
- `PUT /api/devices/{id}/` - Update device (full)
- `PATCH /api/devices/{id}/` - Update device (partial)
- `DELETE /api/devices/{id}/` - Delete device
- `PATCH /api/devices/{id}/update_status/` - Update device status
- `GET /api/devices/by-user/{user_id}/` - Get devices by user

### Potholes
- `GET /api/potholes/` - List all potholes
- `POST /api/potholes/` - Create pothole record
- `GET /api/potholes/{id}/` - Get pothole details
- `PUT /api/potholes/{id}/` - Update pothole (full)
- `PATCH /api/potholes/{id}/` - Update pothole (partial)
- `DELETE /api/potholes/{id}/` - Delete pothole
- `GET /api/potholes/by-severity/{severity}/` - Filter by severity (low/medium/high)
- `GET /api/potholes/by-status/{status}/` - Filter by status (unresolved/fixed/ignored)
- `GET /api/potholes/by-device/{device_id}/` - Filter by device
- `POST /api/potholes/upload_image/` - Upload pothole image

### Alerts
- `GET /api/alerts/` - List all alerts
- `POST /api/alerts/` - Create new alert
- `GET /api/alerts/{id}/` - Get alert details
- `PUT /api/alerts/{id}/` - Update alert (full)
- `PATCH /api/alerts/{id}/` - Update alert (partial)
- `DELETE /api/alerts/{id}/` - Delete alert
- `GET /api/alerts/by-user/{user_id}/` - Get alerts by user
- `GET /api/alerts/by-pothole/{pothole_id}/` - Get alerts by pothole
- `GET /api/alerts/by-type/{type}/` - Filter by type (warning/info/emergency)

## Firebase Schema

### Firestore Collections

#### users
```json
{
  "username": "string",
  "email": "string",
  "phone": "string",
  "createdAt": "timestamp"
}
```

#### iot_devices
```json
{
  "deviceType": "string",
  "macId": "string",
  "status": "active | inactive | blocked",
  "registeredAt": "timestamp",
  "registeredBy": "string (userId)",
  "userId": "string"
}
```

#### potholes
```json
{
  "deviceId": "string",
  "userId": "string",
  "depth": "number",
  "severity": "low | medium | high",
  "imageUrl": "string",
  "detectedAt": "timestamp",
  "status": "unresolved | fixed | ignored",
  "location": {
    "latitude": "number",
    "longitude": "number",
    "address": "string"
  }
}
```

#### alerts
```json
{
  "alertText": "string",
  "alertType": "warning | info | emergency",
  "alertTime": "timestamp",
  "distance": "number (meters)",
  "potholeId": "string",
  "userId": "string"
}
```

## Testing APIs

### Using Swagger UI

1. Navigate to http://localhost:8000/api/docs/
2. Click on any endpoint to expand
3. Click "Try it out"
4. Fill in the required parameters
5. Click "Execute"
6. View the response

### Using cURL

**Create a user:**
```bash
curl -X POST http://localhost:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890"
  }'
```

**Get all potholes:**
```bash
curl http://localhost:8000/api/potholes/
```

**Filter potholes by severity:**
```bash
curl http://localhost:8000/api/potholes/by-severity/high/
```

## Django Admin

Access Django admin at http://localhost:8000/admin/

Features:
- View and manage all entities
- Search and filter capabilities
- Bulk actions
- Detailed fieldsets for complex models

## Development

### Running Tests
```bash
python manage.py test
```

### Collecting Static Files
```bash
python manage.py collectstatic
```

### Creating Migrations (if needed)
```bash
python manage.py makemigrations
python manage.py migrate
```

## Troubleshooting

### Firebase Connection Issues

If you see Firebase-related errors:
1. Verify `firebase-credentials.json` exists and path is correct in `.env`
2. Check Firebase project permissions
3. Ensure Firestore is enabled in Firebase Console

### Import Errors

If you get import errors:
```bash
pip install -r requirements.txt --upgrade
```

### Port Already in Use

If port 8000 is busy:
```bash
python manage.py runserver 8080
```

## Security Notes

⚠️ **Important for Production:**

1. Never commit `.env` or `firebase-credentials.json` to version control
2. Set `DEBUG=False` in production
3. Update `SECRET_KEY` to a secure random value
4. Configure proper `ALLOWED_HOSTS`
5. Use HTTPS in production
6. Implement authentication/authorization
7. Set up proper CORS policies

## License

This project is part of the Pothole Detection System.

## Support

For issues or questions, please refer to the project documentation or contact the development team.
