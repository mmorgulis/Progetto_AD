-- Creazione del Keyspace con RF = 3 e SimpleStrategy (non considero fattori tipo datacenter/rack)
CREATE KEYSPACE IF NOT EXISTS network_giustino 
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};

USE network_giustino;

-- Tabella Utenti (Query: Visualizzazione profilo / Login)
CREATE TABLE IF NOT EXISTS users (
    username text,
    email text,
    password_hash text,
    nome text,
    cognome text,
    foto_profilo blob, -- dato che è piccola e compressa la inserisco direttamente
    PRIMARY KEY (username)
    -- ci aspettiamo di fare ricerche con il nome dell'utente
);

-- Tabella Post (Query: "Posta un post" + "Mostra i post nel profilo dell'autore")
CREATE TABLE IF NOT EXISTS posts_by_user (
    username text,
    post_id timeuuid,
    testo text, -- testo obbligatorio (tipo twitter)
    media_url text, -- facoltativo foto/video sempre con link fittizi
    media_type text,
    luogo text,
    PRIMARY KEY (username, post_id)
) WITH CLUSTERING ORDER BY (post_id DESC);
-- il media_type è verificato dall'application layer

-- Tabella Feed di Home (Query: Mostra la bacheca dei follower pre-ordinata)
CREATE TABLE IF NOT EXISTS home_feed (
    viewer_username text,
    post_id timeuuid,
    author_username text,
    testo text,
    media_url text,
    media_type text,
    luogo text,
    PRIMARY KEY (viewer_username, post_id)
) WITH CLUSTERING ORDER BY (post_id DESC);
