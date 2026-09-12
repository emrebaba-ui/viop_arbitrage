import sys
from dashboard import main as run_dashboard

def start():
    # Start the main loop from dashboard.py
    try:
        run_dashboard()
    except KeyboardInterrupt:
        print("\n\nArbitrage Dashboard stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start()