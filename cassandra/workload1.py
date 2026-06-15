import time
import dbLogic

def run_workload1(k_ms, total_users=100):
    """
    The first possible workload is simply inserting a single random user 
    every k millisecond. For example 30ms for every users till 100
    """
    db = dbLogic.DBLogic()
    
    # Automatically clear database tables before running the benchmarks
    print("Truncating tables for clean state...")
    db.session.execute("TRUNCATE users")
    db.session.execute("TRUNCATE posts_by_user")
    db.session.execute("TRUNCATE home_feed")
    
    print(f"Starting Workload 1: Inserting {total_users} standard users via insert_one_user() (1 every {k_ms} ms)...")
    start_time = time.time()
    
    for i in range(total_users):
        # Calls the function without extra parameters to generate standard profiles
        db.insert_one_user()
        time.sleep(k_ms / 1000.0)
        
    end_time = time.time()
    print(f"Workload 1 finished. Total execution time: {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    run_workload1(k_ms=30, total_users=100)