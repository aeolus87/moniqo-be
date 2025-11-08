"""Check if all modules can be imported."""

import sys

def check_imports():
    """Check if key modules can be imported."""
    errors = []
    
    try:
        from app.config import settings
        print("✓ app.config.settings")
    except Exception as e:
        errors.append(f"✗ app.config.settings: {e}")
    
    try:
        from app.config import database
        print("✓ app.config.database")
    except Exception as e:
        errors.append(f"✗ app.config.database: {e}")
    
    try:
        from app.core import security
        print("✓ app.core.security")
    except Exception as e:
        errors.append(f"✗ app.core.security: {e}")
    
    try:
        from app.core import dependencies
        print("✓ app.core.dependencies")
    except Exception as e:
        errors.append(f"✗ app.core.dependencies: {e}")
    
    try:
        from app.modules.auth import router
        print("✓ app.modules.auth.router")
    except Exception as e:
        errors.append(f"✗ app.modules.auth.router: {e}")
    
    try:
        from app.modules.users import router
        print("✓ app.modules.users.router")
    except Exception as e:
        errors.append(f"✗ app.modules.users.router: {e}")
    
    try:
        from app.main import app
        print("✓ app.main")
    except Exception as e:
        errors.append(f"✗ app.main: {e}")
    
    if errors:
        print("\n❌ Import Errors:")
        for error in errors:
            print(error)
        return 1
    else:
        print("\n✅ All imports successful!")
        return 0

if __name__ == "__main__":
    sys.exit(check_imports())

