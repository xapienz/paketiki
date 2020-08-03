FROM fedora:32
RUN dnf install -y rpm-build rpmdevtools git autoconf libtool make wget pacman jq dnf-plugins-core
ARG PACKAGE

RUN useradd pktk
RUN mkdir -p /paketiki
RUN chown pktk /paketiki

USER pktk
WORKDIR /paketiki

COPY common.sh .

COPY from_pkgbuild_prepare.sh .
RUN ./from_pkgbuild_prepare.sh $PACKAGE

COPY pktk.py .
COPY pkgbuild_mapping.json .
COPY from_pkgbuild.sh .
RUN ./from_pkgbuild.sh $PACKAGE

USER root
COPY to_rpmbuild_prepare.sh .
RUN ./to_rpmbuild_prepare.sh $PACKAGE

USER pktk
COPY to_rpmbuild.sh .
RUN ./to_rpmbuild.sh $PACKAGE

USER root
