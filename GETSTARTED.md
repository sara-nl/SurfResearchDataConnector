# Get started
This is a manual for getting started with a minimal configured locally running instance of the SRDC app on minikube.
This is ideal if you quickly want to get the app working with your cloud.

## Install minikube
First install minikube on your system following the instructions from the documentation for your operating system at https://minikube.sigs.k8s.io/docs/start/

## Do a minimal configuration of the app
The minimum configuration we need to do is to set the DRIVE_URL and CLOUD_SERVICE value in the ./local/local-surf-rdc-chart/values.yaml file.
```
# enviroment vars
env:
  - name: DRIVE_URL
    value: https://acc-aperture.data.surfsara.nl
  - name: SRDC_URL
    value: https://local-srdr-rd-app-acc.data.surfsara.nl
  - name: CLOUD_SERVICE
    value: owncloud
```
Here you need to set the value of the DRIVE_URL to the url of your owncloud or nextcloud instance.
Also you want to change the value of CLOUD_SERVICE to nextcloud if your instance is a nextcloud instance.

## Run the script
On linux you can run the minikube.sh script from the local folder. This will launch the app on a minikube cluster and make it available on a locally available url.
```
cd local
sh minikube.sh
```

## Make the app available on a url
After the script has finished running the app can be made available at: https://local-srdr-rd-app-acc.data.surfsara.nl by setting this domain to the minikube ip in your host file on your computer.
You can see the minikube ip by typing in the terminal:
```
minikube ip
```
On linux you can edit the host file here: /etc/hosts.


## Connect the SRDC app to your owncloud or nextcloud
The app will automatically try to connect on the home page. This will fail as we have not configured this in this minimal setup.
To connect manually with username and app password, go to the connect page directly at: https://local-srdr-rd-app-acc.data.surfsara.nl/connect
There you can connect by username and (app) password.
Once connected to your owncloud or nextcloud instance you can connect to the available repositories and start using the app.

## Notes
In order to integrate the app with your cloud application it needs to run on an url with a ssl certificate. This setup mimics this by generating a self-signed certificate for the url that you can make availalble locally by editing your computers host file. The local app can run in firefox which allows the user to accept self signed ssl certificates.