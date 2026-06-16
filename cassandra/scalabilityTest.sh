#!/bin/bash

# Shell script for distributed Cassandra scalability testing.
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

# Set RF = 1
docker exec -i cassandra-node1 cqlsh -e "ALTER KEYSPACE network_giustino WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};" 2>/dev/null
sleep 5

echo "Running benchmark against 1 node..."
docker run --rm \
  --network=cassandra_default \
  -v "$(pwd)":/app -w /app \
  -e CASSANDRA_HOSTS="cassandra-node1" \
  python:3.10-slim sh -c "pip install cassandra-driver faker >/dev/null && python3 workloadWriteRead.py" > linear_1_node.txt

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

# Set RF = 1
docker exec -i cassandra-node1 cqlsh -e "ALTER KEYSPACE network_giustino WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};" 2>/dev/null
sleep 5

echo "Running benchmark with 2 nodes..."
docker run --rm \
  --network=cassandra_default \
  -v "$(pwd)":/app -w /app \
  -e CASSANDRA_HOSTS="cassandra-node1,cassandra-node2" \
  python:3.10-slim sh -c "pip install cassandra-driver faker >/dev/null && python3 workloadWriteRead.py" > linear_2_nodes.txt

docker compose down -v

# -------------------------------------------------------------------------
# PHASE 3: 3 ACTIVE NODES
# -------------------------------------------------------------------------
echo "Starting Phase 3: 3 Active Nodes"
docker compose up -d

echo "Waiting for cassandra-node3 to be healthy..."
until [ "$(docker inspect --format='{{.State.Health.Status}}' cassandra-node3)" == "healthy" ]; do
    sleep 2
done

echo "Injecting schema for Phase 3..."
docker exec -i cassandra-node1 cqlsh < schema.cql 2>/dev/null

# Set RF = 1
docker exec -i cassandra-node1 cqlsh -e "ALTER KEYSPACE network_giustino WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};" 2>/dev/null
sleep 5

echo "Running benchmark with 3 nodes..."
docker run --rm \
  --network=cassandra_default \
  -v "$(pwd)":/app -w /app \
  -e CASSANDRA_HOSTS="cassandra-node1,cassandra-node2,cassandra-node3" \
  python:3.10-slim sh -c "pip install cassandra-driver faker >/dev/null && python3 workloadWriteRead.py" > linear_3_nodes.txt

docker compose down -v

echo "Scalability benchmarks completed successfully."