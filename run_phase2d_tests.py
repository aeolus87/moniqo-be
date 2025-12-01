#!/usr/bin/env python3
"""
Quick test runner for Phase 2D tests
"""

import subprocess
import sys

def run_tests():
    """Run Phase 2D tests and show results"""
    test_files = [
        "tests/integrations/ai/test_base_llm.py",
        "tests/integrations/ai/test_gemini_model.py",
        "tests/integrations/ai/test_groq_model.py",
        "tests/integrations/ai/test_model_factory.py",
        "tests/modules/ai_agents/test_base_agent.py",
        "tests/modules/ai_agents/test_market_analyst.py",
        "tests/modules/ai_agents/test_risk_manager.py",
        "tests/modules/ai_agents/test_executor_agent.py",
        "tests/modules/ai_agents/test_monitor_agent.py",
    ]
    
    print("=" * 60)
    print("Running Phase 2D Tests")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_errors = 0
    
    for test_file in test_files:
        print(f"\n{'='*60}")
        print(f"Running: {test_file}")
        print(f"{'='*60}")
        
        result = subprocess.run(
            ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True,
            text=True
        )
        
        # Parse output
        output = result.stdout + result.stderr
        
        # Count results
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        skipped = output.count(" SKIPPED")
        errors = output.count(" ERROR")
        
        total_passed += passed
        total_failed += failed
        total_skipped += skipped
        total_errors += errors
        
        # Print summary
        print(f"  PASSED: {passed}")
        print(f"  FAILED: {failed}")
        print(f"  SKIPPED: {skipped}")
        print(f"  ERROR: {errors}")
        
        if failed > 0 or errors > 0:
            print("\n  Errors/Failures:")
            for line in output.split('\n'):
                if 'FAILED' in line or 'ERROR' in line:
                    print(f"    {line}")
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total PASSED: {total_passed}")
    print(f"Total FAILED: {total_failed}")
    print(f"Total SKIPPED: {total_skipped}")
    print(f"Total ERROR: {total_errors}")
    print(f"Total Tests: {total_passed + total_failed + total_skipped + total_errors}")
    print(f"{'='*60}")
    
    if total_failed > 0 or total_errors > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_tests()


