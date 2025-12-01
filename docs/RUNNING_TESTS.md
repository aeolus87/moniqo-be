# Running Tests

**Author:** Moniqo Team  
**Last Updated:** 2025-11-22

## Quick Start

### Prerequisites

Make sure you have the virtual environment activated:

```bash
cd Moniqo_BE
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Running All Tests

### Run All Phase 2D Tests

```bash
# Run all Phase 2D tests (AI integrations + AI agents)
pytest tests/integrations/ai/ tests/modules/ai_agents/ -v

# With coverage report
pytest tests/integrations/ai/ tests/modules/ai_agents/ -v --cov=app/integrations/ai --cov=app/modules/ai_agents --cov-report=html
```

### Run All Tests in Project

```bash
# Run all tests
pytest -v

# Run all tests with coverage
pytest -v --cov=app --cov-report=html

# Run all tests with detailed output
pytest -v --tb=short

# Run all tests and stop on first failure
pytest -v -x
```

## Running Specific Test Suites

### Phase 2A Tests (Wallet Abstraction)

```bash
pytest tests/integrations/wallets/ tests/modules/user_wallets/ -v
```

### Phase 2B Tests (Exchanges & Market Data)

```bash
pytest tests/integrations/exchanges/ tests/integrations/market_data/ tests/services/ -v
```

### Phase 2C Tests (Orders & Positions)

```bash
pytest tests/modules/orders/ tests/modules/positions/ -v
```

### Phase 2D Tests (AI Models & Agents)

```bash
# All Phase 2D tests
pytest tests/integrations/ai/ tests/modules/ai_agents/ -v

# AI integrations only
pytest tests/integrations/ai/ -v

# AI agents only
pytest tests/modules/ai_agents/ -v
```

### Specific Test Files

```bash
# BaseLLM tests
pytest tests/integrations/ai/test_base_llm.py -v

# GeminiModel tests
pytest tests/integrations/ai/test_gemini_model.py -v

# GroqModel tests
pytest tests/integrations/ai/test_groq_model.py -v

# ModelFactory tests
pytest tests/integrations/ai/test_model_factory.py -v

# BaseAgent tests
pytest tests/modules/ai_agents/test_base_agent.py -v

# MarketAnalystAgent tests
pytest tests/modules/ai_agents/test_market_analyst.py -v

# RiskManagerAgent tests
pytest tests/modules/ai_agents/test_risk_manager.py -v

# ExecutorAgent tests
pytest tests/modules/ai_agents/test_executor_agent.py -v

# MonitorAgent tests
pytest tests/modules/ai_agents/test_monitor_agent.py -v
```

## Running Single Tests

### Run a Specific Test Function

```bash
# Run specific test
pytest tests/modules/ai_agents/test_executor_agent.py::test_executor_agent_init -v

# Run multiple specific tests
pytest tests/modules/ai_agents/test_executor_agent.py::test_executor_agent_init tests/modules/ai_agents/test_monitor_agent.py::test_monitor_agent_init -v
```

## Test Output Options

### Verbose Output

```bash
pytest -v  # Verbose mode
pytest -vv  # More verbose
```

### Short Traceback

```bash
pytest --tb=short  # Short traceback
pytest --tb=line   # One line per failure
pytest --tb=no     # No traceback
```

### Show Print Statements

```bash
pytest -s  # Show print statements
```

### Stop on First Failure

```bash
pytest -x  # Stop on first failure
pytest --maxfail=3  # Stop after 3 failures
```

## Coverage Reports

### Generate Coverage Report

```bash
# Terminal report
pytest --cov=app --cov-report=term

# HTML report
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml
```

### Coverage for Specific Modules

```bash
# Phase 2D only
pytest tests/integrations/ai/ tests/modules/ai_agents/ --cov=app/integrations/ai --cov=app/modules/ai_agents --cov-report=html

# All Phase 2 tests
pytest tests/integrations/ tests/modules/ --cov=app/integrations --cov=app/modules --cov-report=html
```

## Parallel Test Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest -n 4

# Auto-detect number of CPUs
pytest -n auto
```

## Markers and Filtering

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Run Tests by Name Pattern

```bash
# Run all tests matching "test_executor"
pytest -k executor

# Run all tests matching "test_agent"
pytest -k agent
```

## Common Issues

### Missing Dependencies

If you get import errors:

```bash
# Install all dependencies
pip install -r requirements.txt

# Install AI dependencies specifically
pip install google-generativeai groq
```

### Virtual Environment Not Activated

```bash
# Activate virtual environment
source venv/bin/activate

# Verify activation (should show (venv) in prompt)
which python
```

### Test Collection Issues

```bash
# Check if tests are discovered
pytest --collect-only

# Check specific file
pytest tests/modules/ai_agents/test_executor_agent.py --collect-only
```

## Recommended Test Commands

### Daily Development

```bash
# Run all Phase 2D tests quickly
pytest tests/integrations/ai/ tests/modules/ai_agents/ -v -x

# Run with coverage
pytest tests/integrations/ai/ tests/modules/ai_agents/ -v --cov=app/integrations/ai --cov=app/modules/ai_agents
```

### Before Committing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=app --cov-report=term-missing
```

### CI/CD Pipeline

```bash
# Run all tests with XML coverage
pytest -v --cov=app --cov-report=xml --cov-report=term --junitxml=results.xml
```

## Test Statistics

### Phase 2D Test Count

- **BaseLLM:** 7 tests
- **GeminiModel:** 16 tests
- **GroqModel:** 11 tests
- **ModelFactory:** 10 tests
- **BaseAgent:** 14 tests
- **MarketAnalystAgent:** 9 tests
- **RiskManagerAgent:** 10 tests
- **ExecutorAgent:** 10 tests
- **MonitorAgent:** 13 tests
- **Total:** 100 tests

## Quick Reference

```bash
# Most common command
pytest -v

# Run specific test file
pytest tests/modules/ai_agents/test_executor_agent.py -v

# Run all Phase 2D tests
pytest tests/integrations/ai/ tests/modules/ai_agents/ -v

# Run with coverage
pytest -v --cov=app --cov-report=html
```

---

**Author:** Moniqo Team  
**Last Updated:** 2025-11-22


