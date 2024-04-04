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
minikube start --kubernetes-version=v1.23.0 --mount-string="/home/dave/Projects/data-retriever:/RRDS" --mount

echo "#######################################"
echo "Enable the ingress addon"
minikube addons enable ingress

echo "#######################################"
echo "create namespace surf-rdr in the cluster"
kubectl create ns surf-rdr
kubectl create ns surf-rdr-demo

echo "#######################################"
echo "Set docker environment to that of minikube, so we can build images directly available in minikube"
eval $(minikube -p minikube docker-env)

echo "#######################################"
echo "Build the surfresearchdataretriever image to local/surfresearchdataretriever"
cd ..
docker build -f dockerfile -t local/surfresearchdataretriever:latest .
cd local

echo "#######################################"
echo "create ssl cert for local-srdc-rd-app-acc.data.surfsara.nl"
echo "Change the script to set your domain."
rm -Rf cert
mkdir cert
cd cert
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout tls.key -out tls.crt -subj "/CN=local-srdc-rd-app-acc.data.surfsara.nl"
kubectl create secret -n surf-rdr tls localdomain-reversed-tls --key="tls.key" --cert="tls.crt"
kubectl get secret -n surf-rdr localdomain-reversed-tls -o yaml

openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout demo-tls.key -out demo-tls.crt -subj "/CN=demo-srdc-rd-app-acc.data.surfsara.nl"
kubectl create secret -n surf-rdr-demo tls demodomain-reversed-tls --key="demo-tls.key" --cert="demo-tls.crt"
kubectl get secret -n surf-rdr-demo demodomain-reversed-tls -o yaml

cd ..
rm -Rf cert

echo "#######################################"
echo "run helm install"
helm install -n surf-rdr surfresearchdataretriever local-surf-rdr-chart/ --values local-surf-rdr-chart/values-aperture.yaml
helm install -n surf-rdr-demo surfresearchdataretriever local-surf-rdr-chart/ --values local-surf-rdr-chart/values-demo.yaml

echo "#######################################"
echo "See cluster status"
echo "kubectl get po -A"
kubectl get po -A

echo "#######################################"
echo "Ingress has been setup like this:"
kubectl get ingress -n surf-rdr

echo "#######################################"
echo "Set the following in /etc/hosts file:"
echo "$(minikube ip)     <your rds-web domain>"
