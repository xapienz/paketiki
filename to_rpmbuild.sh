#!/bin/sh
source ./common.sh $*

prepare_source() {
    pushd "$WORKDIR"
    VERSION=$(jq -r ".version" pkspec.json)
    mkdir -p ~/rpmbuild/SOURCES/
    tar czf ~/rpmbuild/SOURCES/$PACKAGE-$VERSION.tar.gz --transform "s/^./$PACKAGE-$VERSION/" .
    popd
}

build_package() {
    pushd "$WORKDIR"
    rpmbuild -bb pkspec.spec
    popd
}

prepare_source
build_package
