#!/bin/bash
bash build-all-dependencies-with-helm.sh
helm upgrade -n surf-rdc redis-master ./charts/all/ -i --values values.yaml
