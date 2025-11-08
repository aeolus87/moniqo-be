# 🚀 PHASE 1.5: API DOCUMENTATION SETUP - AI IMPLEMENTATION PROMPT

You are an expert FastAPI backend developer tasked with implementing comprehensive API documentation for the **AI Agent Trading Platform** using **Swagger UI** and **ReDoc**.

---

## 🎯 YOUR MISSION

Add professional, interactive API documentation to the existing Phase 1 FastAPI backend. This documentation will be used by frontend developers, API consumers, and for testing purposes.

---

## 📋 WHAT YOU NEED TO DO

### **CRITICAL: Test-Driven Development (TDD)**

**YOU MUST FOLLOW THIS ORDER:**

1. ✅ **FIRST:** Write comprehensive tests in `tests/test_documentation.py`
2. ✅ **SECOND:** Implement the documentation features to make tests pass
3. ✅ **THIRD:** Run tests and verify everything works

**DO NOT write implementation before tests!**

---

## 🎯 OBJECTIVES

1. **Setup Swagger UI** accessible at `/api/docs`
2. **Setup ReDoc** accessible at `/api/redoc`
3. **Configure OpenAPI schema** at `/api/openapi.json`
4. **Add JWT security scheme** to OpenAPI
5. **Organize all endpoints with tags** (Authentication, Users, Roles, Permissions, Plans, Notifications)
6. **Add detailed descriptions** to every endpoint (summary, description, response examples)
7. **Add schema examples** to all Pydantic models with Field() descriptions
8. **Add response examples** for success (200, 201) and error cases (400, 401, 403, 404, 422, 429)
9. **Document authentication requirements** clearly
10. **Add common response schemas** to OpenAPI components

---

## 📁 FILES YOU WILL CREATE/MODIFY

```
backend/
├── app/
│   ├── main.py                          # UPDATE: Add custom OpenAPI configuration
│   │
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── router.py               # UPDATE: Add endpoint documentation
│   │   │   └── schemas.py              # UPDATE: Add Field descriptions & examples
│   │   │
│   │   ├── users/
│   │   │   ├── router.py               # UPDATE: Add endpoint documentation
│   │   │   └── schemas.py              # UPDATE: Add Field descriptions & examples
│   │   │
│   │   ├── roles/
│   │   │   ├── router.py               # UPDATE: Add endpoint documentation
│   │   │   └── schemas.py              # UPDATE: Add Field descriptions & examples
│   │   │
│   │   ├── permissions/
│   │   │   ├── router.py               # UPDATE: Add endpoint documentation
│   │   │   └── schemas.py              # UPDATE: Add Field descriptions & examples
│   │   │
│   │   ├── plans/
│   │   │   ├── router.py               # UPDATE: Add endpoint documentation
│   │   │   └── schemas.py              # UPDATE: Add Field descriptions & examples
│   │   │
│   │   └── notifications/
│   │       ├── router.py               # UPDATE: Add endpoint documentation
│   │       └── schemas.py              # UPDATE: Add Field descriptions & examples
│   │
│   └── tests/
│       └── test_documentation.py        # CREATE: Documentation tests
```

---

## 🧪 STEP 1: CREATE TESTS FIRST (test_documentation.py)

Create `tests/test_documentation.py` with these test cases:

### **Required Test Cases:**

```python
"""Tests for API documentation endpoints."""

import pytest
from httpx import AsyncClient
from app.main import app


class TestAPIDocumentation:
    """Test suite for API documentation."""
    
    # Test 1: Swagger UI is accessible
    @pytest.mark.asyncio
    async def test_swagger_ui_accessible(self):
        """Test that Swagger UI is accessible at /api/docs."""
        # Should return 200 and HTML content with "swagger-ui"
        pass
    
    # Test 2: ReDoc is accessible
    @pytest.mark.asyncio
    async def test_redoc_accessible(self):
        """Test that ReDoc is accessible at /api/redoc."""
        # Should return 200 and HTML content with "redoc"
        pass
    
    # Test 3: OpenAPI schema is accessible
    @pytest.mark.asyncio
    async def test_openapi_schema_accessible(self):
        """Test that OpenAPI schema is accessible at /api/openapi.json."""
        # Should return 200 and valid JSON with "openapi", "info", "paths", "components"
        pass
    
    # Test 4: Security scheme is defined
    @pytest.mark.asyncio
    async def test_openapi_schema_has_security_scheme(self):
        """Test that OpenAPI schema includes JWT BearerAuth security scheme."""
        # Should have components.securitySchemes.BearerAuth with type="http", scheme="bearer", bearerFormat="JWT"
        pass
    
    # Test 5: Tags are defined
    @pytest.mark.asyncio
    async def test_openapi_schema_has_tags(self):
        """Test that OpenAPI schema includes properly organized tags."""
        # Should have tags: Authentication, Users, Roles, Permissions, Plans, Notifications
        pass
    
    # Test 6: All endpoints have summaries
    @pytest.mark.asyncio
    async def test_all_endpoints_have_summary(self):
        """Test that all endpoints have a summary field."""
        # Every path operation should have non-empty "summary"
        pass
    
    # Test 7: All endpoints have descriptions
    @pytest.mark.asyncio
    async def test_all_endpoints_have_description(self):
        """Test that all endpoints have a description field."""
        # Every path operation should have non-empty "description"
        pass
    
    # Test 8: Schemas have descriptions
    @pytest.mark.asyncio
    async def test_schemas_have_descriptions(self):
        """Test that all schemas have descriptions or titles."""
        # All schemas in components.schemas should have "description" or "title"
        # Skip internal schemas like Body_, HTTPValidationError
        pass
```

**Write the full implementation of these tests with proper assertions!**

---

## 🔧 STEP 2: UPDATE main.py

In `app/main.py`, add the following:

### **Required Changes:**

1. **Update FastAPI initialization:**
   - Set `title="AI Agent Trading Platform API"`
   - Set detailed `description` (multi-paragraph markdown explaining features, auth, rate limits, pagination, response format)
   - Set `version="1.0.0"`
   - Set `docs_url="/api/docs"` (Swagger UI)
   - Set `redoc_url="/api/redoc"` (ReDoc)
   - Set `openapi_url="/api/openapi.json"`
   - Add `contact` with name, email, url
   - Add `license_info` with name and url

2. **Create custom_openapi() function:**
   ```python
   def custom_openapi():
       # Generate base schema with get_openapi()
       # Add security scheme: BearerAuth (http, bearer, JWT)
       # Add tags with descriptions for all modules
       # Add common response schemas (SuccessResponse, ErrorResponse)
       # Cache and return schema
   ```

3. **Set custom OpenAPI:**
   ```python
   app.openapi = custom_openapi
   ```

### **Description Content to Include:**

- Overview of platform features (auth, RBAC, plans, notifications, caching, rate limiting)
- Authentication instructions (how to get token, how to use it)
- Rate limit information (100/min for users, unlimited for admins)
- Pagination documentation (limit/offset parameters, defaults, max values)
- Response format documentation (success and error response structures with examples)
- Contact information for support

### **Tags to Define:**

Each tag needs a name and detailed description:

1. **Authentication** - Registration, login, verification, password reset
2. **Users** - Profile management, avatar upload, user administration
3. **Roles** - Role management for RBAC (admin only)
4. **Permissions** - Permission management (superadmin only)
5. **Plans** - Subscription plan management
6. **Notifications** - In-app and email notifications

### **Security Scheme:**

```python
"BearerAuth": {
    "type": "http",
    "scheme": "bearer",
    "bearerFormat": "JWT",
    "description": "Enter your JWT access token. Format: Bearer <token>"
}
```

### **Common Response Schemas:**

Add `SuccessResponse` and `ErrorResponse` schemas to `components.schemas` with full property definitions and examples.

---

## 📝 STEP 3: UPDATE ALL ROUTERS

For **EVERY endpoint** in **EVERY router** (`auth`, `users`, `roles`, `permissions`, `plans`, `notifications`), add:

### **Required Documentation for Each Endpoint:**

```python
@router.post(
    "/endpoint-path",
    status_code=status.HTTP_201_CREATED,
    summary="Short, clear summary (5-10 words)",
    description="""
    Detailed multi-paragraph description explaining:
    
    **What it does:**
    - Main functionality
    - Business logic
    - Side effects
    
    **Workflow:**
    1. Step-by-step process
    2. What happens internally
    3. What gets returned
    
    **Requirements:**
    - Authentication needed?
    - Permissions required?
    - Special conditions?
    
    **Notes:**
    - Any important information
    - Rate limiting
    - Caching behavior
    """,
    response_description="Brief description of successful response",
    responses={
        201: {
            "description": "Success case description",
            "content": {
                "application/json": {
                    "example": {
                        "status_code": 201,
                        "message": "Success message",
                        "data": { /* realistic example data */ },
                        "error": None
                    }
                }
            }
        },
        400: {
            "description": "Bad request case",
            "content": {
                "application/json": {
                    "example": {
                        "status_code": 400,
                        "message": "Error message",
                        "data": None,
                        "error": {
                            "code": "ERROR_CODE",
                            "message": "Detailed error"
                        }
                    }
                }
            }
        },
        401: { /* Unauthorized example */ },
        403: { /* Forbidden example */ },
        404: { /* Not found example */ },
        422: { /* Validation error example */ }
    }
)
async def endpoint_function():
    """
    Concise docstring for the function.
    
    Args:
        param: Description
        
    Returns:
        ResponseModel: Description
        
    Raises:
        HTTPException: When and why
    """
    pass
```

### **Endpoints to Document:**

**Auth Module:**
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- GET /api/v1/auth/verify-email
- POST /api/v1/auth/forgot-password
- POST /api/v1/auth/reset-password

**Users Module:**
- GET /api/v1/users/me
- PUT /api/v1/users/me
- DELETE /api/v1/users/me
- POST /api/v1/users/me/avatar
- DELETE /api/v1/users/me/avatar
- GET /api/v1/users (admin)
- GET /api/v1/users/{user_id} (admin)
- PUT /api/v1/users/{user_id} (admin)
- DELETE /api/v1/users/{user_id} (admin)

**Roles Module:**
- GET /api/v1/roles
- GET /api/v1/roles/{role_id}
- POST /api/v1/roles (superadmin)
- PUT /api/v1/roles/{role_id} (superadmin)
- DELETE /api/v1/roles/{role_id} (superadmin)
- POST /api/v1/roles/{role_id}/permissions
- DELETE /api/v1/roles/{role_id}/permissions/{permission_id}

**Permissions Module:**
- GET /api/v1/permissions
- GET /api/v1/permissions/{permission_id}
- POST /api/v1/permissions (superadmin)
- PUT /api/v1/permissions/{permission_id} (superadmin)
- DELETE /api/v1/permissions/{permission_id} (superadmin)

**Plans Module:**
- GET /api/v1/plans
- GET /api/v1/plans/{plan_id}
- POST /api/v1/plans (admin)
- PUT /api/v1/plans/{plan_id} (admin)
- DELETE /api/v1/plans/{plan_id} (admin)

**Notifications Module:**
- GET /api/v1/notifications
- PUT /api/v1/notifications/{notification_id}/view
- DELETE /api/v1/notifications/{notification_id}

---

## 📋 STEP 4: UPDATE ALL SCHEMAS

For **EVERY Pydantic model** in **EVERY schema file**, add detailed Field() descriptions and examples:

### **Required Documentation for Each Field:**

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class ExampleSchema(BaseModel):
    """
    Brief schema description.
    
    Longer explanation of what this schema represents and when it's used.
    """
    
    field_name: str = Field(
        ...,  # or default value
        description="Clear description of this field",
        example="realistic example value",
        min_length=1,  # validators if applicable
        max_length=100
    )
    
    email: EmailStr = Field(
        ...,
        description="Valid email address (must be unique)",
        example="user@example.com"
    )
    
    optional_field: Optional[int] = Field(
        None,
        description="Optional field description",
        example=42,
        ge=0,  # greater than or equal to 0
        le=100
    )
    
    nested_object: dict = Field(
        ...,
        description="Nested object description",
        example={
            "key1": "value1",
            "key2": 123
        }
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "field_name": "example value",
                "email": "user@example.com",
                "optional_field": 42,
                "nested_object": {
                    "key1": "value1",
                    "key2": 123
                }
            }
        }
```

### **Schemas to Document:**

**Auth Schemas:**
- UserRegister
- UserLogin
- TokenResponse
- PasswordResetRequest
- PasswordReset
- VerifyEmailRequest

**User Schemas:**
- UserCreate
- UserUpdate
- UserResponse
- UserList
- AvatarUpload

**Role Schemas:**
- RoleCreate
- RoleUpdate
- RoleResponse
- RoleList

**Permission Schemas:**
- PermissionCreate
- PermissionUpdate
- PermissionResponse
- PermissionList

**Plan Schemas:**
- PlanCreate
- PlanUpdate
- PlanResponse
- PlanList

**Notification Schemas:**
- NotificationResponse
- NotificationList
- NotificationUpdate

---

## ✅ STEP 5: VERIFY IMPLEMENTATION

After implementing everything:

1. **Run tests:**
   ```bash
   pytest tests/test_documentation.py -v
   ```
   All tests must pass!

2. **Start the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Manually verify:**
   - Visit `http://localhost:8000/api/docs` - Swagger UI should load with all endpoints
   - Visit `http://localhost:8000/api/redoc` - ReDoc should load with beautiful documentation
   - Visit `http://localhost:8000/api/openapi.json` - Should return valid OpenAPI schema JSON
   - Check that all endpoints are organized by tags
   - Check that all endpoints have detailed descriptions
   - Check that example requests/responses are realistic
   - Check that authentication is clearly documented

---

## 🎨 QUALITY STANDARDS

### **Documentation Quality Checklist:**

- [ ] Every endpoint has a clear, concise summary
- [ ] Every endpoint has a detailed, multi-paragraph description
- [ ] Every endpoint documents its workflow step-by-step
- [ ] Every endpoint has realistic request/response examples
- [ ] Every endpoint documents all possible error cases (400, 401, 403, 404, 422)
- [ ] Every Pydantic field has a description
- [ ] Every Pydantic field has a realistic example
- [ ] All tags have detailed descriptions
- [ ] Security requirements are clearly documented
- [ ] Rate limiting is documented
- [ ] Pagination is documented
- [ ] Response format is consistent and documented
- [ ] All tests pass
- [ ] Swagger UI renders correctly
- [ ] ReDoc renders correctly

---

## 🚀 FINAL DELIVERABLES

When you're done, you should have:

1. ✅ **test_documentation.py** - Comprehensive tests (all passing)
2. ✅ **Updated main.py** - Custom OpenAPI configuration
3. ✅ **Updated all routers** - Detailed endpoint documentation
4. ✅ **Updated all schemas** - Field descriptions and examples
5. ✅ **Working Swagger UI** at /api/docs
6. ✅ **Working ReDoc** at /api/redoc
7. ✅ **Valid OpenAPI schema** at /api/openapi.json

---

## 💡 IMPLEMENTATION TIPS

1. **Start with tests** - Write all test cases first, then make them pass
2. **Use realistic examples** - Don't use "string", "123", use actual data
3. **Be consistent** - Use the same format for all endpoints
4. **Think like a user** - Document what a developer needs to know
5. **Use markdown** - Make descriptions readable with formatting
6. **Test as you go** - Run tests frequently to catch issues early

---

## ⚠️ COMMON MISTAKES TO AVOID

- ❌ DON'T skip tests
- ❌ DON'T use generic descriptions like "Get data" or "Create item"
- ❌ DON'T forget error response examples
- ❌ DON'T use unrealistic examples like "string" or "user@email.com"
- ❌ DON'T forget to document authentication requirements
- ❌ DON'T skip docstrings in function bodies
- ❌ DON'T forget validators in Field() definitions

---

**NOW, BEGIN IMPLEMENTATION! Start with tests, then make them pass. Good luck! 🚀**