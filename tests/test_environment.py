import os

from crm.environment import load_environment
from iniciar import create_environment, verify


def test_private_env_is_created_once_without_overwriting(tmp_path):
    (tmp_path / '.env.example').write_text('CRM_ADMIN_PASSWORD=\nCRM_SESSION_SECRET=\nCRM_WORKER_TOKEN=\nCRM_APIFY_TOKEN=\n')
    assert create_environment(tmp_path)
    target = tmp_path / '.env'
    first = target.read_text()
    values = dict(line.split('=', 1) for line in first.splitlines())
    assert all(len(values[k]) >= 32 for k in ['CRM_ADMIN_PASSWORD', 'CRM_SESSION_SECRET', 'CRM_WORKER_TOKEN'])
    assert values['CRM_APIFY_TOKEN'] == ''
    if os.name == 'posix':
        assert target.stat().st_mode & 0o777 == 0o600
    assert not create_environment(tmp_path)
    assert target.read_text() == first


def test_dotenv_does_not_override_hosting_variables(tmp_path, monkeypatch):
    monkeypatch.setenv('CRM_TEST_SETTING', 'hosting')
    monkeypatch.delenv('CRM_TEST_EXTRA', raising=False)
    path = tmp_path / '.env'
    path.write_text('CRM_TEST_SETTING=file\nCRM_TEST_EXTRA=loaded\n')
    load_environment(path)
    assert os.environ['CRM_TEST_SETTING'] == 'hosting'
    assert os.environ['CRM_TEST_EXTRA'] == 'loaded'
    monkeypatch.delenv('CRM_TEST_EXTRA')


def test_verification_reports_missing_connections_without_credentials(monkeypatch, capsys):
    monkeypatch.setenv('CRM_DATABASE_URL', 'sqlite:///data/crm2.db')
    monkeypatch.setenv('CRM_GMAIL_CLIENT_SECRET', 'test-secret-never-print')
    monkeypatch.delenv('CRM_GMAIL_CLIENT_ID', raising=False)
    monkeypatch.delenv('CRM_GMAIL_REFRESH_TOKEN', raising=False)
    assert not verify()
    output = capsys.readouterr().out
    assert 'Supabase não conectado' in output
    assert 'CRM_GMAIL_CLIENT_ID' in output
    assert 'test-secret-never-print' not in output
