# Copyright 2015 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from tripleo_common.tests import base
from tripleo_common import update


class UpdateManagerTest(base.TestCase):

    def setUp(self):
        super(UpdateManagerTest, self).setUp()

    @mock.patch('tuskarclient.common.utils.find_resource')
    def test_update(self, mock_find_resource):
        heatclient = mock.MagicMock()
        tuskarclient = mock.MagicMock()
        heatclient.stacks.get.return_value = mock.MagicMock(
            stack_name='stack', stack_id='stack_id')
        mock_find_resource.return_value = mock.MagicMock(uuid='plan')
        tuskarclient.plans.templates.return_value = {
            'plan.yaml': 'template body',
            'environment.yaml': 'resource_registry: {}\n',
            'puppet/manifests/file.yaml': 'file',
        }
        update.PackageUpdateManager(
            heatclient, tuskarclient, 'stack_id', 'plan').update()
        params = {
            'template': 'template body',
            'environment': {
                'resource_registry': {
                    'resources': {
                        '*': {
                            '*': {
                                'update_deployment': {'hooks': 'pre-update'}
                            }
                        }
                    }
                }
            }
        }
        heatclient.stacks.update.assert_called_one_with('stack_id', params)
