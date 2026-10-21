"""Canonical CLI entrypoint for the Market Intelligence System.

All menu text and command routing live in the adjacent ``Valuation_model.py``.
This wrapper deliberately contains no duplicate CLI implementation.
"""

import sys

from Valuation_model import run_cli


def main(argv=None):
    """Run the active CLI using explicit arguments or the current process arguments."""
    return run_cli(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
