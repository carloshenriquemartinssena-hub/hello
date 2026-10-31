"""Certificado raiz fornecido pelo proprietário, sem desativar TLS."""
import atexit
import os
import ssl
import tempfile
from functools import lru_cache

from .secrets_config import ConfigurationError

_files = []


def _cleanup():
    for path in _files:
        try:
            os.unlink(path)
        except OSError:
            pass


atexit.register(_cleanup)


def certificate_file(pem):
    pem = pem.strip().replace('\\n', '\n') + '\n'
    return _certificate_file(pem)


@lru_cache(maxsize=4)
def _certificate_file(pem):
    if len(pem) > 200000 or 'PRIVATE KEY' in pem or '-----BEGIN CERTIFICATE-----' not in pem:
        raise ConfigurationError('CRM_DATABASE_CA_CERT deve conter apenas o certificado público PEM oficial do Supabase, nunca uma chave privada.')
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cadata=pem)
    except (ssl.SSLError, ValueError):
        raise ConfigurationError('CRM_DATABASE_CA_CERT não é um certificado PEM válido. Copie todo o arquivo oficial, incluindo BEGIN CERTIFICATE e END CERTIFICATE.') from None
    fd, path = tempfile.mkstemp(prefix='crm2-supabase-ca-', suffix='.pem')
    try:
        with os.fdopen(fd, 'w', encoding='ascii') as file:
            file.write(pem)
    except Exception:
        os.unlink(path)
        raise
    _files.append(path)
    return path


def postgres_connect_options():
    options = {'connect_timeout': 10}
    pem = os.getenv('CRM_DATABASE_CA_CERT', '').strip()
    if pem:
        options.update(sslmode='verify-full', sslrootcert=certificate_file(pem))
    return options
