import os
import tempfile

# Tests must never append to the repository's signal history (checklist 2.1).
_HISTORY_DIR = tempfile.mkdtemp(prefix="chainstox-history-tests-")
os.environ["CHAINSTOX_HISTORY_DIR"] = _HISTORY_DIR
# Tests must never fetch live chart history to fill market inputs (solution plan C1); tests that
# exercise market_inputs inject a fake fetch, which bypasses this switch.
os.environ["CHAINSTOX_DERIVE_MARKET_INPUTS"] = "0"
