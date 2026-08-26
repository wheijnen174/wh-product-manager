"""
Nuitka entry point for building the EXE
This is separate from run.py to avoid module loading issues
"""

import sys
import traceback


def main():
    """Main entry point for the built EXE"""
    try:
        print("Starting WH Product Manager...")
        sys.stdout.flush()

        # Import settings first to catch config errors
        print("Loading configuration...")
        from wh_product_manager.settings import Settings

        settings = Settings()
        print("Configuration loaded")
        print(f"  HOST: {settings.HOST}")
        print(f"  PORT: {settings.PORT}")
        sys.stdout.flush()

        # Import and run uvicorn
        print("Starting uvicorn server...")
        import uvicorn

        uvicorn.run(
            "wh_product_manager.main:app",
            host=settings.HOST,
            port=settings.PORT,
            log_level=settings.LOG_LEVEL_CONSOLE.lower(),
            reload=False,  # Don't use reload in EXE
        )

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}")
        print(f"Message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        sys.stdout.flush()

        # Keep console open
        input("\nPress Enter to close...")
        sys.exit(1)


if __name__ == "__main__":
    main()
else:
    print("This script is meant to be run as the main entry point for the EXE.")
    sys.exit(1)
