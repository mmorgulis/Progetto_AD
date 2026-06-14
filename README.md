# Progetto_AD
## How to run
Il progetto è interamente scritto in Python e richiede 2 librerie esterne:
1. cassandra-driver
2. Faker

Solitamente è consigliato creare una cartella *venv* per contenere le dipendenze esterne, in questo modo:
```
python -m venv .venv
```
E si attiva con:  
**Windows**
```
.venv\Scripts\activate
```
**Linux/macOS**
```
source .venv/bin/activate
```
Successivamente è possibile installare tutte le librerie spostandosi nella cartella */cassandra* con:
```
pip install -r requirements.txt
```
Oppure singolarmente con:
```
pip install <NOME_LIBRERIA>
```

### Guida base per Docker/Cassandra
Invece per eseguire l'effettivo codice relativo a cassandra, è necessario aver installato docker ed eseguire:
```
docker compose up -d
```
Alcuni comandi utili per controllare l'esecuzione sono (su windows omettere "*sudo*"):
1. Per controllare lo stato dei nodi:  
```
sudo docker exec -it cassandra-node1 nodetool status
```  
2. Per verificare la topologia:
```
sudo docker exec -it cassandra-node1 nodetool describecluster
```
3. Se un nodo non dovesse partire correttamente (?N), per farlo ripartire:
```
sudo docker restart cassandra-<nome_nodo>
```
Successivamente per caricare lo schema è necessario eseguire:  
**Windows**
```
Get-Content schema.cql | docker exec -i cassandra-node1 cqlsh
```
**Linux/MacOS**
```
sudo docker exec -i cassandra-node1 cqlsh < schema.cql
```  
Per caricare i dati dello script python:
```
python3 test.py
```  
Infine per testare direttamente della shell cql l'inserimento dei dati:
```
sudo docker exec -it cassandra-node1 cqlsh
```
e inserire delle query cql direttamente nella shell del nodo (es. SELECT username, email, nome, foto_profilo FROM users;)  
Per fermare i container senza cancellare i volumi usare:  
```
sudo docker compose stop
```
Per riavviarli: 
```
sudo docker compose start
```
Per cancellare anche i container:
```
sudo docker compose down
```
Per cancellare anche i container e i volumi associati:
```
sudo docker compose down -v
```



