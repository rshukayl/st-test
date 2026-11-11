#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
command -v openssl >/dev/null 2>&1 || { echo 'openssl is required' >&2; exit 1; }
umask 077
mkdir -p certs
if [ -s certs/localhost.key ] && [ -s certs/localhost.crt ]; then
    echo 'Using existing certificate. Remove both files to regenerate.'
    exit 0
fi
if [ -e certs/localhost.key ] || [ -e certs/localhost.crt ]; then
    echo 'Incomplete certificate pair. Remove both files and retry.' >&2
    exit 1
fi
openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 365 \
    -keyout certs/localhost.key \
    -out certs/localhost.crt \
    -subj '/CN=localhost' \
    -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1,IP:::1' \
    -addext 'extendedKeyUsage=serverAuth'
chmod 600 certs/localhost.key
chmod 644 certs/localhost.crt
echo 'Created certs/localhost.crt and certs/localhost.key'
