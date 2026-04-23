import os
import subprocess
from datetime import datetime


def main() -> int:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    gatekeeper = os.path.join(repo_root, "standalone_workspace/scripts/qa_deployment_gatekeeper.py")
    report_dir = os.path.join(repo_root, "standalone_workspace/tests/qa_reports")
    os.makedirs(report_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(report_dir, f"gatekeeper_run_{ts}.log")

    result = subprocess.run(
        ["python3", gatekeeper],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    with open(log_path, "w", encoding="utf-8") as f:
        if result.stdout:
            f.write(result.stdout)
        if result.stderr:
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)

    print(log_path)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
