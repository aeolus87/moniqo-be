# Workspace Rules Comparison

This document shows the differences between the original workspace rules and the updated rules based on `project.md`.

---

## Overview of Changes

| Category | Original Status | Updated Status | Change Type |
|----------|----------------|----------------|-------------|
| TDD Workflow | Generic mention | Mandatory with specific patterns | **NEW** |
| Background Tasks | Not specified | FastAPI BackgroundTasks required | **NEW** |
| MongoDB Patterns | Generic | Motor async with soft delete | **NEW** |
| API Responses | Not standardized | Mandatory format specified | **NEW** |
| RBAC | Generic security | Full RBAC implementation | **NEW** |
| Rate Limiting | Not specified | 100/min users, unlimited admins | **NEW** |
| Caching | Not specified | Redis with 1-day TTL | **NEW** |
| Pagination | Not specified | limit/offset with specific format | **NEW** |
| Module Structure | Generic | Feature-based with file patterns | **ENHANCED** |
| Code Quality | Present | Enhanced with examples | **ENHANCED** |
| Environment Vars | Comprehensive | Kept as-is | **KEEP** |
| Documentation | Present | Enhanced with TDD reference | **ENHANCED** |
| Scaffold Dev | Present | Enhanced with init scripts | **ENHANCED** |

---

## Detailed Comparison

### 1. Test-Driven Development

#### Before (Original)
```
Testing guidelines mentioned generically in testing rule.
No specific TDD workflow enforcement.
```

#### After (Updated)
```
MANDATORY TDD workflow:
1. Write tests FIRST (positive, negative, edge cases)
2. Then implement feature
3. Run tests continuously

Specific patterns for pytest-asyncio with FastAPI.
Test fixtures and naming conventions defined.
```

#### Why Changed
`project.md` makes TDD absolutely mandatory with specific workflow steps. This is critical for code quality and must be enforced in workspace rules.

---

### 2. Background Tasks

#### Before (Original)
```
No guidance on background task implementation.
```

#### After (Updated)
```
Use FastAPI's built-in BackgroundTasks (not Celery/ARQ).

Pattern:
@router.post("/register")
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks
):
    user = await create_user(user_data)
    background_tasks.add_task(send_welcome_email, user.email)
    return {"message": "Success"}
```

#### Why Changed
`project.md` explicitly specifies using FastAPI BackgroundTasks for simplicity. This is a deliberate architectural decision that must be reflected in rules.

---

### 3. MongoDB/Motor Patterns

#### Before (Original)
```
Generic database mentions.
No specific patterns or ODM specified.
```

#### After (Updated)
```
- Database: MongoDB
- Driver: Motor (async)
- Soft Delete: MANDATORY is_deleted flag on all collections
- References: Use ObjectId references (normalized)

Specific patterns for async queries with soft delete checks.
```

#### Why Changed
`project.md` defines MongoDB as the database with specific patterns. Soft delete is used throughout the system and must be enforced.

---

### 4. API Response Standardization

#### Before (Original)
```
No standardized response format specified.
```

#### After (Updated)
```
MANDATORY response format for ALL endpoints:
{
    "status_code": int,
    "message": str,
    "data": Any | None,
    "error": {...} | None
}

Both success and error examples provided.
```

#### Why Changed
`project.md` mandates a specific response format for consistency across all API endpoints. This is non-negotiable for API consumers.

---

### 5. RBAC Implementation

#### Before (Original)
```
Generic security best practices mentioned.
No specific authorization pattern.
```

#### After (Updated)
```
Full RBAC system:
- Users → Roles → Permissions
- Permissions format: {resource}:{action}
- Permission dependency: require_permission(resource, action)

Specific collection structures and implementation patterns.
```

#### Why Changed
`project.md` defines a complete RBAC system as core feature. Authorization patterns must be standardized across all protected endpoints.

---

### 6. Rate Limiting

#### Before (Original)
```
Not specified in workspace rules.
```

#### After (Updated)
```
- Regular users: 100 requests/minute
- Admins: Unlimited (if ADMIN_RATE_LIMIT_ENABLED=False)
- Implementation: Redis-based
- Key format: rate_limit:{user_id}:{minute}
- Return: 429 Too Many Requests
```

#### Why Changed
`project.md` specifies exact rate limiting rules. This prevents API abuse and must be implemented consistently.

---

### 7. Caching Strategy

#### Before (Original)
```
Not specified in workspace rules.
```

#### After (Updated)
```
- Cache: Redis
- TTL: 1 day max (configurable)
- Key format: {module}:{operation}:{params_hash}
- Invalidation: On CREATE/UPDATE/DELETE
- Target: GET requests for list/detail endpoints

Utility functions defined.
```

#### Why Changed
`project.md` defines specific caching strategy for performance. Cache invalidation rules are critical for data consistency.

---

### 8. Pagination Standards

#### Before (Original)
```
Not specified in workspace rules.
```

#### After (Updated)
```
Request: ?limit=10&offset=0
Response: {items, total, limit, offset, has_more}

Default from env: DEFAULT_PAGE_SIZE
Max from env: MAX_PAGE_SIZE
```

#### Why Changed
`project.md` standardizes pagination across all list endpoints. Consistent pagination improves API usability.

---

### 9. Module Organization

#### Before (Original)
```
Generic folder structure mentioned.
Feature-based structure noted.
```

#### After (Updated)
```
Specific file patterns for each module:
- models.py: Database models
- schemas.py: Pydantic DTOs
- service.py: Business logic
- router.py: API endpoints
- dependencies.py: Module-specific dependencies

Phase 1 vs Phase 2 modules defined.
```

#### Why Changed
`project.md` provides exact module organization pattern. Consistency in file structure improves navigation and maintainability.

---

### 10. Initialization Scripts

#### Before (Original)
```
Not mentioned in workspace rules.
```

#### After (Updated)
```
MANDATORY startup scripts:
- init_superadmin.py: Create superadmin on startup
- init_default_data.py: Create default roles/permissions/plans

Integration in main.py @app.on_event("startup")
```

#### Why Changed
`project.md` requires initialization scripts for first-time setup. This ensures the system has required data on startup.

---

## What Stayed the Same

### Environment Variables Policy ✅
The existing comprehensive policy remains unchanged. It already matches `project.md` requirements:
- No hardcoded values
- .env.example (commit) vs .env (never commit)
- ALL configuration from environment

### Documentation Standards ✅
Google-style docstrings and comprehensive documentation requirements remain. Enhanced with TDD references.

### Project Structure Overview ✅
Moniqo_BE (active) vs Moniqo_BE_FORK (reference) remains as defined.

### Scaffold Development Approach ✅
Core concept remains, enhanced with specific requirements from `project.md`.

---

## Impact Analysis

### High Impact Changes (Require Immediate Action)
1. **TDD Workflow**: Changes development process fundamentally
2. **API Response Format**: Affects all existing and future endpoints
3. **Soft Delete Pattern**: Affects all database operations

### Medium Impact Changes (Require Planning)
1. **Background Tasks Pattern**: Affects async operations
2. **RBAC Implementation**: Affects all protected endpoints
3. **Module Organization**: Affects new feature development

### Low Impact Changes (Gradual Implementation)
1. **Rate Limiting**: Can be added progressively
2. **Caching Strategy**: Can be optimized over time
3. **Pagination**: Can be standardized incrementally

---

## Migration Strategy

### Immediate (Sprint 1)
- [ ] Update workspace rules configuration
- [ ] Apply TDD workflow to new features
- [ ] Implement standardized API responses for new endpoints

### Short Term (Sprint 2-3)
- [ ] Create init scripts (superadmin, default data)
- [ ] Implement RBAC system
- [ ] Add soft delete to all collections

### Medium Term (Sprint 4-6)
- [ ] Refactor existing endpoints to use standard response format
- [ ] Implement caching strategy
- [ ] Add rate limiting middleware

### Long Term (Ongoing)
- [ ] Maintain test coverage above 80%
- [ ] Regular review of rules alignment with project.md
- [ ] Update documentation as patterns evolve

---

## Verification Checklist

Use this checklist to verify rules are being followed:

### Code Review Checklist
- [ ] Tests written before implementation (TDD)
- [ ] Standardized API response format used
- [ ] Soft delete implemented (not hard delete)
- [ ] Type hints on all functions
- [ ] Google-style docstrings present
- [ ] No hardcoded values (env vars used)
- [ ] Background tasks use FastAPI BackgroundTasks
- [ ] Permission checks on protected routes
- [ ] Async patterns used correctly (Motor)

### Architecture Review Checklist
- [ ] Module follows models/schemas/service/router pattern
- [ ] Initialization scripts exist and work
- [ ] RBAC properly implemented
- [ ] Caching strategy applied where appropriate
- [ ] Rate limiting configured
- [ ] Pagination standardized

---

## Questions & Answers

### Q: Why switch from Celery to FastAPI BackgroundTasks?
**A:** For this project's needs, FastAPI BackgroundTasks is simpler and sufficient. It handles email sending and notifications without complex queue infrastructure. Can upgrade to Celery later if needed for scheduling or distributed processing.

### Q: Why mandatory soft deletes?
**A:** Soft deletes enable audit trails, data recovery, and comply with data retention policies. They're critical for production systems handling user data.

### Q: Why standardized API responses?
**A:** Consistency makes API easier to consume. Clients can handle responses uniformly without checking different formats per endpoint.

### Q: Why TDD mandatory?
**A:** TDD ensures code quality, documents expected behavior, and prevents regressions. Critical for a scaffold project being built from ground up.

### Q: Can we deviate from these rules?
**A:** Only with documented architectural decision record (ADR) and team consensus. `project.md` is the source of truth unless explicitly changed.

---

**Summary:** The updated rules are significantly more comprehensive and specific, providing concrete patterns that directly implement the architecture defined in `project.md`.


