import time
import dbLogic

def run_workload3(fixed_photo_size_bytes, total_users=100):
    db = dbLogic.DBLogic()
    
    # Wipe data completely before checking memory/io footprint constraints
    print("Wiping database tables for strict size isolation testing...")
    db.session.execute("TRUNCATE users")
    db.session.execute("TRUNCATE posts_by_user")
    db.session.execute("TRUNCATE home_feed")
    
    print(f"Starting Workload 3: Benchmarking {total_users} users with forced blob size: {fixed_photo_size_bytes / 1024:.2f} KB...")
    start_time = time.time()
    
    # Invoking insert_k_users with the image size argument to trigger custom photo generation
    db.insert_k_users(total_users, photo_size=fixed_photo_size_bytes)
    
    end_time = time.time()
    print(f"Workload 3 completed in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    # Test boundary limits using a specific size (clipping mechanism handles values over limits)
    TARGET_SIZE_BYTES = 8 * 1024  # 8 KB image
    run_workload3(fixed_photo_size_bytes=TARGET_SIZE_BYTES, total_users=100)