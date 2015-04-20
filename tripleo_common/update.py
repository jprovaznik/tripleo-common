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

import logging
import time
import yaml

from heatclient.common import template_utils
from tripleo_common import libutils
from tuskarclient.common import utils as tuskarutils

LOG = logging.getLogger(__name__)


class UpdateManager(object):
    def __init__(self, heatclient, tuskarclient, stack_id, plan_id):
        self.tuskarclient = tuskarclient
        self.heatclient = heatclient
        self.stack = heatclient.stacks.get(stack_id)
        self.plan = tuskarutils.find_resource(self.tuskarclient.plans, plan_id)

    def update(self):
        params = libutils.heat_params_from_templates(
            self.tuskarclient.plans.templates(self.plan.uuid))
        timestamp = int(time.time())
        params['parameters'] = {
            'Controller-1::update_timestamp': timestamp,
        }
        env = yaml.load(params['environment'])
        template_utils.deep_update(env, {
            'resource_registry': {
                'resources': {
                    '*': {
                        '*': {
                            'update_deployment': {'hooks': 'pre-update'}
                        }
                    }
                }
            }
        })
        params['environment'] = env
        LOG.info('updating stack: {0}', params)
        self.heatclient.stacks.update(self.stack.id, **params)

    def clear_breakpoint(self, ref):
        resources = self._resources_by_state()
        try:
            res = resources['on_breakpoint'][ref]
            LOG.info("removing breakpoint on %s", ref)
            stack_id = next(x['href'] for x in res.links if
                            x['rel'] == 'stack').rsplit('/', 1)[1]
            self.heatclient.resources.signal(
                stack_id=stack_id,
                resource_name=res.logical_resource_id,
                data={'unset_hook': 'pre-update'})
        except IndexError:
            LOG.error("no more breakpoints")

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

    def cancel(self, resources):
        LOG.info("canceling update")
        self.heatclient.actions.cancel_update(self.stack.id)
        # removing existing breakpoints
        for ref in resources['on_breakpoint'].keys():
            self.clear_breakpoint(ref)

    def do_interactive_update(self):
        status = None
        while status not in ['COMPLETE', 'FAILED']:
            status, resources = self.get_status()
            if status == 'WAITING':
                for state in resources:
                    if resources[state]:
                        print("{0}: {1}".format(state,
                                                resources[state].keys()))
                user_input = raw_input("Breakpoint reached, continue? "
                                       "Enter=proceed, no=cancel update, "
                                       "C-C=quit interactive mode: ")
                if user_input.strip().lower() == 'no':
                    print("canceling the update, doing rollback")
                    self.cancel(resources)
                else:
                    ref = resources['on_breakpoint'].keys().pop()
                    print("removing breakpoint on {0}".format(ref))
                    self.clear_breakpoint(ref)
            time.sleep(1)
        print('update finished with status {0}'.format(status))

    def _resources_by_state(self):
        resources = {
            'in_progress': {},
            'on_breakpoint': {},
            'completed': {},
            'failed': {},
        }
        all_resources = self.heatclient.resources.list(
            self.stack.id, nested_depth=2)
        for res in all_resources:
            if res.resource_name != 'update_deployment':
                continue
            stack_name, stack_id = next(
                x['href'] for x in res.links if
                x['rel'] == 'stack').rsplit('/', 2)[1:]
            event = self._last_event(stack_id, res)
            if event.resource_status_reason == ('UPDATE paused until Hook '
                                                'pre-update is cleared'):
                state = 'on_breakpoint'
            elif event.resource_status == 'UPDATE_IN_PROGRESS':
                state = 'in_progress'
            elif event.resource_status == 'UPDATE_COMPLETE':
                state = 'completed'
            else:
                state = 'failed'
            resources[state][stack_name] = res
        return resources

    def _last_event(self, stack_id, res):
        last_event = None
        for ev in self.heatclient.events.list(
                stack_id=stack_id,
                resource_name=res.logical_resource_id):
            if not last_event or ev.event_time > last_event.event_time:
                last_event = ev
        return last_event
