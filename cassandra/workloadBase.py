import time
import random
from concurrent.futures import ThreadPoolExecutor
from dbLogic import DBLogic, UserData, PostData

def user_lifecycle(db: DBLogic, username: str, k_ms: int, start_time: float, total_duration: int, all_users: list):
    """
    Simulates a realistic user behavioral pattern over a pre-populated database:
    - 50% chance to read their own home feed (Read Operation)
    - 30% chance to write a new post. This triggers a REAL Fan-out on-write:
    - 20% chance to follow another random user (Write Operation)
    It queries Cassandra to fetch the actual followers of the user, then updates their feeds.
    Repeats every k_ms until total_duration expires.
    """
    local_success_count = 0
    local_latencies = []
    interval_seconds = k_ms / 1000.0

    while time.time() - start_time < total_duration:
        op_start = time.time()
        try:
            action_roll = random.choices(
                population=['read_feed', 'post', 'follow'],
                weights=[0.50, 0.30, 0.20],
                k=1
            )[0]
            
            if action_roll == 'read_feed':
                # SCENARIO 1: Read own home feed
                query = "SELECT * FROM home_feed WHERE viewer_username = %s LIMIT 10"
                db.session.execute(query, (username,))
                
            elif action_roll == 'follow':
                # SCENARIO 2: Follow another user
                potential_targets = [u for u in all_users if u != username]
                if potential_targets:
                    target_to_follow = random.choice(potential_targets)
                    db.follow_user(follower_username=username, followed_username=target_to_follow)

            elif action_roll == 'post':
                # SCENARIO 3: Publish a new post (WRITE)
                post = db.insert_one_post(username=username)
                
                # FAN-OUT ON-WRITE ( = the post is immediately copied to all relevant destinations):
                # Query Cassandra to get the real followers of this specific author
                followers_query = "SELECT follower_username FROM followers_by_user WHERE username = %s"
                followers_rows = db.session.execute(followers_query, (username,))
                
                # Distribute the post strictly to the real followers found in the DB
                for row in followers_rows:
                    follower_username = row.follower_username
                    if follower_username != username:  # Prevent self-feeding
                        db.insert_row_in_the_feed(
                            viewer_username=follower_username,
                            post_id=post.post_id,
                            author_username=post.username,
                            post_text=post.post_text,
                            media_url=post.media_url,
                            media_type=post.media_type,
                            location=post.location
                        )

            op_latency = time.time() - op_start
            local_latencies.append(op_latency)
            local_success_count += 1

        except Exception as e:
            # Avoid breaking the thread execution if a single operation timeouts under heavy load
            pass

        # Pacing control
        time.sleep(interval_seconds)

    return local_success_count, local_latencies


def run_workload_base(k_ms, total_duration, total_users=100):
    """
    Executes the social network interaction benchmark over an initialized environment.
    """
    db = DBLogic()
    
    # Clean the database tables before running the benchmarks for a clean state
    print("Truncating tables for clean state...")
    db.session.execute("TRUNCATE users")
    db.session.execute("TRUNCATE posts_by_user")
    db.session.execute("TRUNCATE home_feed")
    db.session.execute("TRUNCATE following_by_user")
    db.session.execute("TRUNCATE followers_by_user")
    print("Tables truncated successfully.")

    # Mute query logs to measure true Cassandra engine speed
    db.query_logger_enabled = False

    # Standard database initialization to build up realistic social structures
    print(f"Pre-populating database with {total_users} users for the baseline environment...")
    init_summary = db.initialization(user_number=total_users)
    print(f"Baseline ready: {init_summary['users']} users, {init_summary['posts']} posts, and {init_summary['following_relations']} follow edges.")

    # Generate the reference list of users matching the initialization pattern (user_0, user_1...)
    simulated_usernames = [f"user_{i}" for i in range(total_users)]
    
    CONCURRENT_USER = 50 
    
    print(f" -> Active Thread Clients: {CONCURRENT_USER}")
    print(f" -> User Request Pacing (k_ms): {k_ms}ms")
    print(f" -> Total Duration: {total_duration} seconds\n")

    start_time = time.time()
    total_successful_ops = 0
    global_latencies = []

    with ThreadPoolExecutor(max_workers=CONCURRENT_USER) as executor:
        futures = []
        for i in range(CONCURRENT_USER):
            # Select an identity from the pool for this thread
            worker_username = f"user_{random.randint(0, total_users - 1)}"
            futures.append(
                executor.submit(
                    user_lifecycle, db, worker_username, k_ms, start_time, total_duration, simulated_usernames
                )
            )

        for future in futures:
            success_count, thread_latencies = future.result()
            total_successful_ops += success_count
            global_latencies.extend(thread_latencies)

    end_time = time.time()
    actual_duration = end_time - start_time
    
    throughput = total_successful_ops / actual_duration if actual_duration > 0 else 0
    avg_latency_ms = (sum(global_latencies) / len(global_latencies)) * 1000 if global_latencies else 0

    print("=" * 60)
    print("                WORKLOAD BASE BENCHMARK RESULTS                ")
    print("=" * 60)
    print(f"Actual Execution Time:   {actual_duration:.2f} seconds")
    print(f"Total Completed Actions: {total_successful_ops} ops")
    print(f"System Throughput:       {throughput:.2f} operations/sec")
    print(f"Average Action Latency:  {avg_latency_ms:.2f} ms")
    print("=" * 60)


if __name__ == "__main__":
    run_workload_base(k_ms=500, total_duration=60, total_users=1000)