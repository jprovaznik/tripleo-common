# Copyright 2015 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from tripleo_common.tests import base
from tripleo_common.utils import clients


class ClientsTest(base.TestCase):
    @mock.patch('keystoneclient.session.Session')
    @mock.patch('keystoneclient.auth.identity.v2.Password')
    @mock.patch('heatclient.client.Client')
    def test_get_heat_client(self, client_mock, password_mock, session_mock):
        clients.get_heat_client('username', 'password', 'tenant_name',
                                'auth_url')
        password_mock.assert_called_once_with(auth_url='auth_url',
                                              username='username',
                                              password='password',
                                              tenant_name='tenant_name')
        session_mock.assert_called_once_with(auth=password_mock.return_value)
        session_mock.return_value.get_endpoint.assert_called_once_with(
            service_type='orchestration', interface='public',
            region_name='regionOne')
        client_mock.assert_called_once_with(
            '1', session_mock.return_value.get_endpoint.return_value,
            username='username', password='password',
            session=session_mock.return_value, tenant_name='tenant_name',
            auth=password_mock.return_value, auth_url='auth_url',
            include_pass=False, ca_cert=None)
