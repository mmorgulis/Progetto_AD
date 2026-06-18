"""
This workload benchmarks how does Cassandra handles a lot of 
concurrent threads (users) in reading and writing.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import time
import random
from concurrent.futures import ThreadPoolExecutor
from dbLogicLan import DBLogic

def write_worker(db: DBLogic, active_usernames: list, ops_per_thread: int):
    # Pure loop for write operations without intermediate simulation logic
    success_count = 0
    latencies = []
    
    for _ in range(ops_per_thread):
        target_user = random.choice(active_usernames)
        start_op = time.time()
        try:
            db.insert_one_post(username=target_user)
            latencies.append(time.time() - start_op)
            success_count += 1
        except Exception:
            pass
            
    return success_count, latencies


def read_worker(db: DBLogic, active_usernames: list, ops_per_thread: int):
    # Pure loop for read operations on the home feed table
    success_count = 0
    latencies = []
    query = "SELECT * FROM home_feed WHERE viewer_username = %s LIMIT 10"
    
    for _ in range(ops_per_thread):
        target_user = random.choice(active_usernames)
        start_op = time.time()
        try:
            db.session.execute(query, (target_user,))
            latencies.append(time.time() - start_op)
            success_count += 1
        except Exception:
            pass
            
    return success_count, latencies


def run_workload_stress_test(total_users=1000, concurrent_threads=50, ops_per_thread=100):
    db = DBLogic(consistency_level=ConsistencyLevel.ONE)
    db.query_logger_enabled = False
    db.session.default_timeout = 120.0
    
    # Clean tables to ensure a fresh starting point
    db.session.execute("TRUNCATE users")
    db.session.execute("TRUNCATE posts_by_user")
    db.session.execute("TRUNCATE home_feed")
    db.session.execute("TRUNCATE following_by_user")
    db.session.execute("TRUNCATE followers_by_user")

    # Populate the database with initial users and relations
    db.initialization(user_number=total_users)
    
    # Retrieve active usernames to guarantee valid query hits
    rows = db.session.execute("SELECT username FROM users LIMIT %s", (total_users,))
    active_usernames = [row.username for row in rows]

    # Execute intese write test phase
    start_time = time.time()
    total_writes = 0
    write_latencies = []

    with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
        futures = [
            executor.submit(write_worker, db, active_usernames, ops_per_thread)
            for _ in range(concurrent_threads)
        ]
        for future in futures:
            success, latencies = future.result()
            total_writes += success
            write_latencies.extend(latencies)

    write_duration = time.time() - start_time
    write_throughput = total_writes / write_duration if write_duration > 0 else 0
    avg_write_ms = (sum(write_latencies) / len(write_latencies)) * 1000 if write_latencies else 0

    # Cooldown sleep to minimize JVM garbage collection overlap interference
    time.sleep(2)

    # Execute intense read test phase
    start_time = time.time()
    total_reads = 0
    read_latencies = []

    with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
        futures = [
            executor.submit(read_worker, db, active_usernames, ops_per_thread)
            for _ in range(concurrent_threads)
        ]
        for future in futures:
            success, latencies = future.result()
            total_reads += success
            read_latencies.extend(latencies)

    read_duration = time.time() - start_time
    read_throughput = total_reads / read_duration if read_duration > 0 else 0
    avg_read_ms = (sum(read_latencies) / len(read_latencies)) * 1000 if read_latencies else 0

    # Print final comparison metrics display    
    # Print final comparison metrics display    
    print("\n" + "=" * 80)
    print("                      INTENSE WORKLOAD STRESS TEST REPORT                      ")
    print("=" * 80)
    print(f"{'Performance Metric':<30} | {'INTENSE WRITING':<20} | {'INTESE READING':<20}")
    print("-" * 80)
    print(f"{'Total Completed Operations':<30} | {f'{total_writes} ops':<20} | {f'{total_reads} ops':<20}")
    print(f"{'Total Execution Time':<30} | {f'{write_duration:.2f} seconds':<20} | {f'{read_duration:.2f} seconds':<20}")
    print(f"{'System Throughput':<30} | {f'{write_throughput:.2f} ops/sec':<20} | {f'{read_throughput:.2f} ops/sec':<20}")
    print(f"{'Average Request Latency':<30} | {f'{avg_write_ms:.2f} ms':<20} | {f'{avg_read_ms:.2f} ms':<20}")
    print("=" * 80)

if __name__ == "__main__":
    run_workload_stress_test(total_users=1000, concurrent_threads=25, ops_per_thread=100)