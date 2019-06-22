# rr-firebase
Roony tool for firebase

## Install
```
git clone https://github.com/robot-ronny/rr-firebase.git

cd rr-firebase

sudo pip3 install -e .
```

Parameter `-e` creates symlinks so you can edit original files.

## Service enable
```
pm2 --interpreter "python3" start rr-firebase -- --firebase robot-ronny --credentials s/home/pi/rr-firebase/robot-ronny-firebase-adminsdk-9l8ve-7c189e1908.json

pm2 save
```

## Usage
```
rr-firebase --help
```
