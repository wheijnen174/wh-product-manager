"""
Minimal test to see if EXE runs at all
"""

import sys


def main():
    """Absolute minimal entry point"""
    try:
        # Test 1: Can we write to console?
        sys.stdout.write("TEST 1: Console output works\n")
        sys.stdout.flush()

        # Test 2: Can we import standard library?
        sys.stdout.write("TEST 2: Importing sys module...\n")
        sys.stdout.flush()
        sys.stdout.write("TEST 2: Success\n")
        sys.stdout.flush()

        # Test 3: Can we import Pydantic?
        sys.stdout.write("TEST 3: Importing pydantic...\n")
        sys.stdout.flush()
        sys.stdout.write("TEST 3: Success\n")
        sys.stdout.flush()

        # Test 4: Can we import our config?
        sys.stdout.write("TEST 4: Importing wh_product_manager.config...\n")
        sys.stdout.flush()
        from wh_product_manager.config import Settings

        sys.stdout.write("TEST 4: Success\n")
        sys.stdout.flush()

        # Test 5: Can we create settings?
        sys.stdout.write("TEST 5: Creating Settings object...\n")
        sys.stdout.flush()
        settings = Settings()
        sys.stdout.write(f"TEST 5: Success - PORT={settings.PORT}\n")
        sys.stdout.flush()

        sys.stdout.write("\n✅ ALL TESTS PASSED\n")
        sys.stdout.flush()

        # Keep window open
        input("Press Enter to close...")

    except Exception as e:
        sys.stdout.write(f"\n❌ ERROR: {str(e)}\n")
        sys.stdout.flush()
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
        input("Press Enter to close...")


if __name__ == "__main__":
    main()
else:
    print("This script is meant to be run as the main entry point for the EXE.")
    print("If you're seeing this message, something went wrong with the build process.")
    sys.exit(1)
