import sys
import os
import pytest
import json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from qa_engine.coverage_matrix import get_global_tracker

def run_gatekeeper():
    print("\n" + "="*70)
    print("🛡️  STARTING SELF-PROVING QA ENGINE GATEKEEPER 🛡️")
    print("="*70)
    
    # 1. Run all QA Matrix tests to populate the tracker
    print("\n[1/3] Running Strategy & Official Rulebook Test Suite...")
    test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tests/qa_matrix_tests'))
    
    # Run pytest programmatically
    exit_code = pytest.main([test_dir, "-q", "--disable-warnings"])
    
    if exit_code != 0:
        print("\n❌ GATEKEEPER BLOCKED: Tests failed. Code violates Strategy or Official Rulebooks.")
        sys.exit(1)
        
    # 2. Check the 16x6 Coverage Matrix
    print("\n[2/3] Analyzing 16x6 Play Type Lifecycle Coverage Matrix...")
    tracker = get_global_tracker()
    report = tracker.get_coverage_report()
    
    print(f"Coverage: {report['coverage_percentage']}% ({report['covered_nodes']}/{report['total_nodes']} nodes)")
    
    # 3. Generate Report
    print("\n[3/3] Generating Deployment Report...")
    report_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tests/qa_reports'))
    os.makedirs(report_dir, exist_ok=True)
    
    report_path = os.path.join(report_dir, f"qa_matrix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"Report saved to: {report_path}")
    
    if not report["is_complete"]:
        print("\n❌ GATEKEEPER BLOCKED: Coverage < 100%. The following nodes are missing implementation/tests:")
        for missing in report["missing_nodes"]:
            print(f"  - {missing}")
        print("\nYou MUST implement and test these blind spots before deployment is allowed.")
        sys.exit(1)
        
    print("\n✅ GATEKEEPER PASSED: 100% Coverage & Rulebook Alignment Verified. Deployment Allowed.")
    sys.exit(0)

if __name__ == "__main__":
    run_gatekeeper()