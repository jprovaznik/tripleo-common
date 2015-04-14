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

import collections
import mock

from tripleo_common import scale
from tripleo_common.tests import base


def mock_plan():
    plan = mock.Mock()
    plan.uuid = '5'
    plan.name = 'My Plan'
    plan.parameters = []
    plan.parameters.append({'name': 'compute-1::count', 'value': '2'})
    plan.to_dict.return_value = {
        'uuid': 5,
        'name': 'My Plan',
        'parameters': plan.parameters,
    }
    return plan


class ScaleManagerTest(base.TestCase):

    def setUp(self):
        super(ScaleManagerTest, self).setUp()
        self.image = collections.namedtuple('image', ['id'])

    @mock.patch('tuskarclient.common.utils.find_resource')
    def test_scaleup(self, mock_find_resource):
        mock_find_resource.return_value = mock_plan()
        heatclient = mock.MagicMock()
        tuskarclient = mock.MagicMock()
        tuskarclient.plans.patch.return_value = mock_plan()
        tuskarclient.plans.templates.return_value = {
            'plan.yaml': '',
            'environment.yaml': '',
            'puppet/manifests/file.yaml': 'file',
        }
        manager = scale.ScaleManager(tuskarclient=tuskarclient,
                                     heatclient=heatclient, stack_id='stack',
                                     plan_id='plan')
        manager.scaleup(role='compute-1', num=2)
        tuskarclient.plans.patch.assert_called_once_with(
            '5', [{'name': 'compute-1::count', 'value': 2}])
        heatclient.stacks.update.assert_called_once_with(
            'stack', template='', environment='',
            files={'manifests/file.yaml': 'file'})
