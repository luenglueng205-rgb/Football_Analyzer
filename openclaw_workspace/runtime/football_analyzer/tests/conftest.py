import os
import sys


standalone_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if standalone_root not in sys.path:
    sys.path.insert(0, standalone_root)
