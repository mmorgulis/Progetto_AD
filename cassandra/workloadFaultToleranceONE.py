import time
import subprocess
from cassandra import ConsistencyLevel, Unavailable, WriteTimeout
from dbLogic import DBLogic

NODE1, NODE2, NODE3 = "cassandra-node1", "cassandra-node2", "cassandra-node3"

def run_cmd(cmd):
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

def test_cl_one():
    """
    The function test the fault tolerance with 3 nodes, CL = ONE and RF = 3. 
    It must continue working also with 2 nodes down.
    """
    print("=" * 80)
    print("        FAULT TOLERANCE EVALUATION - CONSISTENCY LEVEL: ONE        ")
    print("=" * 80)
    
    db = DBLogic(consistency_level=ConsistencyLevel.ONE)
    db.query_logger_enabled = True

    run_cmd(f"docker start {NODE1} {NODE2} {NODE3}")
    db.session.execute("TRUNCATE home_feed")
    
    test_user = "user_0"
    
    for i in range(1, 41):
        if i == 10:
            print(f"\n[-] INFO: Stopping {NODE3}, two nodes still up")
            run_cmd(f"docker stop {NODE3}")
        elif i == 20:
            print(f"\n[-] INFO: Stopping {NODE2}, only one node up")
            run_cmd(f"docker stop {NODE2}")
        elif i == 30:
            print(f"\n[+] INFO: Restarting nodes {NODE2}, {NODE3}.")
            run_cmd(f"docker start {NODE2} {NODE3}")
            time.sleep(15)

        try:
            start = time.time()
            db.insert_one_post(username=test_user)
            print(f"[{time.strftime('%H:%M:%S')}] [POST #{i:<2}] -> SUCCESS | Latency: {(time.time()-start)*1000:.2f} ms")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] [POST #{i:<2}] -> ERROR: {type(e).__name__}")
        time.sleep(1)

if __name__ == "__main__":
    test_cl_one()