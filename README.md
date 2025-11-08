# Moniqo Backend - AI Agent Trading Platform

Production-ready FastAPI backend for an AI Agent Trading Platform with comprehensive RBAC, caching, and testing.

## Features

- **Test-Driven Development (TDD):** Complete test coverage for all modules
- **RBAC:** Role-Based Access Control with permissions
- **Soft Deletes:** All deletions are soft (is_deleted flag)
- **Caching:** Redis-based caching with automatic invalidation
- **Rate Limiting:** 100 requests/minute per user (unlimited for admins)
- **Background Tasks:** Async email sending and notifications
- **File Upload:** AWS S3 integration for avatars
- **Email Service:** Resend integration for transactional emails
- **API Documentation:** Auto-generated OpenAPI docs at `/docs`

## Tech Stack

- **Framework:** FastAPI 0.104.1
- **Database:** MongoDB with Motor (async)
- **Cache/Queue:** Redis
- **Auth:** JWT (python-jose)
- **Storage:** AWS S3
- **Email:** Resend
- **Testing:** pytest + pytest-asyncio + httpx

## Project Structure

```
Moniqo_BE/
├── app/
│   ├── config/          # Configuration and database setup
│   ├── core/            # Security, dependencies, responses, exceptions
│   ├── modules/         # Feature modules (auth, users, roles, etc.)
│   ├── providers/       # Third-party integrations (AWS, Resend)
│   ├── utils/           # Utilities (cache, logger, pagination)
│   ├── middleware/      # Rate limiting, logging, error handling
│   └── tasks/           # Background tasks
├── tests/               # Test suite
├── scripts/             # Initialization scripts
├── logs/                # Application logs
└── requirements.txt     # Python dependencies
```

## Setup Instructions

### 1. Prerequisites

- Python 3.11+
- MongoDB instance (local or remote)
- Redis instance (local or remote)
- AWS S3 account (for file uploads)
- Resend account (for emails)

### 2. Clone and Setup

```bash
# Clone the repository
cd /path/to/Moniqo_BE

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables

```bash
# Copy the example env file
cp env.example .env

# Edit .env with your actual credentials
nano .env  # or your preferred editor
```

**Required Variables:**
- `MONGODB_URL`: MongoDB connection string (format: `mongodb://user:pass@host:port/database`)
- `REDIS_URL`: Redis connection string (format: `redis://:password@host:port`)
- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET_NAME`: AWS S3 credentials
- `RESEND_API_KEY`: Resend email API key
- `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`: Initial superadmin credentials

### 4. Run the Application

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Access API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/verify-email` - Email verification
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password

### Users
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update current user
- `DELETE /api/v1/users/me` - Soft delete current user
- `POST /api/v1/users/me/avatar` - Upload avatar
- `GET /api/v1/users` - List users (admin only)
- `GET /api/v1/users/{id}` - Get user by ID (admin only)

### Roles & Permissions
- `GET /api/v1/roles` - List roles
- `POST /api/v1/roles` - Create role (superadmin only)
- `GET /api/v1/permissions` - List permissions
- `POST /api/v1/permissions` - Create permission (superadmin only)

### Plans & Subscriptions
- `GET /api/v1/plans` - List plans (public)
- `POST /api/v1/plans` - Create plan (admin only)
- `GET /api/v1/users/me/plans` - Get user's subscriptions
- `POST /api/v1/users/me/plans` - Subscribe to plan

### Notifications
- `GET /api/v1/notifications` - Get user's notifications
- `PUT /api/v1/notifications/{id}/view` - Mark as viewed

## Development Guidelines

### Code Quality Standards
- **Type hints:** Required for all functions
- **Docstrings:** Google style for all functions/classes
- **Atomic functions:** Single responsibility principle
- **No hardcoded values:** Use environment variables
- **Logging:** Context-rich logging (never log sensitive data)

### Testing Requirements
- **TDD:** Write tests BEFORE implementation
- **Coverage:** 80%+ target
- **Test types:** Positive, negative, edge cases

### Response Format
All endpoints return standardized responses:

```json
{
    "status_code": 200,
    "message": "Success message",
    "data": { ... },
    "error": null
}
```

## Deployment

See workspace `.cursorrules` for Docker deployment guidelines.

## Phase 1 Modules

- ✅ Auth (registration, login, verification, password reset)
- ✅ Users (CRUD, avatar upload, soft delete)
- ✅ Roles (RBAC with permissions)
- ✅ Permissions (resource:action format)
- ✅ Plans (subscription plans)
- ✅ User Plans (user subscriptions)
- ✅ Notifications (in-app notifications)

## Contributing

1. Follow TDD workflow
2. Write tests first
3. Implement features
4. Run tests before committing
5. Ensure 80%+ coverage

## License

Proprietary - All rights reserved

## Support

For issues or questions, contact the development team.

