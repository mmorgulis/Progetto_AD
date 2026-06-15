import time
import dbLogic

def run_workload2(users_to_stress=150):
    db = dbLogic.DBLogic()

    # Clean the database tables before running the benchmarks for a clean state
    print("Truncating tables for clean state...")
    db.session.execute("TRUNCATE users")
    db.session.execute("TRUNCATE posts_by_user")
    db.session.execute("TRUNCATE home_feed")
    db.session.execute("TRUNCATE following_by_user")
    db.session.execute("TRUNCATE followers_by_user")
    print("Tables truncated successfully.")

if __name__ == "__main__":
    run_workload2()