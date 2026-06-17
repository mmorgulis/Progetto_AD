"""
Injects cumulative batches of users concurrently using dbLogic's insert_k_users.
Each user record includes a 1KB binary payload to have a precise metric for the 
space occupied in the database.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import time
from cassandra import ConsistencyLevel
from dbLogic import DBLogic

def run_memory_degradation_test(batch_size=1000, max_users=1000000):
    print("=" * 80)
    print("     MEMORY ACCUMULATION AND PERFORMANCE DEGRADATION BENCHMARK     ")
    print("=" * 80)

    db = DBLogic(consistency_level=ConsistencyLevel.ONE)
    db.query_logger_enabled = False
    db.session.default_timeout = 120.0

    # Clean tables to ensure a completely fresh test state
    db.session.execute("TRUNCATE users")
    db.session.execute("TRUNCATE posts_by_user")
    db.session.execute("TRUNCATE home_feed")
    db.session.execute("TRUNCATE following_by_user")
    db.session.execute("TRUNCATE followers_by_user")    

    print(f"\nStarting incremental injection (Batch Size: {batch_size} users, Max Cap: {max_users}).")
    print("The test will terminate if latency remains >= 2.0x the baseline for 3 consecutive batches.")
    print("-" * 80)

    total_inserted_users = 0
    baseline_latency = None
    batch_counter = 1
    
    # Counter to track consecutive batches that exceed the degradation threshold
    consecutive_spikes = 0

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

        if batch_counter == 1:
            # Batch #1 acts purely as a warm-up phase
            print(f"[BATCH #{batch_counter:<2}] Inserted {batch_size} users | Total: {total_inserted_users:<6} | Payload Size: ~{accumulated_payload_KB:<6} KB | Latency: {batch_latency:.2f} ms (WARM-UP) | Status: {status_str}")
        
        elif batch_counter == 2:
            # Batch #2 is established as our fixed baseline reference
            baseline_latency = batch_latency
            print(f"[BATCH #{batch_counter:<2}] Inserted {batch_size} users | Total: {total_inserted_users:<6} | Payload Size: ~{accumulated_payload_KB:<6} KB | Latency: {batch_latency:.2f} ms (BASE) | Status: {status_str}")
        
        else:
            # From Batch #3 onwards, compare current latency against the fixed baseline
            latency_ratio = batch_latency / baseline_latency
            
            # Check if the current batch is a spike (>= 2.0x)
            if latency_ratio >= 2.0:
                consecutive_spikes += 1
            else:
                consecutive_spikes = 0 # Reset the streak if performance recovers
                
            print(f"[BATCH #{batch_counter:<2}] Inserted {batch_size} users | Total: {total_inserted_users:<6} | Payload Size: ~{accumulated_payload_KB:<6} KB | Latency: {batch_latency:.2f} ms | Delta vs Base: {latency_ratio:.2f}x (Streak: {consecutive_spikes}/3) | Status: {status_str}")

            # Termination criterion: stop if the last 3 consecutive runs (k-2, k-1, k) are all >= 2.0x
            if consecutive_spikes >= 3:
                print("\n" + "!" * 80)
                print(f"[-] BENCHMARK TERMINATED: Sustained performance degradation threshold reached.")
                print(f"Latency remained >= 2.0x relative to the baseline for 3 consecutive batches.")
                print(f"Total sustained capacity before breakdown: {total_inserted_users} users (~{accumulated_payload_KB} KB raw payload).")
                print("!" * 80 + "\n")
                break

        batch_counter += 1
        time.sleep(0.5)
    else:
        print("\n" + "=" * 80)
        print("[+] BENCHMARK COMPLETED: Maximum user injection capacity reached without a sustained 2.0x latency breakdown.")
        print(f"Final state: {total_inserted_users} users successfully stored (~{total_inserted_users} KB raw payload).")
        print("=" * 80 + "\n")

if __name__ == "__main__":
    run_memory_degradation_test(batch_size=2000, max_users=1000000)