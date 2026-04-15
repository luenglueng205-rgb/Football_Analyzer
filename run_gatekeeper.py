import subprocess
import sys

try:
    result = subprocess.run(["python3", "standalone_workspace/scripts/qa_deployment_gatekeeper.py"], capture_output=True, text=True, check=True)
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print(e.stdout)
    print(e.stderr)
