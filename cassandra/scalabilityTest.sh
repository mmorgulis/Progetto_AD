#!/bin/bash

# Shell script for geometric Cassandra scalability testing (1 -> 2 -> 4 Nodes).
# Runs the benchmark inside the Docker network to enable Token-Aware Routing.

# Ensure a completely clean state by removing existing containers and volumes
docker compose down -v

# -------------------------------------------------------------------------
# PHASE 1: 1 ACTIVE NODE
# -------------------------------------------------------------------------
echo "Starting Phase 1: 1 Active Node"
docker compose up -d cassandra-node1

echo "Waiting for cassandra-node1 to be healthy..."
until [ "$(docker inspect --format='{{.State.Health.Status}}' cassandra-node1)" == "healthy" ]; do
    sleep 2
done

docker exec -i cassandra-node1 cqlsh < schema.cql 2>/dev/null
docker exec -i cassandra-node1 cqlsh -e "ALTER KEYSPACE network_giustino WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};" 2>/dev/null
sleep 5

echo "Running benchmark against 1 node..."
docker run --rm \
  --network=cassandra_default \
  -v "$(pwd)":/app -w /app \
  -e CASSANDRA_HOSTS="cassandra-node1" \
  python:3.10-slim sh -c "pip install cassandra-driver faker >/dev/null && python3 workloadStressTest.py" > testScalability_1_node.txt

docker compose down -v

# -------------------------------------------------------------------------
# PHASE 2: 2 ACTIVE NODES
# -------------------------------------------------------------------------
echo "Starting Phase 2: 2 Active Nodes"
docker compose up -d cassandra-node1 cassandra-node2

echo "Waiting for cassandra-node2 to be healthy..."
until [ "$(docker inspect --format='{{.State.Health.Status}}' cassandra-node2)" == "healthy" ]; do
    sleep 2
done

docker exec -i cassandra-node1 cqlsh < schema.cql 2>/dev/null
docker exec -i cassandra-node1 cqlsh -e "ALTER KEYSPACE network_giustino WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};" 2>/dev/null
sleep 5

echo "Running benchmark with 2 nodes..."
docker run --rm \
  --network=cassandra_default \
  -v "$(pwd)":/app -w /app \
  -e CASSANDRA_HOSTS="cassandra-node1,cassandra-node2" \
  python:3.10-slim sh -c "pip install cassandra-driver faker >/dev/null && python3 workloadStressTest.py" > testScalability_2_nodes.txt

docker compose down -v

# -------------------------------------------------------------------------
# PHASE 3: 4 ACTIVE NODES
# -------------------------------------------------------------------------
echo "Starting Phase 3: 4 Active Nodes"
docker compose up -d cassandra-node1 cassandra-node2 cassandra-node3 cassandra-node4

echo "Waiting for cassandra-node4 to be healthy..."
until [ "$(docker inspect --format='{{.State.Health.Status}}' cassandra-node4)" == "healthy" ]; do
    sleep 2
done

docker exec -i cassandra-node1 cqlsh < schema.cql 2>/dev/null
docker exec -i cassandra-node1 cqlsh -e "ALTER KEYSPACE network_giustino WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};" 2>/dev/null
sleep 5

echo "Running benchmark with 4 nodes..."
docker run --rm \
  --network=cassandra_default \
  -v "$(pwd)":/app -w /app \
  -e CASSANDRA_HOSTS="cassandra-node1,cassandra-node2,cassandra-node3,cassandra-node4" \
  python:3.10-slim sh -c "pip install cassandra-driver faker >/dev/null && python3 workloadStressTest.py" > testScalability_4_nodes.txt

docker compose down -v

echo "Scalability benchmarks (1, 2, 4 nodes) completed successfully."

# Restore the full topology
docker compose up -d 
docker exec -i cassandra-node1 cqlsh < schema.cql 2>/dev/null