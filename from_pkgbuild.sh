#!/bin/sh
source ./common.sh $*

get_spec() {
    git clone https://aur.archlinux.org/$PACKAGE.git --depth=1 "$WORKDIR"
    rm -rf "$WORKDIR/.git"
}

parse_spec() {
    ./pktk.py "$WORKDIR/PKGBUILD" "$WORKDIR/pkspec"
}

generate_source() {
    pushd "$WORKDIR"
    makepkg --verifysource
    for file in *; do
        if [[ -d "$file" ]]; then
            pushd "$file"
            bare=$(git rev-parse --is-bare-repository 2>/dev/null || echo false)
            popd
            if [[ $bare == "true" ]]; then
                mv "$file" "$file-bare"
                git clone -s "$file-bare" "$file"
                rm -rf "$file-bare"
            fi
            rm -rf "$file/.git"
        fi
    done
    popd
}

get_spec
parse_spec
generate_source