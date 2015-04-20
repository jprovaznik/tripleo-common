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

from tripleo_common import stack_update
from tripleo_common.tests import base


class StackUpdateManagerTest(base.TestCase):

    def setUp(self):
        super(StackUpdateManagerTest, self).setUp()
        self.heatclient = mock.MagicMock()
        self.stack = mock.MagicMock(id='123', status='IN_PROGRESS',
                                    stack_name='stack')
        self.heatclient.stacks.get.return_value = self.stack
        events = [
            mock.MagicMock(
                event_time='2015-03-25T09:15:04Z',
                resource_name='Controller-0',
                resource_status='CREATE_IN_PROGRESS',
                resource_status_reason='UPDATE paused until Hook pre-update '
                                       'is cleared'),
            mock.MagicMock(
                event_time='2015-03-25T09:15:02Z',
                resource_name='Controller-1',
                resource_status='CREATE_COMPLETE',
                resource_status_reason=''),
        ]
        self.heatclient.resources.list.return_value = [
            mock.MagicMock(
                links=[{'rel': 'stack',
                        'href': 'http://192.0.2.1:8004/v1/'
                                'a959ac7d6a4a475daf2428df315c41ef/'
                                'stacks/overcloud/123'}],
                logical_resource_id='logical_id'
            )
        ]
        self.heatclient.events.list.return_value = events
        self.stack_update_manager = stack_update.StackUpdateManager(
            self.heatclient, self.stack, 'pre-update')

    def test_get_status(self):
        status, resources = self.stack_update_manager.get_status()
        self.heatclient.events.list.assert_called_once_with(
            stack_id='123', resource_name='logical_id')
        self.assertEqual('WAITING', status)

    def test_clear_breakpoint(self):
        self.stack_update_manager.clear_breakpoint('overcloud')
        self.heatclient.resources.signal.assert_called_once_with(
            stack_id='123',
            resource_name='logical_id',
            data={'unset_hook': 'pre-update'})

    def test_cancel(self):
        self.stack_update_manager.cancel()
        self.heatclient.actions.cancel_update.assert_called_once_with('123')
        self.heatclient.resources.signal.assert_called_once_with(
            stack_id='123',
            resource_name='logical_id',
            data={'unset_hook': 'pre-update'})
