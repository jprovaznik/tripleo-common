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

from tuskarclient.common import utils as tuskarutils

LOG = logging.getLogger(__name__)


class ScaleManager:
    def __init__(self, tuskarclient, heatclient, plan_id=None, stack_id=None):
        self.tuskarclient = tuskarclient
        self.heatclient = heatclient
        self.stack_id = stack_id
        self.plan = tuskarutils.find_resource(self.tuskarclient.plans, plan_id)

    def scaleup(self, role, num):
        param_name = "{0}::count".format(role)
        self.plan = self.tuskarclient.plans.patch(
            self.plan.uuid, [{'name': '{0}::count'.format(role),
                              'value': num}])
        templates = self.tuskarclient.plans.templates(self.plan.uuid)
        master = templates.get('plan.yaml')
        env = templates.get('environment.yaml')

        files = {}
        for name in templates:
            if name != 'plan.yaml' and name != 'environment.yaml':
                # there is an issue with file path - in templates we use
                # relative paths so get_file xxx doesn't include 'puppet/'
                # subdir, as a workaround 'puppet/' is removed from file names
                if name.startswith('puppet/manifests'):
                    files[name[7:]] = templates[name]
                    #print "{0} -> {1}".format(name, name[7:])
                else:
                    files[name] = templates[name]

        # TODO: add breakpoints
        params = {
            'template': master,
            'environment': env,
            'files': files,
        }
        stack = self.heatclient.stacks.update(self.stack_id, **params)
