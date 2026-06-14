import uuid
from enum import Enum
from cassandra.cluster import Cluster
from cassandra import ConsistencyLevel
from cassandra.driver import QueryLogger

# Definizione dell'Enum per bloccare i media non validi a livello applicativo
class MediaType(Enum):
    FOTO = "foto"
    VIDEO = "video"
    NONE = "none"

def run_social_test():
    # Connessione al cluster locale
    print("Connessione al cluster Cassandra in corso...")
    cluster = Cluster(['127.0.0.1'], port=9042)
    session = cluster.connect()
    
    # Selezione del Keyspace corretto
    session.set_keyspace('network_giustino')
    print("=== Connessione stabilita con il keyspace 'network_giustino' ===\n")

    # Ottimizzano le performance su Cassandra ed evitano il parsing della stringa CQL a ogni insert
    insert_user_stmt = session.prepare("""
        INSERT INTO users (username, email, password_hash, nome, cognome, foto_profilo)
        VALUES (?, ?, ?, ?, ?, ?)
    """)

    insert_post_stmt = session.prepare("""
        INSERT INTO posts_by_user (username, post_id, testo, media_url, media_type, luogo)
        VALUES (?, ?, ?, ?, ?, ?)
    """)

    insert_feed_stmt = session.prepare("""
        INSERT INTO home_feed (viewer_username, post_id, author_username, testo, media_url, media_type, luogo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """)

    # REGISTRAZIONE UTENTE (Con gestione del BLOB)
    print("1. Creazione di un utente con foto profilo compressa...")
    
    username_test = "fabio_col"
    # Nel codice reale sarebbe tipo: with open("avatar.jpg", "rb") as f: foto_bytes = f.read()
    finti_bytes_foto = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10' 

    session.execute(insert_user_stmt, (
        username_test, 
        "fabio@unimib.it", 
        "hash_secure_password_123", 
        "Fabio", 
        "Colonetti", 
        finti_bytes_foto
    ))
    
    # Creiamo anche un follower per testare la Home Feed
    session.execute(insert_user_stmt, ("andrea_col", "andrea@unimib.it", "hash_pass", "Andrea", "Coldani", None))
    print("[OK] Utenti creati sul database.\n")

    # PUBBLICAZIONE POST (Con validazione Enum e Scrittura Doppia)
    print("2. Pubblicazione di un nuovo post (Write-Intensive Pattern)...")
    
    autore = "fabio_col"
    follower = "andrea_col"
    
    # ID unico temporale generato via hardware/time da Python (Mappa il TIMEUUID di Cassandra)
    id_post = uuid.uuid1() 
    testo_post = "Sviluppando il backend in Python per il progetto di AD! #Cassandra #Docker"
    url_media = "https://storage.cloud.it/media/vlog_01.mp4"
    
    tipo_media_scelto = MediaType.VIDEO 

    # Luogo opzionale
    geolocalizzazione = "U14 Abacus, Milano"

    # SCRITTURA 1: Inserimento nella bacheca dell'autore
    session.execute(insert_post_stmt, (
        autore, 
        id_post, 
        testo_post, 
        url_media, 
        tipo_media_scelto.value, # Estraiamo la stringa ("video") per il DB
        geolocalizzazione
    ))
    print(f" -> [Scrittura 1/2] Salvato nel profilo di: {autore}")

    # SCRITTURA 2: Fan-out immediato nella Home del follower (Inclusi i campi denormalizzati)
    session.execute(insert_feed_stmt, (
        follower, 
        id_post, 
        autore, 
        testo_post, 
        url_media, 
        tipo_media_scelto.value, 
        geolocalizzazione
    ))
    print(f" -> [Scrittura 2/2] Copiato direttamente nel feed di: {follower}")
    print("[OK] Post pubblicato globalmente.\n")

    # VERIFICA LETTURE
    print("3. Simulazione lettura dal punto di vista del follower...")
    
    # Il backend interroga solo la tabella home_feed filtrando per Partition Key
    query_bacheca = f"SELECT author_username, testo, media_type, luogo FROM home_feed WHERE viewer_username = '{follower}'"
    rows = session.execute(query_bacheca)
    
    print(f"\n--- HOME FEED DI @{follower} ---")
    for r in rows:
        print(f"Da: @{r.author_username} | Posizione: {r.luogo}")
        print(f"Contenuto: {r.testo}")
        print(f"Tipo Media allegato: [{r.media_type.upper()}]")
        print("-" * 40)

    # Chiudiamo la sessione in modo pulito
    cluster.shutdown()
    print("\n=== Test completato. Connessioni chiuse ===")

if __name__ == "__main__":
    run_social_test()
