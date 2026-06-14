import os
import bcrypt
from faker import Faker
from cassandra.cluster import Cluster
#from cassandra.query import QueryLogger

class DBLogic:

    def __init__(self):
        self.IP_ADDRESS = '127.0.0.1'
        self.CQL_PORT = 9042
        self.USER_NUMBER_INIT = 5000
        self.PHOTO_SIZE = 256
        self.PASSWORD_LENGTH = 12

        print("Connessione a Cassandra...")

        self.cluster = Cluster([self.IP_ADDRESS], port=self.CQL_PORT)
        self.session = self.cluster.connect()
        self.session.set_keyspace('network_giustino')

        print("Connesso al keyspace\n")

        # Faker singleton
        self.fake = Faker(['it_IT', 'en_US', 'ja_JP'])

        # Prepared statements
        self.insert_user = self.session.prepare("""
            INSERT INTO users (username, email, password_hash, nome, cognome, foto_profilo)
            VALUES (?, ?, ?, ?, ?, ?)
        """)

        # Debugging delle query
        #self.query_logger = QueryLogger()
        #self.session.client_config.query_logger = self.query_logger


    def initialization(self, user_number=None):
        if user_number is None:
            user_number = self.USER_NUMBER_INIT

        for _ in range(user_number):

            first_name = self.fake.first_name()
            last_name = self.fake.last_name()

            username = f"{first_name.lower()}.{last_name.lower()}"
            email = f"{username}@{self.fake.free_email_domain()}"

            password = self.fake.password(length=self.PASSWORD_LENGTH)
            password_hash = bcrypt.hashpw(
                password.encode(),
                bcrypt.gensalt()
            ).decode()

            profile_picture = os.urandom(self.PHOTO_SIZE)

            self.session.execute(self.insert_user, (
                username,
                email,
                password_hash,
                first_name,
                last_name,
                profile_picture
            ))