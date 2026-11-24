import os
import tempfile

# Tests must never append to the repository's signal history (checklist 2.1).
_HISTORY_DIR = tempfile.mkdtemp(prefix="chainstox-history-tests-")
os.environ["CHAINSTOX_HISTORY_DIR"] = _HISTORY_DIR
