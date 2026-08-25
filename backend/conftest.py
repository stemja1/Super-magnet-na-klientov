"""Make the ``app`` package importable for pytest run from the backend dir."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
