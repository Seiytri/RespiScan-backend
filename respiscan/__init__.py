import socket

# Windows IPv6 fallback patch:
# On Windows environments where an unroutable NAT64 IPv6 prefix is advertised,
# non-blocking sockets hang for 40+ seconds or trigger [WinError 10035] WSAEWOULDBLOCK.
# Preferring AF_INET prevents blackholing and speeds up Supabase & external network calls to <10ms.
_orig_getaddrinfo = socket.getaddrinfo

def _ipv4_preferred_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    except Exception:
        return _orig_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = _ipv4_preferred_getaddrinfo

from .celery import app as celery_app

__all__ = ('celery_app',)

