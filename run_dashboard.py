import subprocess
import sys

def main():
    print("Starting Memory Intelligence Dashboard...")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "src/dashboard/app.py"])
    except KeyboardInterrupt:
        print("\nDashboard stopped.")

if __name__ == "__main__":
    main()
