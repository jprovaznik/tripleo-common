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
        self.stack = self.heatclient.stacks.get(self.stack.id)
        # check if any of deployments' child resource has last
        # event indicating that it has reached a breakpoint (this
        # seems to be the only way how to check pre-create breakpoints ATM)
        resources = self._resources_by_state()
        if self.stack.status == 'IN_PROGRESS':
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
            status = self.stack.status
        LOG.debug('%s status: %s', self.stack.stack_name, status)
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

    def _clear_breakpoint(self, node_ref):
        LOG.debug('clearing breakpoint on %s/%s' % node_ref)
        import pdb;pdb.set_trace()
        self.heatclient.resources.signal(
            stack_id=node_ref[0],
            resource_name=node_ref[1],
            data={'unset_hook': 'pre-update'})

    def _resources_by_state(self):
        resources = {
            'in_progress': [],
            'on_breakpoint': [],
            'completed': [],
        }
        # FIXME: check only CRATE_* states for now
        for ev in self._last_events().items():
            if ev[1].resource_status_reason != ('UPDATE paused until Hook '
                                                'pre-update is cleared'):
                resources['on_breakpoint'].append(ev[0])
            elif ev[1].resource_status == 'UPDATE_IN_PROGRESS':
                resources['in_progress'].append(ev[0])
            else:
                resources['completed'].append(ev[0])
        return resources

    def _last_events(self):
        # 'deployments' resource may not exist right after update
        # stack is created
        #if not deployment_resource.physical_resource_id:
        #    return {}
        last_events = {}
        for res in self.heatclient.resources.list(self.stack.id, nested_depth=2):
            if not res.resource_name == 'update_deployment':
                continue
            ref = (self._resource_stack_id(res), 'update_deployment')
            for ev in self.heatclient.events.list(
                    stack_id=ref[0],
                    resource_name=ref[1]):
                last_ev = last_events.get(ref, None)
                if not last_ev or ev.event_time > last_ev.event_time:
                    last_events[ref] = ev
        return last_events

    def _resource_stack_id(self, res):
        # FIXME (jprovazn): get resource's stack id in a proper way
        link = next(x['href'] for x in res.links if x['rel'] == 'stack')
        return link.rsplit('/', 1)[1]
