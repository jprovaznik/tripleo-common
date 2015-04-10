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

import json
import logging
import time
import yaml
import libutils

from tuskarclient.common import utils as tuskarutils

LOG = logging.getLogger(__name__)


class UpdateManager:
    def __init__(self, heatclient, tuskarclient, stack_id, plan_id=None):
        self.tuskarclient = tuskarclient
        self.heatclient = heatclient
        self.stack = heatclient.stacks.get(stack_id)
        self.plan = tuskarutils.find_resource(self.tuskarclient.plans, plan_id)

    def update(self):
        params = libutils.heat_params_from_templates(
            self.tuskarclient.plans.templates(self.plan.uuid))
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        params['parameters'] = {
            'Controller-1::update_timestamp': timestamp,
            'Compute-1::update_timestamp': timestamp,
        }
        env = yaml.load(params['environment'])
        libutils.deep_merge(env, {
            'resource_registry': {
                'resources': {
                    'Controller': {
                        '*': {
                            'update_deployment': {'hooks': 'pre-update'}
                        }
                    }
                }
            }
        })
        params['environment'] = env
        LOG.debug('updating stack: {0}', params)
        self.heatclient.stacks.update(self.stack.id, **params)

    def proceed(self, node=None):
        resources = self._resources_by_state()
        try:
            self._clear_breakpoint(resources['on_breakpoint'].pop())
        except IndexError:
            LOG.error("no more breakpoints")

    def cancel(stack):
        # TODO(jprovazn)
        stack.rollback
        stack.delete

    def get_status(self, verbose=False):
        stack = self.client.stacks.get(self.stack_id)
        # check if any of deployments' child resource has last
        # event indicating that it has reached a breakpoint (this
        # seems to be the only way how to check pre-create breakpoints ATM)
        resources = self._resources_by_state()
        if stack.status == 'IN_PROGRESS':
            if verbose:
                print(resources)
            if resources['on_breakpoint']:
                if resources['in_progress']:
                    status = 'IN_PROGRESS'
                else:
                    status = 'WAITING'
            else:
                status = 'IN_PROGRESS'
        else:
            status = stack.status
        LOG.debug('%s status: %s', stack.stack_name, status)
        return (status, resources)

    def do_interactive_update(self):
        status = None
        while status not in ['COMPLETE', 'FAILED']:
            status, resources = self.get_status()
            if status == 'WAITING':
                print(resources)
                raw_input("Breakpoint reached, continue? Press Enter or C-c:")
                self.proceed()
            time.sleep(1)
        print('update finished with status {0}'.format(status))

    def _clear_breakpoint(self, node_name):
        LOG.debug('clearing breakpoint on %s' % node_name)
        deployment_resource = self.client.resources.get(
            self.stack_id, 'deployments')
        self.client.resources.signal(
            stack_id=deployment_resource.physical_resource_id,
            resource_name=node_name,
            data={'unset_hook': 'pre-create'})

    def _resources_by_state(self):
        resources = {
            'in_progress': [],
            'on_breakpoint': [],
            'completed': [],
        }
        # FIXME: check only CRATE_* states for now
        for ev in self._last_events().items():
            if ev[1].resource_status == 'CREATE_IN_PROGRESS':
                if ev[1].resource_status_reason != ('Paused until the hook '
                                                    'is cleared'):
                    resources['in_progress'].append(ev[0])
                else:
                    resources['on_breakpoint'].append(ev[0])
            else:
                resources['completed'].append(ev[0])
        return resources

    def _last_events(self):
        deployment_resource = self.client.resources.get(
            self.stack_id, 'deployments')
        # 'deployments' resource may not exist right after update
        # stack is created
        if not deployment_resource.physical_resource_id:
            return {}
        last_events = {}
        for ev in self.client.events.list(
                deployment_resource.physical_resource_id):
            last_known_ev = last_events.get(ev.resource_name, None)
            # FIXME: proper datetime comparison
            if not last_known_ev or ev.event_time > last_known_ev.event_time:
                last_events[ev.resource_name] = ev
        return last_events

