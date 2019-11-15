#!/bin/bash

echo "creating Prometheus datasource in grafana"
curl -X POST http://admin:admin@$(oc get route grafana-route --no-headers | awk '{print $2}')/api/datasources -d @grafana-dashboards/datasource.json --header "Content-Type: application/json"

echo "\nAdding Kafka dashboard"
curl -X POST http://admin:admin@$(oc get route grafana-route --no-headers | awk '{print $2}')/api/dashboards/db -d @grafana-dashboards/strimzi-kafka.json --header "Content-Type: application/json"

echo "\nAdding Zookeeper dashboard"
curl -X POST http://admin:admin@$(oc get route grafana-route --no-headers | awk '{print $2}')/api/dashboards/db -d @grafana-dashboards/strimzi-zookeeper.json --header "Content-Type: application/json"
