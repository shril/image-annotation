#!/bin/bash

cd servers/
sudo apt install python3-pip
pip3 install numpy
pip3 install image
pip3 install scikit-image
pip3 install flask
pip3 install flask-login
python3 server1/image-annotation/flask_app.py&
python3 server2/image-annotation/flask_app.py&
python3 server3/image-annotation/flask_app.py&
python3 server4/image-annotation/flask_app.py