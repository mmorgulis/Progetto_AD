import os
import hashlib
import uuid
import random
import datetime
from dataclasses import dataclass
from faker import Faker
from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args
from cassandra import ConsistencyLevel

@dataclass
class UserData:
    """ Dataclass representing user profile records inside the application layers """
    username: str
    email: str
    password_hash: str
    first_name: str
    last_name: str
    profile_picture: bytes = None

@dataclass
class PostData:
    """ Dataclass representing post records inside the application layers """
    username: str
    post_id: uuid.UUID
    post_text: str
    media_url: str = None
    media_type: str = None
    location: str = None

class DBLogic:
    def __init__(self, consistency_level=ConsistencyLevel.QUORUM):

        # Using actual nodes
        hosts_env = os.getenv('CASSANDRA_HOSTS')
        if hosts_env:
            self.CONTACT_POINTS = hosts_env.split(',')
        else:
            self.CONTACT_POINTS = ['192.168.1.34', '192.168.1.35', '192.168.1.27']

        self.CQL_PORT = 9042
        self.USER_NUMBER_INIT = 50
        self.PROFILE_PICTURE_SIZES = (1 * 1024, 5 * 1024, 10 * 1024)
        self.PASSWORD_LENGTH = 12
        self.MAX_PROFILE_SIZE = 100 * 1024 # 100 KB
        self.MIN_FOLLOWERS_PER_USER = 0
        self.MAX_FOLLOWERS_PER_USER = self.USER_NUMBER_INIT // 4
        self.query_logger_enabled = True
        self.CONCURRENCY_FACTOR = 10

        print("Connecting to Cassandra...")

        self.cluster = Cluster(self.CONTACT_POINTS, port=self.CQL_PORT)
        self.session = self.cluster.connect()
        self.session.set_keyspace('network_giustino')

        print("Connected to the keyspace network_giustino\n")

        # Query logger
        self.session.add_request_init_listener(self._log_cql_queries)

        # Faker singleton
        self.fake = Faker(['en_US'])
        self.profile_pictures = [random.randbytes(size) for size in self.PROFILE_PICTURE_SIZES]

        # Prepared statements
        self.insert_user = self.session.prepare("""
            INSERT INTO users (username, email, password_hash, first_name, last_name, profile_picture)
            VALUES (?, ?, ?, ?, ?, ?)
        """)
        self.insert_post = self.session.prepare("""
            INSERT INTO posts_by_user (username, post_id, post_text, media_url, media_type, location)
            VALUES (?, ?, ?, ?, ?, ?)
        """)

        self.insert_feed = self.session.prepare("""
            INSERT INTO home_feed (viewer_username, post_id, author_username, post_text, media_url, media_type, location)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """)

        # Prepared statements for relationship tables (following and followers)
        self.insert_following = self.session.prepare("""
            INSERT INTO following_by_user (username, followed_username, followed_at)
            VALUES (?, ?, ?)
        """)

        self.insert_followers = self.session.prepare("""
            INSERT INTO followers_by_user (username, follower_username, followed_at)
            VALUES (?, ?, ?)
        """)

        # Consistency level
        self.insert_user.consistency_level = consistency_level
        self.insert_post.consistency_level = consistency_level
        self.insert_feed.consistency_level = consistency_level
        self.insert_following.consistency_level = consistency_level
        self.insert_followers.consistency_level = consistency_level

    def _log_cql_queries(self, response_future):
        """
        Fallback function that intercepts all the queries on the database
        """
        if not self.query_logger_enabled:
            return

        statement = response_future.query

        # Query is a prepared statement (mostly our case)
        if hasattr(statement, 'prepared_statement'):
            cql_string = statement.prepared_statement.query_string.strip()
            
            # Readable log
            clean_values = []
            for val in statement.values:
                if isinstance(val, (bytes, bytearray)):
                    clean_values.append(f"<Binary BLOB: {len(val)} bytes>")
                else:
                    clean_values.append(val)
                    
            print(f"[CQL PREPARED] {cql_string}")
            print(f"   -> Params: {tuple(clean_values)}\n")

        # Query is an "INSERT ..." statement
        elif isinstance(statement, str):
            print(f"[CQL DIRECT] {statement.strip()}\n")
            
        # Other queries
        else:
            print(f"[CQL EXEC] {statement}\n")
    
    def create_random_user(self, HAS_PHOTO = True, PHOTO_SIZE = None):
        """
        The function generate a random user, if it has a given probability to have 
        a profile photo with k bytes. The function returns all the parameters 
        to create a user, so first_name, last_name, username, email, password_hash, 
        profile_picture. A user this created weights around.
        """
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()

        username = f"{first_name.lower()}.{last_name.lower()}"
        email = f"{username}@{self.fake.free_email_domain()}"

        password = self.fake.password(length=self.PASSWORD_LENGTH)
        # Sha256 does a rapid hashing of the passwords, just
        # to have credible password into the databases. In
        # reality you should encrypt every user with a random salt (bcprypt)
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        random_number = random.randrange(6)
        # Simulation of profile images: 50% does not have an image and the others
        # has a uniform distribution with images weighting 1KB, 5KB, 10KB
        if HAS_PHOTO == True:
            if PHOTO_SIZE is not None:
                if PHOTO_SIZE > self.MAX_PROFILE_SIZE:
                    PHOTO_SIZE = self.MAX_PROFILE_SIZE
                # Images of requested size
                profile_picture = random.randbytes(PHOTO_SIZE)
            else:
                if random_number < 3:
                    profile_picture = None
                else:
                    profile_picture = self.profile_pictures[random_number - 3]
        else:
            profile_picture = None

        return UserData(
            username=username,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            profile_picture=profile_picture
        )
    
    def create_random_post(self, username):
        """
        Generates a random post for a specific user
        """
        if not username:
            raise ValueError("The post must have au author")

        post_id = uuid.uuid1() 
        post_text = self.fake.sentence(nb_words=14) 
        
        # Distribution on media:
        # 50% None, 25% image, 25% video
        media_roll = random.choice(['none', 'none', 'image', 'video'])
        
        if media_roll == 'none':
            media_url = None
            media_type = None
        elif media_roll == 'image':
            media_url = self.fake.image_url()
            media_type = "image"
        else: # video
            media_url = self.fake.url() + "/video.mp4"
            media_type = "video"

        # Distribution on location:
        # 50% None, 50% location
        location_roll = random.choice(['none', 'location'])
        if location_roll == 'none':
            location = None
        else:
            location = self.fake.city()

        # Return a strongly-typed PostData dataclass object
        return PostData(
            username=username,
            post_id=post_id,
            post_text=post_text,
            media_url=media_url,
            media_type=media_type,
            location=location
        )

    def post_count_for_user(self, user_index):
        """
        The function returns the number of post the a user have, the strategy to create 
        a possibile real database is that most users have 0 or 1 post,
        a smaller group has a few posts, and a tiny tail reaches 100.
        """
        bucket = user_index % 100

        if bucket < 35:
            return 0
        if bucket < 65:
            return 1
        if bucket < 85:
            return 2 + ((bucket - 65) % 4)
        if bucket < 95:
            return 10 + ((bucket - 85) % 11)

        return [50, 75, 100, 75, 50][bucket - 95]

    def initialization(self, user_number=None):
        """
        The function fills the database with credible data; 
        it is probably slow, but that's because we want to simulate
        a possible real scenario, furthermore the initialization function
        must be used only once, so it's not so time critical. 
        It returns how many users, posts and feed rows has inserted (for the logs).
        """
        if user_number is None:
            user_number = self.USER_NUMBER_INIT

        previous_logger_state = self.query_logger_enabled
        self.query_logger_enabled = False

        # Previous preferences
        orig_user_cl = self.insert_user.consistency_level
        orig_post_cl = self.insert_post.consistency_level
        orig_feed_cl = self.insert_feed.consistency_level
        orig_following_cl = self.insert_following.consistency_level
        orig_followers_cl = self.insert_followers.consistency_level

        # Force ONE consistency level to avoid timeouts
        self.insert_user.consistency_level = ConsistencyLevel.ONE
        self.insert_post.consistency_level = ConsistencyLevel.ONE
        self.insert_feed.consistency_level = ConsistencyLevel.ONE
        self.insert_following.consistency_level = ConsistencyLevel.ONE
        self.insert_followers.consistency_level = ConsistencyLevel.ONE

        usernames = []
        usernames_set = set() # registry to ensure absolute uniqueness in memory

        print(f"Data generation for {user_number} users...")
        user_args_list = []
        print("User insertion in progress ...")
        for i in range(user_number):
            user = self.create_random_user()

            # Resolve username collisions at the application level
            # It adds a little time, but it's required for consistency
            base_username = user.username
            counter = 1
            # Adds a counter to the username to avoid collision
            while user.username in usernames_set:
                user.username = f"{base_username}{counter}"
                counter += 1

            usernames_set.add(user.username)
            usernames.append(user.username)

            # For inserting a large number of users, is required to use the 
            # async call, instead python would be waiting for the rrt of the call every .execute
            user_args_list.append((user.username, user.email, user.password_hash, user.first_name, user.last_name, 
                                   user.profile_picture))
            
        # Concurrent esecution
        results_users = execute_concurrent_with_args(
            self.session, self.insert_user, user_args_list, concurrency=self.CONCURRENCY_FACTOR
        )
        inserted_users = len(results_users)

        # Generate a realistic social graph relationship network
        print("Generating follow relationships...")
        following_args_list = []
        followers_args_list = []
        
        # In-memory index mapping to efficiently map author -> list of followers for feed fan-out
        author_to_followers = {u: [] for u in usernames}
        now = datetime.datetime.now()

        for follower in usernames:
            # Prevent a user from following themselves
            potential_targets = [u for u in usernames if u != follower]
            # Each user follows a random number of profiles
            num_to_follow = min(len(potential_targets), random.randint(self.MIN_FOLLOWERS_PER_USER, self.MAX_FOLLOWERS_PER_USER))
            followed_users = random.sample(potential_targets, k=num_to_follow)
            
            for followed in followed_users:
                following_args_list.append((follower, followed, now))
                followers_args_list.append((followed, follower, now))
                author_to_followers[followed].append(follower)

        print(f"Inserting {len(following_args_list)} following relationships...")
        execute_concurrent_with_args(self.session, self.insert_following, following_args_list, concurrency=self.CONCURRENCY_FACTOR)

        print(f"Inserting {len(followers_args_list)} followers relationships...")
        execute_concurrent_with_args(self.session, self.insert_followers, followers_args_list, concurrency=self.CONCURRENCY_FACTOR)

        # Steps to create the posts (distribution described in post_count_for_user)
        print("Generating posts and feed ...")
        post_args_list = []
        feed_args_list = []
        for user_index, username in enumerate(usernames):
            post_count = self.post_count_for_user(user_index)

            for post_index in range(post_count):
                # Store the posts
                post = self.create_random_post(username)
                post_args_list.append((post.username, post.post_id, post.post_text, post.media_url, post.media_type, post.location))

                # Fan-out on-write implementation: populate feed for actual followers of the author
                for follower_username in author_to_followers[username]:
                    feed_args_list.append((follower_username, post.post_id, username, post.post_text, post.media_url, post.media_type, post.location))

        # Concurrent esecution for posts
        print(f"Inserting {len(post_args_list)} post...")
        results_posts = execute_concurrent_with_args(
            self.session, self.insert_post, post_args_list, concurrency=self.CONCURRENCY_FACTOR
        )
        inserted_posts = len(results_posts)

        # Concurrent esecution for feed
        print(f"Inserting {len(feed_args_list)} rows of home feed...")
        results_feed = execute_concurrent_with_args(
            self.session, self.insert_feed, feed_args_list, concurrency=self.CONCURRENCY_FACTOR
        )
        inserted_feed_rows = len(results_feed)

        # Restore previous consistency levels
        self.insert_user.consistency_level = orig_user_cl
        self.insert_post.consistency_level = orig_post_cl
        self.insert_feed.consistency_level = orig_feed_cl
        self.insert_following.consistency_level = orig_following_cl
        self.insert_followers.consistency_level = orig_followers_cl

        self.query_logger_enabled = previous_logger_state

        return {
            "users": inserted_users,
            "posts": inserted_posts,
            "feed_rows": inserted_feed_rows,
            "following_relations": len(following_args_list)
        }

    def insert_one_user(self, username=None, email=None, password_hash=None, 
                        first_name=None, last_name=None, profile_picture=None, photo_size=None):
        """
        Inserts a single user into the database. It can be done passing all the parameters 
        like a real application or, if the username is not passed the function will create 
        the user randomly. It's possible to specify a photo_size for benchmarking how the 
        size of the foto changes the performances of the databases.
        """
        if username is None:
            # Test mode
            if photo_size is not None:
                user = self.create_random_user(HAS_PHOTO=True, PHOTO_SIZE=photo_size)
            else:
                user = self.create_random_user()
        else:
            # Suppose real data from application
            user = UserData(
                username=username,
                email=email,
                password_hash=password_hash,
                first_name=first_name,
                last_name=last_name,
                profile_picture=profile_picture
            )

        self.session.execute(
            self.insert_user, 
            (user.username, user.email, user.password_hash, user.first_name, user.last_name, user.profile_picture)
        )
        
        return user
    
    def insert_k_users(self, k, photo_size = None):
        """
        Inserts k random users. If k is below a threshold, it runs sequentially.
        If k is larger, it builds a batch list and executes concurrently/async 
        to maximize Cassandra's write performance capacity.
        """
        CONCURRENCY_THRESHOLD = 25

        if k < CONCURRENCY_THRESHOLD:
            # Fallback to synchronous sequential loop for small inputs
            for i in range(k):
                self.insert_one_user(photo_size=photo_size)
        else:
            # High throughput async concurrent pipeline execution for larger batches
            user_args_list = []
            for i in range(k):
                if photo_size is not None:
                    user = self.create_random_user(HAS_PHOTO=True, PHOTO_SIZE=photo_size)
                else:
                    user = self.create_random_user()
                
                # Append params matching our prepared statement structure
                user_args_list.append((user.username, user.email, user.password_hash, user.first_name, user.last_name, user.profile_picture))
            
            # Execute concurrently with an optimized driver execution pool 
            execute_concurrent_with_args(self.session, self.insert_user, user_args_list, concurrency=self.CONCURRENCY_FACTOR)

    def insert_one_post(self, username, post_text=None, media_url=None, media_type=None, location=None):
        """
        I can suppose that the interface force the user to be logged to create a post, so 
        in this function the caller must call the function with a valid username, thus 
        there will be no particular control. Of course is infeasible to do here a control 
        if the user is real.
        """
        if post_text is None:
            post = self.create_random_post(username)
        else:
            post = PostData(
                username=username,
                post_id=uuid.uuid1(),
                post_text=post_text,
                media_url=media_url,
                media_type=media_type,
                location=location
            )

        self.session.execute(
            self.insert_post, 
            (post.username, post.post_id, post.post_text, post.media_url, post.media_type, post.location)
        )

        return post

    def follow_user(self, follower_username, followed_username):
        """
        Establishes a follow relationship between two users at an application level.
        Inserts data simultaneously into both 'following_by_user' and 'followers_by_user'
        to respect Cassandra's data duplication patterns and maintain query throughput.
        """
        if not follower_username or not followed_username:
            raise ValueError("Both follower and followed usernames must be valid")

        now = datetime.datetime.now()

        # Update the following catalog (from the follower's perspective)
        self.session.execute(self.insert_following, (follower_username, followed_username, now))

        # Update the followers catalog (from the followed user's perspective)
        self.session.execute(self.insert_followers, (followed_username, follower_username, now))

        return {
            "follower_username": follower_username,
            "followed_username": followed_username,
            "followed_at": now
        }
    
    def insert_row_in_the_feed(self, viewer_username, post_id, post_text, author_username, 
                               media_url=None, media_type=None, location=None):
        """
        The function puts a new row (a post) in the home_feed table, the text is mandatory, the remaining 
        parts of the post are optional. As the insertion of the post, I can suppose that the upper 
        layer gave me an existing user and post.
        """
        self.session.execute(self.insert_feed, 
                             (viewer_username, post_id, author_username, post_text, media_url, media_type, location)
        )

    def insert_feed_to_followers_concurrent(self, followers_list, post_id, author_username, post_text, 
                                        media_url=None, media_type=None, location=None):
        """
        The function inserts concurrently the posts in the feed of all followers, with the 
        async call.
        """
        # Prepare the args for all followers
        statements_args = [
            (follower, post_id, author_username, post_text, media_url, media_type, location)
            for follower in followers_list
        ]
        
        if not statements_args:
            return
            
        # Launch the execute directly on the list created before
        results = execute_concurrent_with_args(self.session, self.insert_feed, statements_args)
        return results