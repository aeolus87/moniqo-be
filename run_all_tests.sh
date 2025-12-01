#!/bin/bash
# Run all tests script

cd "$(dirname "$0")"
source venv/bin/activate

echo "=========================================="
echo "Running All Phase 2D Tests"
echo "=========================================="
pytest tests/integrations/ai/ tests/modules/ai_agents/ -v --tb=short

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
