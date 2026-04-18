import sys
import os
import pytest
import json
import subprocess
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from qa_engine.coverage_matrix import get_global_tracker

CORE_CLOSED_LOOP_TESTS = [
    "test_data_contract.py",
    "test_match_identity.py",
    "test_multisource_normalization.py",
    "test_recommendation_schema.py",
    "test_network_policy_gatekeeper.py",
    "test_mentor_cli.py",
    "test_closed_loop_trade.py",
    "test_physical_isolation.py",
    "test_capability_matrix_smoke.py",
]

def run_gatekeeper():
    print("\n" + "="*70)
    print("🛡️  STARTING SELF-PROVING QA ENGINE GATEKEEPER 🛡️")
    print("="*70)
    
    # 1. Run all QA Matrix tests to populate the tracker
    print("\n[1/4] Running Strategy & Official Rulebook Test Suite...")
    test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tests/qa_matrix_tests'))
    
    # Run pytest programmatically
    exit_code = pytest.main([test_dir, "-q", "--disable-warnings"])
    
    if exit_code != 0:
        print("\n❌ GATEKEEPER BLOCKED: Tests failed. Code violates Strategy or Official Rulebooks.")
        sys.exit(1)
        
    # 2. Check the 16x6 Coverage Matrix
    print("\n[2/4] Analyzing 16x6 Play Type Lifecycle Coverage Matrix...")
    tracker = get_global_tracker()
    report = tracker.get_coverage_report()
    
    print(f"Coverage: {report['coverage_percentage']}% ({report['covered_nodes']}/{report['total_nodes']} nodes)")
    
    # 3. Generate Report
    print("\n[3/4] Generating Deployment Report...")
    report_dir = os.environ.get("QA_GATEKEEPER_REPORT_DIR") or os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../tests/qa_reports")
    )
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

    # 4. Run core closed-loop tests (must not regress)
    print("\n[4/4] Running Core Closed-Loop Test Suite...")
    standalone_tests_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../tests"))
    core_test_paths = [os.path.join(standalone_tests_dir, name) for name in CORE_CLOSED_LOOP_TESTS]
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *core_test_paths, "-q", "--disable-warnings"],
        cwd=repo_root,
    )
    exit_code = int(result.returncode)

    if exit_code != 0:
        print("\n❌ GATEKEEPER BLOCKED: Core closed-loop tests failed.")
        sys.exit(1)
        
    print("\n✅ GATEKEEPER PASSED: 100% Coverage & Rulebook Alignment Verified. Deployment Allowed.")
    sys.exit(0)

if __name__ == "__main__":
    run_gatekeeper()
