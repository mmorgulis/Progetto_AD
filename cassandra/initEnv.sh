#!/bin/bash

echo "Starting Cassandra cluster (all 5 nodes)..."
docker compose up -d

echo "Waiting for cassandra-node5 to be healthy (ensuring full topology is up)..."
until [ "$(docker inspect --format='{{.State.Health.Status}}' cassandra-node5)" == "healthy" ]; do
    sleep 2
done

echo "Injecting schema.cql..."
docker exec -i cassandra-node1 cqlsh < schema.cql 2>/dev/null

echo "======================================================================"
echo " Environment ready: now you can run the workloads (e.g. python3 workloadWriteRead.py)"
echo "======================================================================"