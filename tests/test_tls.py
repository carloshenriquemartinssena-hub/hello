import os
import ssl
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from crm.secrets_config import ConfigurationError, apply_secrets
from crm.tls import certificate_file, postgres_connect_options


def trusted_test_certificate():
    # Certificado público do trust store do sistema; nenhuma conexão de rede.
    root = ssl.create_default_context().get_ca_certs(binary_form=True)[0]
    return ssl.DER_cert_to_PEM_cert(root)


def test_ca_from_secrets_creates_private_file_and_keeps_full_verification(monkeypatch):
    pem = trusted_test_certificate()
    monkeypatch.delenv('CRM_DATABASE_CA_CERT', raising=False)
    apply_secrets({'CRM_DATABASE_CA_CERT': pem})
    options = postgres_connect_options()
    path = Path(options['sslrootcert'])
    assert options['sslmode'] == 'verify-full'
    assert path.read_text() == pem
    if os.name == 'posix':
        assert path.stat().st_mode & 0o777 == 0o600
    assert certificate_file(pem) == str(path)
    monkeypatch.delenv('CRM_DATABASE_CA_CERT')


@pytest.mark.parametrize('value', ['not-a-certificate', '-----BEGIN PRIVATE KEY-----\nprivate-test-value', '-----BEGIN CERTIFICATE-----\ninvalid\n-----END CERTIFICATE-----'])
def test_invalid_ca_is_rejected_without_disclosing_contents(value, monkeypatch):
    monkeypatch.setenv('CRM_DATABASE_CA_CERT', value)
    with pytest.raises(ConfigurationError) as error:
        postgres_connect_options()
    assert value not in str(error.value)
    assert 'private-test-value' not in str(error.value)


def test_no_ca_preserves_uri_certificate_configuration(monkeypatch):
    monkeypatch.delenv('CRM_DATABASE_CA_CERT', raising=False)
    assert postgres_connect_options() == {'connect_timeout': 10}


def test_custom_ca_is_passed_to_driver_over_system_query(monkeypatch):
    from crm import db
    monkeypatch.setenv('CRM_DATABASE_CA_CERT', trusted_test_certificate())
    monkeypatch.setenv('CRM_ENV', 'production')
    class StopBeforeNetwork(Exception):
        pass
    captured = {}
    def fake_engine(url, **kwargs):
        captured.update(kwargs)
        assert make_url(url).query['sslrootcert'] == 'system'
        raise StopBeforeNetwork
    monkeypatch.setattr(db, 'create_engine', fake_engine)
    with pytest.raises(StopBeforeNetwork):
        db.connect('postgresql://example:test-only@example.invalid/postgres?sslmode=verify-full&sslrootcert=system')
    assert captured['connect_args']['sslmode'] == 'verify-full'
    assert Path(captured['connect_args']['sslrootcert']).is_file()
