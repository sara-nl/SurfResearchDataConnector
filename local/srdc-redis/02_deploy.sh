#!/bin/bash
bash build-all-dependencies-with-helm.sh
helm upgrade -n srdc-redis surfresearchdataconnector ./charts/all/ -i --values values.yaml
