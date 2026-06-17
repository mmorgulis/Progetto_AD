"""
This workload tests the fault tolerance with 3 nodes, CL = QUORUM and RF = 2. 
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import time
import subprocess
from cassandra import ConsistencyLevel, Unavailable, WriteTimeout
from dbLogic import DBLogic

NODE1 = "cassandra-node1"
NODE2 = "cassandra-node2"
NODE3 = "cassandra-node3"
NODE4 = "cassandra-node4"

def run_cmd(cmd):
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

def test_cl_quorum():
    print("=" * 80)
    print("        FAULT TOLERANCE EVALUATION - CONSISTENCY LEVEL: QUORUM        ")
    print("=" * 80)
    
    db = DBLogic(consistency_level=ConsistencyLevel.QUORUM)
    db.query_logger_enabled = True
    db.session.default_timeout = 120.0

    # Ensure all 3 nodes are initially up
    run_cmd(f"docker start {NODE1} {NODE2} {NODE3} {NODE4}")
    time.sleep(5)

    # Clean users table for a fresh state
    db.session.execute("TRUNCATE users")
    db.session.execute("TRUNCATE posts_by_user")
    db.session.execute("TRUNCATE home_feed")
    db.session.execute("TRUNCATE following_by_user")
    db.session.execute("TRUNCATE followers_by_user")

    for i in range(1, 21):
        if i == 6:
            print(f"\n[-] INFO: Stopping {NODE4}, three nodes up")
            run_cmd(f"docker stop {NODE4}")
        elif i == 11:
            print(f"\n[-] INFO: Stopping {NODE3}, two nodes up")
            run_cmd(f"docker stop {NODE3}")
        elif i == 16:
            print(f"\n[-] INFO: Stopping {NODE2}, only one node up")
            run_cmd(f"docker stop {NODE2}")

        try:
            start = time.time()
            test_user = "user_0"
            db.insert_one_post(username=test_user)
            print(f"[{time.strftime('%H:%M:%S')}] [POST #{i:<2}] -> SUCCESS | Latency: {(time.time()-start)*1000:.2f} ms")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] [POST #{i:<2}] -> ERROR: {type(e).__name__}")
        
        time.sleep(1)
        
    print(f"\nRestarting nodes {NODE2}, {NODE3}, {NODE4}")
    run_cmd(f"docker start {NODE2} {NODE3} {NODE4}")
    

if __name__ == "__main__":
    test_cl_quorum()