#!/bin/bash

##############################################
#         RDS minikube development
#
# This script will help you setup a minikube 
# for development of RDS ports
#
# The script will execute all nessecary steps
# to get minikube running and deploy according
# to the values.yaml in the local
# folder.
#
# Simply comment out the steps you want to skip.
##############################################

echo "######## Setting up minikube ##########"

echo "#######################################"
echo "Set driver to docker"
minikube config set driver docker

echo "#######################################"
echo "start with a new minikube cluster"

echo "#######################################"
echo "Delete the minikube cluster"
minikube delete

echo "#######################################"
echo "Start up a new minikube cluster with kubernetes version 1.23.0"
minikube start --driver=docker --kubernetes-version=v1.26.1 --memory=3g --mount-string="/home/dave/Projects/data-retriever:/RRDS" --mount

echo "#######################################"
echo "Enable the ingress addon"
minikube addons enable ingress

echo "#######################################"
echo "create namespace surf-rdc in the cluster"
kubectl create ns surf-rdc
kubectl create ns surf-rdc-demo
kubectl create ns surf-rdc-algosoc
kubectl create ns surf-rdc-tst-test
kubectl create ns surf-rdc-local-nc

echo "#######################################"
echo "Set docker environment to that of minikube, so we can build images directly available in minikube"
eval $(minikube -p minikube docker-env)

echo "#######################################"
echo "Build the surfresearchdataconnector image to local/surfresearchdataconnector"
cd ..
docker build -f dockerfile -t local/surfresearchdataconnector:latest .
cd local

echo "#######################################"
echo "create ssl cert for local-srdr-rd-app-acc.data.surfsara.nl"
echo "Change the script to set your domain."
rm -Rf cert
mkdir cert
cd cert

openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout tls.key -out tls.crt -subj "/CN=local-srdr-rd-app-acc.data.surfsara.nl"
kubectl create secret -n surf-rdc tls localdomain-reversed-tls --key="tls.key" --cert="tls.crt"
kubectl get secret -n surf-rdc localdomain-reversed-tls -o yaml

openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout demo-tls.key -out demo-tls.crt -subj "/CN=demo-srdr-rd-app-acc.data.surfsara.nl"
kubectl create secret -n surf-rdc-demo tls demodomain-reversed-tls --key="demo-tls.key" --cert="demo-tls.crt"
kubectl get secret -n surf-rdc-demo demodomain-reversed-tls -o yaml

openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout algosoc-tls.key -out algosoc-tls.crt -subj "/CN=algosoc-srdc-rd-app-local.data.surfsara.nl"
kubectl create secret -n surf-rdc-algosoc tls algosocdomain-reversed-tls --key="algosoc-tls.key" --cert="algosoc-tls.crt"
kubectl get secret -n surf-rdc-algosoc algosocdomain-reversed-tls -o yaml

openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout tst-test-tls.key -out tst-test-tls.crt -subj "/CN=local-srdc-test-rd-app-acc.data.surfsara.nl"
kubectl create secret -n surf-rdc-tst-test tls tst-testdomain-reversed-tls --key="tst-test-tls.key" --cert="tst-test-tls.crt"
kubectl get secret -n surf-rdc-tst-test tst-testdomain-reversed-tls -o yaml

openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout local-nc-tls.key -out local-nc-tls.crt -subj "/CN=local-nc-srdc.data.surfsara.nl"
kubectl create secret -n surf-rdc-local-nc tls tst-localnc-reversed-tls --key="local-nc-tls.key" --cert="local-nc-tls.crt"
kubectl get secret -n surf-rdc-local-nc tst-localnc-reversed-tls -o yaml

cd ..
rm -Rf cert


echo "start srdc redis"
echo "#######################################"

cd ./srdc-redis
bash build-all-dependencies-with-helm.sh
helm upgrade -n surf-rdc redis-master ./charts/all/ -i --values values.yaml
cd ..


echo "#######################################"
echo "run helm install"
helm install -n surf-rdc surfresearchdataconnector local-surf-rdc-chart/ --values local-surf-rdc-chart/values-aperture.yaml
helm install -n surf-rdc-demo surfresearchdataconnector local-surf-rdc-chart/ --values local-surf-rdc-chart/values-demo.yaml
helm install -n surf-rdc-algosoc surfresearchdataconnector local-surf-rdc-chart/ --values local-surf-rdc-chart/values-algosoc.yaml
helm install -n surf-rdc-tst-test surfresearchdataconnector local-surf-rdc-chart/ --values local-surf-rdc-chart/values-tst-test.yaml
helm install -n surf-rdc-local-nc surfresearchdataconnector local-surf-rdc-chart/ --values local-surf-rdc-chart/values-local-nc.yaml

# echo "#######################################"
# echo "run helm upgrade"
# helm upgrade -n surf-rdc surfresearchdataconnector local-surf-rdc-chart/ --values local-surf-rdc-chart/values-aperture.yaml
# helm upgrade -n surf-rdc-demo surfresearchdataconnector local-surf-rdc-chart/ --values local-surf-rdc-chart/values-demo.yaml
# helm upgrade -n surf-rdc-algosoc surfresearchdataconnector local-surf-rdc-chart/ --values local-surf-rdc-chart/values-algosoc.yaml
# helm upgrade -n surf-rdc-tst-test surfresearchdataconnector local-surf-rdc-chart/ --values local-surf-rdc-chart/values-tst-test.yaml
# helm upgrade -n surf-rdc-local-nc surfresearchdataconnector local-surf-rdc-chart/ --values local-surf-rdc-chart/values-local-nc.yaml

# echo "start nextcloud"
# echo "#######################################"

# cd ./nextcloud-minikube
# kubectl create ns nextcloud
# bash build-all-dependencies-with-helm.sh
# helm upgrade -n nextcloud nxkube ./charts/all/ -i --values values.yaml
# cd ..

echo "#######################################"
echo "See cluster status"
echo "kubectl get po -A"
kubectl get po -A

echo "#######################################"
echo "Ingress has been setup like this:"
kubectl get ingress -A

echo "#######################################"
echo "Set the following in /etc/hosts file:"
echo "$(minikube ip)     <your rds-web domain>"