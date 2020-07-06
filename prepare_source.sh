#!/bin/bash
set -e
NAME=curl-git-7.56.0.55.g4440b6ad5

mkdir -p /paketiki
wget 'https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=curl-git&id=3251d2670c13e48966638c8129437923ddfa5874' -O /paketiki/PKGBUILD

mkdir $NAME
pushd $NAME
git clone git://github.com/curl/curl.git
cd curl
git checkout 4440b6ad5
rm -rf .git
popd

tar -czvf $NAME.tar.gz $NAME
mkdir -p ~/rpmbuild/SOURCES/
cp $NAME.tar.gz ~/rpmbuild/SOURCES/
