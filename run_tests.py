"""
Test runner script.

Run tests and display results.
"""

import sys
import subprocess

def run_tests():
    """Run pytest with appropriate arguments."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ]
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)

