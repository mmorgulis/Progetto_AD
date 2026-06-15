import time
import dbLogic

def run_workload2(users_to_stress=150):
    db = dbLogic.DBLogic()
    
    # Automatically wipe the cluster state to guarantee a standard baseline
    print("Truncating tables for clean baseline...")
    db.session.execute("TRUNCATE users")
    db.session.execute("TRUNCATE posts_by_user")
    db.session.execute("TRUNCATE home_feed")
    
    print("Phase 1: Seeding initial network context using initialization()...")
    summary = db.initialization(user_number=40)
    print(f"Base data seeded: {summary['users']} users, {summary['posts']} posts inside cluster.")
    
    print(f"Phase 2: Injecting {users_to_stress} additional standard users using insert_k_users()...")
    start_time = time.time()
    
    # Executing the standard iteration through the interface wrapper
    db.insert_k_users(users_to_stress)
    
    end_time = time.time()
    print(f"Workload 2 finished. Processed batch in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    run_workload2()