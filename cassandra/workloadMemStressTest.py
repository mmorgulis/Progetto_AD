"""
Injects cumulative batches of users concurrently using dbLogic's insert_k_users.
Each user record includes a 1KB binary payload to have a precise metric for the 
space occupied in the database.
"""

import time
from cassandra import ConsistencyLevel
from dbLogic import DBLogic

def run_memory_degradation_test(batch_size=1000, max_users=10000):
    print("=" * 80)
    print("     MEMORY ACCUMULATION AND PERFORMANCE DEGRADATION BENCHMARK     ")
    print("=" * 80)

    db = DBLogic(consistency_level=ConsistencyLevel.ONE)
    db.query_logger_enabled = False

    # Heavy TRUNCATE operations protected with extended 60s timeout to prevent crashs
    tables_to_truncate = ["users", "posts_by_user", "home_feed", "following_by_user", "followers_by_user"]
    print("Preparing cluster state (Truncating tables with extended timeout)...")
    
    for table in tables_to_truncate:
        try:
            db.session.execute(f"TRUNCATE {table}", timeout=60.0)
        except Exception as e:
            print(f"[-] Warning: TRUNCATE on '{table}' timed out ({type(e).__name__}). Retrying once...")
            time.sleep(3)
            try:
                db.session.execute(f"TRUNCATE {table}", timeout=60.0)
            except Exception as retry_error:
                print(f"[!] Critical: Could not truncate '{table}': {retry_error}. Moving forward.")

    print(f"\nStarting incremental injection (Batch Size: {batch_size} users, Max Cap: {max_users}).")
    print("The test will terminate if the latency spikes compared to the previous batch.")
    print("-" * 80)

    total_inserted_users = 0
    baseline_latency = None
    batch_counter = 1

    while total_inserted_users < max_users:
        start_time = time.time()
        batch_error = False
        
        try:
            db.insert_k_users(k=batch_size, photo_size=1024)
        except Exception:
            batch_error = True
                
        batch_latency = (time.time() - start_time) * 1000
        total_inserted_users += batch_size
        accumulated_payload_KB = total_inserted_users * 1

        status_str = "DRIVER_ERROR" if batch_error else "OK"

        if baseline_latency is None:
            # First batch behaves as a warm-up step
            latency_ratio = 1.0
            print(f"[BATCH #{batch_counter:<2}] Inserted {batch_size} users | Total: {total_inserted_users:<5} | Payload Size: ~{accumulated_payload_KB:<5} KB | Latency: {batch_latency:.2f} ms (WARM-UP) | Status: {status_str}")
        else:
            # Compute ratio comparing current latency to the PREVIOUS batch's latency
            latency_ratio = batch_latency / baseline_latency
            print(f"[BATCH #{batch_counter:<2}] Inserted {batch_size} users | Total: {total_inserted_users:<5} | Payload Size: ~{accumulated_payload_KB:<5} KB | Latency: {batch_latency:.2f} ms | Delta vs Prev: {latency_ratio:.2f}x | Status: {status_str}")

        # Shift the baseline: the current latency becomes the baseline for the next batch
        baseline_latency = batch_latency

        # Termination criterion: exit if latency climbs significantly (e.g., 3x) compared to the previous step
        if latency_ratio >= 3.0:
            print("\n" + "!" * 80)
            print(f"[-] BENCHMARK TERMINATED: Sudden performance degradation threshold reached.")
            print(f"Batch latency spiked by {latency_ratio:.2f}x relative to the immediately preceding batch.")
            print(f"Total sustained capacity before breakdown: {total_inserted_users} users (~{accumulated_payload_KB} KB raw payload).")
            print("!" * 80 + "\n")
            break

        batch_counter += 1
        time.sleep(0.5)
    else:
        print("\n" + "=" * 80)
        print("[+] BENCHMARK COMPLETED: Maximum user injection capacity reached without a 3x latency breakdown.")
        print(f"Final state: {total_inserted_users} users successfully stored (~{total_inserted_users} KB raw payload).")
        print("=" * 80 + "\n")

if __name__ == "__main__":
    run_memory_degradation_test(batch_size=2000, max_users=200000)