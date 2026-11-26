import os
import tempfile

# Tests must never append to the repository's signal history (checklist 2.1).
_HISTORY_DIR = tempfile.mkdtemp(prefix="chainstox-history-tests-")
os.environ["CHAINSTOX_HISTORY_DIR"] = _HISTORY_DIR
# Tests must never fetch live chart history to fill market inputs (solution plan C1); tests that
# exercise market_inputs inject a fake fetch, which bypasses this switch.
os.environ["CHAINSTOX_DERIVE_MARKET_INPUTS"] = "0"
# Tests must never fetch live SEC HTML/XBRL filing documents unless a fetcher is injected (Stage 2).
os.environ["CHAINSTOX_FETCH_SEC_FILINGS"] = "0"
# Tests must never read a developer's real `.env` API key unless explicitly passed.
os.environ["CHAINSTOX_IGNORE_DOTENV"] = "1"
