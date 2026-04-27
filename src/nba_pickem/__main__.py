import sys

from . import __version__


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        print(f"nba-pickem {__version__}")
        return

    print(f"nba-pickem {__version__}")
    print("Available commands:")
    print("  nba-pickem-init     Initialize database")
    print("  nba-pickem-train     Train prediction model")
    print("  nba-pickem-predict   Predict today's games")
    print("  nba-pickem-extract   Extract data from sources")
    print("\nOr run: python -m nba_pickem.<script>")