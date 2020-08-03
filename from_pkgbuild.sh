#!/bin/sh
source ./common.sh $*

parse_spec() {
    ./pktk.py "$WORKDIR/PKGBUILD" "$WORKDIR/pkspec"
}

parse_spec
