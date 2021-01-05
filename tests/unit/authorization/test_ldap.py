from overhave.entities.authorization.manager import LDAPAuthenticator
from tests.unit.authorization.conftest import TEST_LDAP_GROUPS


class TestLdapAuthenticator:
    def test_get_user_groups(self, test_ldap_authenticator: LDAPAuthenticator) -> None:
        assert test_ldap_authenticator.get_user_groups("kek", "lol") == TEST_LDAP_GROUPS
