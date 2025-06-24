from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess
import sys
import os
from datetime import datetime

def run_importexport_script():
    """Runs the importexport.py script located in the workspace directory."""
    base_folder = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(base_folder, "importexport.py")
    print(f"[{datetime.now()}] Starting the importexport.py script...")
    try:
        # Use the current interpreter (from the virtual environment) to run the script
        subprocess.run([sys.executable, script_path], check=True)
        print(f"[{datetime.now()}] importexport.py completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] Error running importexport.py: {e}")

if __name__ == '__main__':
    # Create a scheduler that runs with the US/Central timezone.
    scheduler = BlockingScheduler(timezone="US/Central")
    
    # Schedule the job to run every day at 8:00 AM Central Time.
    scheduler.add_job(run_importexport_script, 'cron', hour=8, minute=0)
    
    # Schedule the job to run every day at 6:00 PM (18:00) Central Time.
    scheduler.add_job(run_importexport_script, 'cron', hour=18, minute=0)
    
    print(f"[{datetime.now()}] Scheduler started. Waiting for 8:00 AM and 6:00 PM Central Time to run the script...")
    
    try:
        scheduler.start()  # This call blocks and runs indefinitely.
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")
