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
minikube start --driver=docker --kubernetes-version=v1.26.1 --memory=3g --mount-string="/home/dave/Projects/github/SurfResearchDataConnector:/RRDS" --mount

echo "#######################################"
echo "Enable the ingress addon"
minikube addons enable ingress

echo "#######################################"
echo "create namespace surf-rdc in the cluster"
kubectl create ns surf-rdc

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