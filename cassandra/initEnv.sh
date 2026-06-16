#!/bin/bash

echo "Starting Cassandra cluster (all nodes)..."
docker compose up -d

echo "Waiting for cassandra-node3 to be healthy (ensuring full topology is up)..."
until [ "$(docker inspect --format='{{.State.Health.Status}}' cassandra-node3)" == "healthy" ]; do
    sleep 2
done

echo "Injecting schema.cql..."
docker exec -i cassandra-node1 cqlsh < schema.cql 2>/dev/null

echo "======================================================================"
echo " Environment ready: now you can run the workloads (e.g. python3 workloadWriteRead.py)"
echo "======================================================================"