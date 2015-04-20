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

import fnmatch
import logging
import time

LOG = logging.getLogger(__name__)


class StackUpdateManager(object):
    def __init__(self, heatclient, stack, hook_type, nested_depth=5,
                 resource_name=None):
        self.heatclient = heatclient
        self.stack = stack
        self.hook_type = hook_type
        self.nested_depth = nested_depth
        self.resource_name = resource_name
        self.stack_change_time = self._stack_change_time()

    def clear_breakpoint(self, ref):
        resources = self._resources_by_state()
        try:
            res = resources['on_breakpoint'][ref]
            LOG.info("removing breakpoint on %s", ref)
            print("removing breakpoint on {0}".format(ref))
            stack_id = next(x['href'] for x in res.links if
                            x['rel'] == 'stack').rsplit('/', 1)[1]
            self.heatclient.resources.signal(
                stack_id=stack_id,
                resource_name=res.logical_resource_id,
                data={'unset_hook': self.hook_type})
        except IndexError:
            LOG.error("no more breakpoints")

    def get_status(self):
        self.stack = self.heatclient.stacks.get(self.stack.id)
        # check if any of deployments' child resource has last
        # event indicating that it has reached a breakpoint (this
        # seems to be the only way how to check pre-create breakpoints ATM)
        resources = self._resources_by_state()
        if self.stack.status == 'IN_PROGRESS':
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

    def cancel(self):
        LOG.info("canceling update")
        self.heatclient.actions.cancel_update(self.stack.id)
        # removing existing breakpoints
        resources = self._resources_by_state()
        for ref in resources['on_breakpoint'].keys():
            self.clear_breakpoint(ref)

    def do_interactive_update(self):
        status = None
        while status not in ['COMPLETE', 'FAILED']:
            status, resources = self.get_status()
            print(status)
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
                    self.cancel()
                else:
                    ref = resources['on_breakpoint'].keys().pop()
                    print("removing breakpoint on {0}".format(ref))
                    self.clear_breakpoint(ref)
            time.sleep(5)
        print('update finished with status {0}'.format(status))

    def _resources_by_state(self):
        resources = {
            'not_started': {},
            'in_progress': {},
            'on_breakpoint': {},
            'completed': {},
            'failed': {},
        }
        all_resources = self.heatclient.resources.list(
            self.stack.id, nested_depth=self.nested_depth)
        if self.hook_type == 'pre-create':
            hook_reason = 'CREATE paused until Hook pre-create is cleared'
            hook_clear_reason = 'Hook pre-create is cleared'
        else:
            hook_reason = 'UPDATE paused until Hook pre-update is cleared'
            hook_clear_reason = 'Hook pre-update is cleared'
        for res in all_resources:
            if self.resource_name:
                if not fnmatch.fnmatchcase(res.resource_name,
                                           self.resource_name):
                    continue
            stack_name, stack_id = next(
                x['href'] for x in res.links if
                x['rel'] == 'stack').rsplit('/', 2)[1:]
            events = self.heatclient.events.list(
                    stack_id=stack_id,
                    resource_name=res.logical_resource_id,
                    sort_dir='asc')
            state = 'not_started'
            for ev in  events:
                # ignore events older than start of the last stack change
                if ev.event_time < self.stack_change_time:
                    continue
                if ev.resource_status_reason == hook_reason:
                    state = 'on_breakpoint'
                elif ev.resource_status_reason == hook_clear_reason:
                    state = 'in_progress'
                elif ev.resource_status == 'UPDATE_IN_PROGRESS':
                    state = 'in_progress'
                elif ev.resource_status == 'UPDATE_COMPLETE':
                    state = 'completed'
            resources[state][stack_name] = res

        return resources

    def _stack_change_time(self):
        if self.hook_type == 'pre-create':
            status_reason = 'Stack CREATE started'
        else:
            status_reason = 'Stack UPDATE started'
        events = self.heatclient.events.list(
            stack_id=self.stack.id,
            sort_dir='desc')
        try:
            ev = next(e for e in events if
                e.resource_status_reason == status_reason)
            return ev.event_time
        except StopIteration:
            return None