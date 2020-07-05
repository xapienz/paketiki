Name: curl-git
Version: 7.56.0.55.g4440b6ad5
Release: 1
Summary: 'A URL retrieval utility and library'
License: MIT
BuildRequires: git
Source: curl-git-7.56.0.55.g4440b6ad5.tar.gz

%description
'A URL retrieval utility and library'

%build
{ 
    cd curl;
    ./buildconf;
    ./configure --prefix=/usr --mandir=/usr/share/man --disable-ldap --disable-ldaps --enable-ipv6 --enable-manual --enable-versioned-symbols --enable-threaded-resolver --with-gssapi --with-random=/dev/urandom --with-ca-bundle=/etc/ssl/certs/ca-certificates.crt;
    make
}

%install
{ 
    cd curl;
    make DESTDIR="$pkgdir" install;
    install -Dm644 COPYING "$pkgdir/usr/share/licenses/$pkgname/COPYING"
}
