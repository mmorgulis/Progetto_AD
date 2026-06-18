"""
Benchmarks Cassandra's Read Miss handling efficiency sequentially by comparing
queries against existing keys (Read Hits) versus non-existent keys (Read Misses).
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import time
import random
from dbLogicLan import DBLogic

def run_workload_read_miss(operations_count=500, total_users=200):
    db = DBLogic()
    db.query_logger_enabled = False
    db.session.default_timeout = 120.0
    
    # Clean tables to ensure a fresh starting point
    db.session.execute("TRUNCATE users")
    db.session.execute("TRUNCATE posts_by_user")
    db.session.execute("TRUNCATE home_feed")
    db.session.execute("TRUNCATE following_by_user")
    db.session.execute("TRUNCATE followers_by_user")

    # Populate the database using dbLogic built-in initialization
    db.initialization(user_number=total_users)
    
    # Retrieve active usernames to guarantee valid query hits
    rows = db.session.execute("SELECT username FROM users LIMIT %s", (total_users,))
    active_usernames = [row.username for row in rows]
    
    # Generate fake keys beforehand to avoid runtime string manipulation overhead
    fake_usernames = [f"non_existent_user_9999_{i}" for i in range(operations_count)]

    query = "SELECT * FROM home_feed WHERE viewer_username = %s LIMIT 10"
    time.sleep(1)

    # Sequential Read Hit Phase
    start_time = time.time()
    total_hits = 0
    hit_latencies = []

    for _ in range(operations_count):
        target_user = random.choice(active_usernames)
        start_op = time.time()
        try:
            db.session.execute(query, (target_user,))
            hit_latencies.append(time.time() - start_op)
            total_hits += 1
        except Exception:
            pass

    hit_duration = time.time() - start_time
    hit_throughput = total_hits / hit_duration if hit_duration > 0 else 0
    avg_hit_ms = (sum(hit_latencies) / len(hit_latencies)) * 1000 if hit_latencies else 0

    time.sleep(1)

    # Sequential Read Miss Phase
    start_time = time.time()
    total_misses = 0
    miss_latencies = []

    for _ in range(operations_count):
        target_user = random.choice(fake_usernames)
        start_op = time.time()
        try:
            db.session.execute(query, (target_user,))
            miss_latencies.append(time.time() - start_op)
            total_misses += 1
        except Exception:
            pass

    miss_duration = time.time() - start_time
    miss_throughput = total_misses / miss_duration if miss_duration > 0 else 0
    avg_miss_ms = (sum(miss_latencies) / len(miss_latencies)) * 1000 if miss_latencies else 0

    # Print final comparison metrics display
    print("\n" + "=" * 80)
    print("                      READ MISS VS READ HIT TEST REPORT                        ")
    print("=" * 80)
    print(f"{'Performance Metric':<30} | {'READ HIT (REAL KEYS)':<20} | {'READ MISS (FAKE KEYS)':<20}")
    print("-" * 80)
    print(f"{'Total Completed Operations':<30} | {f'{total_hits} ops':<20} | {f'{total_misses} ops':<20}")
    print(f"{'Total Execution Time':<30} | {f'{hit_duration:.2f} seconds':<20} | {f'{miss_duration:.2f} seconds':<20}")
    print(f"{'System Throughput':<30} | {f'{hit_throughput:.2f} ops/sec':<20} | {f'{miss_throughput:.2f} ops/sec':<20}")
    print(f"{'Average Request Latency':<30} | {f'{avg_hit_ms:.2f} ms':<20} | {f'{avg_miss_ms:.2f} ms':<20}")
    print("=" * 80)
    
if __name__ == "__main__":
    run_workload_read_miss(operations_count=1000, total_users=100)