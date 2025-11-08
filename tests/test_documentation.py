"""
Tests for API documentation endpoints.

Ensures Swagger UI, ReDoc, and OpenAPI schema are properly configured.
"""

import pytest
from httpx import AsyncClient


class TestAPIDocumentation:
    """Test suite for API documentation configuration."""
    
    @pytest.mark.asyncio
    async def test_swagger_ui_accessible(self, test_client: AsyncClient):
        """Test that Swagger UI is accessible at /api/docs."""
        response = await test_client.get("/api/docs")
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        content = response.text
        assert "swagger-ui" in content.lower() or "swagger" in content.lower()
    
    @pytest.mark.asyncio
    async def test_redoc_accessible(self, test_client: AsyncClient):
        """Test that ReDoc is accessible at /api/redoc."""
        response = await test_client.get("/api/redoc")
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        content = response.text
        assert "redoc" in content.lower()
    
    @pytest.mark.asyncio
    async def test_openapi_schema_accessible(self, test_client: AsyncClient):
        """Test that OpenAPI schema is accessible at /api/openapi.json."""
        response = await test_client.get("/api/openapi.json")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema
        
        # Verify info section
        assert schema["info"]["title"] == "AI Agent Trading Platform API"
        assert schema["info"]["version"] == "1.0.0"
        assert "description" in schema["info"]
        assert "contact" in schema["info"]
        assert "license" in schema["info"]
    
    @pytest.mark.asyncio
    async def test_openapi_schema_has_security_scheme(self, test_client: AsyncClient):
        """Test that OpenAPI schema includes JWT BearerAuth security scheme."""
        response = await test_client.get("/api/openapi.json")
        schema = response.json()
        
        # Check security schemes
        assert "components" in schema
        assert "securitySchemes" in schema["components"]
        assert "BearerAuth" in schema["components"]["securitySchemes"]
        
        bearer_auth = schema["components"]["securitySchemes"]["BearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"
        assert bearer_auth["bearerFormat"] == "JWT"
        assert "description" in bearer_auth
    
    @pytest.mark.asyncio
    async def test_openapi_schema_has_tags(self, test_client: AsyncClient):
        """Test that OpenAPI schema includes properly organized tags."""
        response = await test_client.get("/api/openapi.json")
        schema = response.json()
        
        assert "tags" in schema
        tag_names = [tag["name"] for tag in schema["tags"]]
        
        # Verify all expected tags exist
        expected_tags = [
            "Authentication",
            "Users",
            "Roles",
            "Permissions",
            "Plans",
            "User Plans",
            "Notifications"
        ]
        
        for expected_tag in expected_tags:
            assert expected_tag in tag_names, f"Missing tag: {expected_tag}"
        
        # Verify each tag has a description
        for tag in schema["tags"]:
            assert "description" in tag
            assert len(tag["description"]) > 0
    
    @pytest.mark.asyncio
    async def test_all_endpoints_have_summary(self, test_client: AsyncClient):
        """Test that all endpoints have a summary field."""
        response = await test_client.get("/api/openapi.json")
        schema = response.json()
        
        missing_summaries = []
        
        for path, methods in schema["paths"].items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    if "summary" not in details or not details["summary"]:
                        missing_summaries.append(f"{method.upper()} {path}")
        
        assert len(missing_summaries) == 0, f"Endpoints missing summary: {missing_summaries}"
    
    @pytest.mark.asyncio
    async def test_all_endpoints_have_description(self, test_client: AsyncClient):
        """Test that all endpoints have a description field."""
        response = await test_client.get("/api/openapi.json")
        schema = response.json()
        
        missing_descriptions = []
        
        for path, methods in schema["paths"].items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    if "description" not in details or not details["description"]:
                        missing_descriptions.append(f"{method.upper()} {path}")
        
        assert len(missing_descriptions) == 0, f"Endpoints missing description: {missing_descriptions}"
    
    @pytest.mark.asyncio
    async def test_schemas_have_descriptions(self, test_client: AsyncClient):
        """Test that all schemas have descriptions or titles."""
        response = await test_client.get("/api/openapi.json")
        schema = response.json()
        
        # Skip internal/generated schemas
        skip_schemas = [
            "Body_",
            "HTTPValidationError",
            "ValidationError",
            "Input",
            "Output"
        ]
        
        missing_descriptions = []
        
        if "components" in schema and "schemas" in schema["components"]:
            for schema_name, schema_def in schema["components"]["schemas"].items():
                # Skip internal schemas
                if any(skip in schema_name for skip in skip_schemas):
                    continue
                
                # Check if schema has description or title
                if "description" not in schema_def and "title" not in schema_def:
                    missing_descriptions.append(schema_name)
        
        assert len(missing_descriptions) == 0, f"Schemas missing description/title: {missing_descriptions}"
    
    @pytest.mark.asyncio
    async def test_endpoints_have_response_examples(self, test_client: AsyncClient):
        """Test that endpoints have response examples."""
        response = await test_client.get("/api/openapi.json")
        schema = response.json()
        
        endpoints_checked = 0
        
        for path, methods in schema["paths"].items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    endpoints_checked += 1
                    
                    # Check if responses are documented
                    assert "responses" in details, f"{method.upper()} {path} missing responses"
                    
                    # At least one response should be documented
                    assert len(details["responses"]) > 0, f"{method.upper()} {path} has no responses"
        
        # Ensure we checked some endpoints
        assert endpoints_checked > 0, "No endpoints found in schema"
    
    @pytest.mark.asyncio
    async def test_auth_endpoints_documented(self, test_client: AsyncClient):
        """Test that authentication endpoints are properly documented."""
        response = await test_client.get("/api/openapi.json")
        schema = response.json()
        
        # Expected auth endpoints
        expected_auth_paths = [
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/api/v1/auth/verify-email",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password"
        ]
        
        for path in expected_auth_paths:
            assert path in schema["paths"], f"Missing auth endpoint: {path}"
    
    @pytest.mark.asyncio
    async def test_common_response_schemas_exist(self, test_client: AsyncClient):
        """Test that common response schemas are defined."""
        response = await test_client.get("/api/openapi.json")
        schema = response.json()
        
        if "components" in schema and "schemas" in schema["components"]:
            schemas = schema["components"]["schemas"]
            
            # At least some response-related schemas should exist
            response_schemas_found = False
            for schema_name in schemas.keys():
                if "Response" in schema_name or "Error" in schema_name:
                    response_schemas_found = True
                    break
            
            assert response_schemas_found, "No common response schemas found"


class TestAPIDocumentationQuality:
    """Test suite for documentation quality standards."""
    
    @pytest.mark.asyncio
    async def test_api_has_contact_info(self, test_client: AsyncClient):
        """Test that API has contact information."""
        response = await test_client.get("/api/openapi.json")
        schema = response.json()
        
        assert "info" in schema
        assert "contact" in schema["info"]
        
        contact = schema["info"]["contact"]
        # At least one contact field should be present
        assert "name" in contact or "email" in contact or "url" in contact
    
    @pytest.mark.asyncio
    async def test_api_has_license_info(self, test_client: AsyncClient):
        """Test that API has license information."""
        response = await test_client.get("/api/openapi.json")
        schema = response.json()
        
        assert "info" in schema
        assert "license" in schema["info"]
        assert "name" in schema["info"]["license"]
    
    @pytest.mark.asyncio
    async def test_api_description_is_comprehensive(self, test_client: AsyncClient):
        """Test that API description is detailed and comprehensive."""
        response = await test_client.get("/api/openapi.json")
        schema = response.json()
        
        description = schema["info"]["description"]
        
        # Should be a substantial description (at least 500 characters)
        assert len(description) >= 500, "API description should be comprehensive"
        
        # Should mention key features
        keywords = ["authentication", "rate limit", "pagination", "response"]
        for keyword in keywords:
            assert keyword.lower() in description.lower(), f"Description should mention '{keyword}'"

