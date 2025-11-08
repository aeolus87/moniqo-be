#!/bin/bash
# Run a single test to verify setup

source venv/bin/activate
python -m pytest tests/test_auth.py::TestRegistration::test_register_with_valid_data_returns_201 -v --tb=short

