#!/bin/sh
sudo docker run -it --entrypoint /bin/bash -v "out:/paketiki/out" pktk_$1
