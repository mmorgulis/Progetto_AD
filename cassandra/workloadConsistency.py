"""
The consistency workload is a simple benchmark, it 
executes an insertion of a post (in a initialized database)
for 1000 times and it compares the results with different 
levels of consistency (ONE, QUORUM, ALL)
"""

import time
import random
from cassandra import ConsistencyLevel
from cassandra.query import SimpleStatement
from dbLogic import DBLogic

def run_simple_consistency_benchmark(operations_count=200, total_users=100):
    print("Setting up database environment...")
    db_setup = DBLogic()
    db_setup.query_logger_enabled = False
    
    db_setup.session.default_timeout = 120.0

    # Truncating tables for a clean test state
    db_setup.session.execute("TRUNCATE users")
    db_setup.session.execute("TRUNCATE posts_by_user")
    db_setup.session.execute("TRUNCATE home_feed")
    
    print(f"Pre-populating database with {total_users} users...")
    db_setup.initialization(user_number=total_users)
    
    time.sleep(10)

    # Cache actual usernames to perform valid hits
    rows = db_setup.session.execute(f"SELECT username FROM users LIMIT {total_users}")    
    active_usernames = [row.username for row in rows]

    # Warm up to avoid cooling down
    print("Warming up Cassandra and the JVM cache...")
    warmup_statement = SimpleStatement("SELECT * FROM home_feed WHERE viewer_username = %s LIMIT 10", 
                                       consistency_level=ConsistencyLevel.ONE)
    for _ in range(100):
        dummy_user = random.choice(active_usernames)
        try:
            db_setup.insert_one_post(username=dummy_user)
            db_setup.session.execute(warmup_statement, (dummy_user,))
        except Exception:
            pass
    time.sleep(1)

    levels_to_test = [
        ("ONE", ConsistencyLevel.ONE),
        ("QUORUM", ConsistencyLevel.QUORUM),
        ("ALL", ConsistencyLevel.ALL)
    ]
    
    report = {}

    for name, level in levels_to_test:
        print(f"Evaluating Consistency Level: {name}")
        
        db = DBLogic(consistency_level=level)
        db.query_logger_enabled = False
        
        db.session.default_timeout = 60.0
                
        # Write benchmark
        write_latencies = []
        for _ in range(operations_count):
            target_user = random.choice(active_usernames)
            
            start_op = time.time()
            try:
                db.insert_one_post(username=target_user)
                write_latencies.append(time.time() - start_op)
            except Exception:
                pass

        # Read benchmark
        read_latencies = []
        read_query = "SELECT * FROM home_feed WHERE viewer_username = %s LIMIT 10"
        read_statement = SimpleStatement(read_query, consistency_level=level)

        for _ in range(operations_count):
            target_user = random.choice(active_usernames)
            
            start_op = time.time()
            try:
                db.session.execute(read_statement, (target_user,))
                read_latencies.append(time.time() - start_op)
            except Exception:
                pass

        # Calculate averages in milliseconds
        avg_write_ms = (sum(write_latencies) / len(write_latencies)) * 1000 if write_latencies else 0
        avg_read_ms = (sum(read_latencies) / len(read_latencies)) * 1000 if read_latencies else 0

        report[name] = {
            "write_ms": avg_write_ms,
            "read_ms": avg_read_ms,
            "ops": f"{len(write_latencies)}/{len(read_latencies)}"
        }
        print(f" -> Write Avg: {avg_write_ms:.2f} ms | Read Avg: {avg_read_ms:.2f} ms\n")
        time.sleep(1)

    print("\n" + "=" * 70)
    print(f"{'CONSISTENCY LEVEL BENCHMARK REPORT':^70}")
    print("=" * 70)
    print(f"{'Level':<12} | {'Avg Write Latency':<18} | {'Avg Read Latency':<18} | {'Ops (W/R)':<10}")
    print("-" * 70)
    for name in report:
        res = report[name]
        w_lat = f"{res['write_ms']:.2f} ms"
        r_lat = f"{res['read_ms']:.2f} ms"
        print(f"{name:<12} | {w_lat:<18} | {r_lat:<18} | {res['ops']:<10}")
    print("=" * 70)


if __name__ == "__main__":
    run_simple_consistency_benchmark(operations_count=2000, total_users=1000)