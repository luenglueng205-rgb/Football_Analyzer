import os
import sys


runtime_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if runtime_root not in sys.path:
    sys.path.insert(0, runtime_root)
