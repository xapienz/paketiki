Name: curl-git
Version: 7.56.0.55.g4440b6ad5
Release: 1
Summary: 'A URL retrieval utility and library'
License: MIT
Requires: ca-certificates
Requires: krb5-libs
Requires: libssh2
Requires: openssl
Requires: zlib
Requires: libpsl
Requires: libnghttp2
Provides: curl
Provides: libcurl.so
Conflicts: curl
BuildRequires: git
Source: curl-git-7.56.0.55.g4440b6ad5.tar.gz
%define debug_package %{nil}
%define srcdir %{_builddir}/curl-git-7.56.0.55.g4440b6ad5

%prep
%setup

%description
'A URL retrieval utility and library'

%build
    export pkgdir="%{buildroot}"
    export srcdir="%{srcdir}"
    export _pkgname="%{_pkgname}"
    cd curl;
    ./buildconf;
    ./configure --prefix=/usr --mandir=/usr/share/man --disable-ldap --disable-ldaps --enable-ipv6 --enable-manual --enable-versioned-symbols --enable-threaded-resolver --with-gssapi --with-random=/dev/urandom --with-ca-bundle=/etc/ssl/certs/ca-certificates.crt;
    make

%install
    export pkgdir="%{buildroot}"
    export srcdir="%{srcdir}"
    export _pkgname="%{_pkgname}"
    cd curl;
    make DESTDIR="$pkgdir" install;
    install -Dm644 COPYING "$pkgdir/usr/share/licenses/$pkgname/COPYING"

%files
/*
%exclude %dir /usr/bin
%exclude %dir /usr/lib

