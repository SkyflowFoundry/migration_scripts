import os
import sys
from pathlib import Path


# Ensure project root is importable and use it as CWD for tests
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_sessionstart(session):
    os.chdir(ROOT)

