FROM fedora:32
RUN dnf install -y rpm-build rpmdevtools git autoconf libtool make wget

RUN useradd rpmbuild
RUN mkdir -p /paketiki
RUN chown rpmbuild /paketiki

USER rpmbuild
WORKDIR /paketiki

COPY prepare_source.sh .
RUN ./prepare_source.sh

COPY pktk.py .
COPY pkgbuild_mapping.json .
RUN ./pktk.py PKGBUILD out
RUN rpmbuild -bb out.spec

USER root
