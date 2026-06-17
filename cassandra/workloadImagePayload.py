"""
Benchmarks Cassandra's write performance variation sequentially under different 
profile picture BLOB sizes using the built-in user insertion logic.
"""

import time
from dbLogic import DBLogic

def run_workload_image_payload(operations_count=200):
    db = DBLogic()
    db.query_logger_enabled = False

    # Clean users table for a fresh state
    db.session.execute("TRUNCATE users")
    db.session.execute("TRUNCATE posts_by_user")
    db.session.execute("TRUNCATE home_feed")
    db.session.execute("TRUNCATE following_by_user")
    db.session.execute("TRUNCATE followers_by_user")

    small_payload = 1 * 1024    # 1 KB
    large_payload = 100 * 1024  # 100 KB

    # Dynamically lift the default safety cap set in dbLogic initialization
    db.MAX_PROFILE_SIZE = large_payload

    # Sequential Small Payload Phase (1 KB)
    start_time = time.time()
    total_small_writes = 0
    small_latencies = []

    for _ in range(operations_count):
        start_op = time.time()
        try:
            db.insert_one_user(photo_size=small_payload)
            small_latencies.append(time.time() - start_op)
            total_small_writes += 1
        except Exception:
            pass

    small_duration = time.time() - start_time
    small_throughput = total_small_writes / small_duration if small_duration > 0 else 0
    avg_small_ms = (sum(small_latencies) / len(small_latencies)) * 1000 if small_latencies else 0

    time.sleep(1)

    # Sequential Large Payload Phase (100 KB)
    start_time = time.time()
    total_large_writes = 0
    large_latencies = []

    for _ in range(operations_count):
        start_op = time.time()
        try:
            db.insert_one_user(photo_size=large_payload)
            large_latencies.append(time.time() - start_op)
            total_large_writes += 1
        except Exception:
            pass

    large_duration = time.time() - start_time
    large_throughput = total_large_writes / large_duration if large_duration > 0 else 0
    avg_large_ms = (sum(large_latencies) / len(large_latencies)) * 1000 if large_latencies else 0

    # Print final comparison metrics display
    print("\n" + "=" * 80)
    print("                    IMAGE PAYLOAD BLOB SIZE STRESS TEST REPORT                  ")
    print("=" * 80)
    print(f"{'Performance Metric':<30} | {'SMALL PAYLOAD (1 KB)':<20} | {'LARGE PAYLOAD (100 KB)':<20}")
    print("-" * 80)
    print(f"{'Total Completed Insertions':<30} | {f'{total_small_writes} ops':<20} | {f'{total_large_writes} ops':<20}")
    print(f"{'Total Execution Time':<30} | {f'{small_duration:.2f} seconds':<20} | {f'{large_duration:.2f} seconds':<20}")
    print(f"{'System Throughput':<30} | {f'{small_throughput:.2f} ops/sec':<20} | {f'{large_throughput:.2f} ops/sec':<20}")
    print(f"{'Average Write Latency':<30} | {f'{avg_small_ms:.2f} ms':<20} | {f'{avg_large_ms:.2f} ms':<20}")
    print("=" * 80)

if __name__ == "__main__":
    run_workload_image_payload(operations_count=1000)