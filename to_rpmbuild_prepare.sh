#!/bin/sh
source ./common.sh $*

install_deps() {
    pushd "$WORKDIR"
    DEPENDS="$(jq -r '.rpm_requires[]' pkspec.json)"
    DEPENDS_DEVEL="$(jq -r '.rpm_devel[]' pkspec.json)"

    dnf install -y $DEPENDS
    dnf builddep -y pkspec.spec
    dnf install -y --skip-broken $DEPENDS_DEVEL
    popd
}

install_deps
