"""Reset the working database to a fresh copy of the original.

Overwrites data/campus_customs_new.db with a copy of data/campus_customs.db.
Run this before each full run so agents always start from a clean state.
The original campus_customs.db is never modified.
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
WORKING_DB = ROOT / "data" / "campus_customs_new.db"


def reset_db() -> None:
    if not ORIGINAL_DB.exists():
        raise FileNotFoundError(f"Original database not found: {ORIGINAL_DB}")
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    print(f"Reset {WORKING_DB} from {ORIGINAL_DB}")


if __name__ == "__main__":
    reset_db()
