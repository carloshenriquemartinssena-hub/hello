import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError

from crm.diagnostics import database_diagnostic


class DatabaseError(Exception):
    def __init__(self, text, sqlstate=None):
        super().__init__(text)
        self.sqlstate = sqlstate


@pytest.mark.parametrize('state,text,expected', [
    ('28P01', 'private-test-password', 'DB_AUTH'),
    (None, 'password authentication failed private-test-password', 'DB_AUTH'),
    (None, 'Tenant or user not found private-test-password', 'DB_POOLER'),
    ('42P01', 'private-test-password', 'DB_TABLES'),
    ('42703', 'private-test-password', 'DB_COLUMNS'),
    ('42501', 'private-test-password', 'DB_PERMISSION'),
    (None, 'SSL certificate verify failed private-test-password', 'DB_CERTIFICATE'),
    (None, 'root certificate file not found private-test-password', 'DB_CERTIFICATE'),
    (None, 'could not translate host name private-test-password', 'DB_DNS'),
    (None, 'connection timeout private-test-password', 'DB_TIMEOUT'),
    (None, 'Network is unreachable private-test-password', 'DB_NETWORK'),
    ('53300', 'private-test-password', 'DB_CONNECTION_LIMIT'),
    (None, 'unrecognized private-test-password', 'DB_UNKNOWN'),
])
def test_nested_database_errors_are_specific_and_never_expose_values(state, text, expected):
    cause = DatabaseError(text, state)
    error = OperationalError('SELECT private-test-value', {'password': 'private-test-password'}, cause)
    code, message = database_diagnostic(error)
    assert code == expected
    assert 'private-test-password' not in message
    assert 'private-test-value' not in message
