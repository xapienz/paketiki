FROM fedora:32
RUN dnf install -y rpm-build rpmdevtools git autoconf libtool make wget

COPY prepare_source.sh .
RUN /prepare_source.sh

COPY pktk.py /paketiki/
RUN /paketiki/pktk.py /paketiki/PKGBUILD /paketiki/out
RUN rpmbuild -bb /paketiki/out.spec
