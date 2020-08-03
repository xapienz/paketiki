#!/bin/sh
set -e
mkdir -p out
sudo docker build --build-arg PACKAGE=$1 -t pktk_$1 .
sudo docker run -v "$(pwd)/out:/paketiki/out" pktk_$1 cp -R /home/pktk/rpmbuild/RPMS /paketiki/out
sudo chown -R $(whoami):$(whoami) out
