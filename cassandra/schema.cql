-- Keyspace creation with RF = 3 and SimpleStrategy (ignores datacenter/rack factors)
CREATE KEYSPACE IF NOT EXISTS network_giustino 
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};

USE network_giustino;

-- Users table (Query: profile view / login)
CREATE TABLE IF NOT EXISTS users (
    username text,
    email text,
    password_hash text,
    first_name text,
    last_name text,
    profile_picture blob, -- since it is small and compressed, store it directly
    PRIMARY KEY (username)
    -- we expect to search users by name
);

-- Posts table (Query: "create a post" + "show posts in the author's profile")
CREATE TABLE IF NOT EXISTS posts_by_user (
    username text,
    post_id timeuuid,
    post_text text, -- required text (Twitter-style)
    media_url text, -- optional photo/video, always with fake links
    media_type text,
    location text,
    PRIMARY KEY (username, post_id)
) WITH CLUSTERING ORDER BY (post_id DESC);
-- media_type is validated by the application layer

-- Home feed table (Query: show the followers' pre-sorted feed)
CREATE TABLE IF NOT EXISTS home_feed (
    viewer_username text,
    post_id timeuuid,
    author_username text,
    post_text text,
    media_url text,
    media_type text,
    location text,
    PRIMARY KEY (viewer_username, post_id)
) WITH CLUSTERING ORDER BY (post_id DESC);
