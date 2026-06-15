import os
import hashlib
import uuid
import random
from faker import Faker
from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args

class DBLogic:
    def __init__(self):
        self.IP_ADDRESS = '127.0.0.1'
        self.CQL_PORT = 9042
        self.USER_NUMBER_INIT = 50
        self.PROFILE_PICTURE_SIZES = (1 * 1024, 5 * 1024, 10 * 1024)
        self.PASSWORD_LENGTH = 12
        self.MAX_PROFILE_SIZE = self.PROFILE_PICTURE_SIZES[-1] # Last element
        self.query_logger_enabled = True

        print("Connessione a Cassandra...")

        self.cluster = Cluster([self.IP_ADDRESS], port=self.CQL_PORT)
        self.session = self.cluster.connect()
        self.session.set_keyspace('network_giustino')

        print("Connesso al keyspace\n")

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
    
    def create_user(self, HAS_PHOTO = True, PHOTO_SIZE = None):
        """
        The function generate a random user, if it has a given probability to have 
        a profile photo with k bytes. The function returns all the parameters 
        to create a user, so first_name, last_name, username, email, password_hash, 
        profile_picture. A user this created weights around 
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
        # has a uniform distribution with images weighting 50Kb, 100Kb, 300Kb
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

        return first_name, last_name, username, email, password_hash, profile_picture

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
        a possible real scenario and the initialization function
        must be used only once. It returns how many users, posts 
        and feed rows has inserted.
        """
        if user_number is None:
            user_number = self.USER_NUMBER_INIT

        previous_logger_state = self.query_logger_enabled
        self.query_logger_enabled = False

        usernames = []

        print(f"Data generation for {user_number} users...")
        user_args_list = []
        print("User insertion in progress ...")
        for i in range(user_number):
            first_name, last_name, username, email, password_hash, profile_picture = self.create_user()

            # For inserting a large number of users, is needed to use the 
            # async call, instead python would be waiting for the rrt of the call every .execute
            user_args_list.append((username, email, password_hash, first_name, last_name, 
                                   profile_picture))
            usernames.append(username)
            
        # Concurrent esecution
        results_users = execute_concurrent_with_args(
            self.session, self.insert_user, user_args_list, concurrency=10
        )
        inserted_users = len(results_users)

        # Steps to create the posts (distribution described in post_count_for_user)
        print("Generating posts and feed ...")
        post_args_list = []
        feed_args_list = []
        for user_index, username in enumerate(usernames):
            post_count = self.post_count_for_user(user_index)

            for post_index in range(post_count):
                post_id = uuid.uuid1()
                post_text = self.fake.sentence(nb_words=12)

                if post_index % 2 == 0:
                    media_url = None
                    media_type = None
                else:
                    media_url = self.fake.url()
                    media_type = "image"

                location = self.fake.city()

                # Store the posts
                post_args_list.append((username, post_id, post_text, media_url, media_type, location))

                # Insert the posts in the feed for a small group (max 3) of viewer
                for offset in range(min(3, len(usernames))):
                    viewer_username = usernames[(user_index + offset) % len(usernames)]
                    feed_args_list.append((viewer_username, post_id, username, post_text, media_url, media_type, location))

        # Concurrent esecution for posts
        print(f"Inserting {len(post_args_list)} post...")
        results_posts = execute_concurrent_with_args(
            self.session, self.insert_post, post_args_list, concurrency=10
        )
        inserted_posts = len(results_posts)

        # Concurrent esecution for feed
        print(f"Inserting {len(feed_args_list)} rows of home feed...")
        results_feed = execute_concurrent_with_args(
            self.session, self.insert_feed, feed_args_list, concurrency=10
        )
        inserted_feed_rows = len(results_feed)

        self.query_logger_enabled = previous_logger_state

        return {
            "users": inserted_users,
            "posts": inserted_posts,
            "feed_rows": inserted_feed_rows,
        }

    def insert_one_user(self, photo_size = None):
        """
        The function insert a single random user in the database, calling create_user and using a simple execute
        """
        if photo_size is not None:
            first_name, last_name, username, email, password_hash, profile_picture = self.create_user(HAS_PHOTO=True, PHOTO_SIZE=photo_size)
        else:
            first_name, last_name, username, email, password_hash, profile_picture = self.create_user()

        self.session.execute(self.insert_user, (username, email, password_hash, 
                                                first_name, last_name, profile_picture))
    
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
                    first_name, last_name, username, email, password_hash, profile_picture = self.create_user(HAS_PHOTO=True, PHOTO_SIZE=photo_size)
                else:
                    first_name, last_name, username, email, password_hash, profile_picture = self.create_user()
                
                # Append params matching our prepared statement structure
                user_args_list.append((username, email, password_hash, first_name, last_name, profile_picture))
            
            # Execute concurrently with an optimized driver execution pool 
            execute_concurrent_with_args(self.session, self.insert_user, user_args_list, concurrency=16)