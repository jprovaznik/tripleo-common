import mock

from tripleo_common.cmd.utils import _clients as clients
from tripleo_common.tests import base


class CMDClientsTest(base.TestCase):

    @mock.patch.dict('os.environ', {'OS_USERNAME': 'username',
                                    'OS_PASSWORD': 'password',
                                    'OS_TENANT_NAME': 'tenant',
                                    'OS_AUTH_URL': 'auth_url',
                                    'OS_CACERT': 'cacert'})
    def test___get_client_args(self):
        result = clients._get_client_args()
        expected = ("username", "password", "tenant", "auth_url", "cacert")
        self.assertEqual(result, expected)
