import schedule
import time
from data_loader import update_database
from datetime import datetime

def job():
    print(f"[{datetime.now()}] Starting scheduled data update...")
    try:
        update_database()
        print(f"[{datetime.now()}] Update completed successfully.")
    except Exception as e:
        print(f"[{datetime.now()}] Update failed: {e}")

def run_scheduler():
    print("Starting Finance Dashboard Scheduler...")
    print("Data will be updated every hour.")
    
    # Run once immediately on start
    job()
    
    # Schedule every hour
    schedule.every(1).hours.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60) # Check every minute

if __name__ == "__main__":
    run_scheduler()
