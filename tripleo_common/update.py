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
from tripleo_common import stack_update
from tuskarclient.common import utils as tuskarutils

LOG = logging.getLogger(__name__)


class PackageUpdateManager(stack_update.StackUpdateManager):
    def __init__(self, heatclient, tuskarclient, stack_id, plan_id):
        stack = heatclient.stacks.get(stack_id)
        self.tuskarclient = tuskarclient
        self.plan = tuskarutils.find_resource(self.tuskarclient.plans, plan_id)
        self.resource_name = '*UpdateDeployment'
        super(PackageUpdateManager, self).__init__(
            heatclient=heatclient, stack=stack, hook_type='pre-update',
            nested_depth=5, resource_name=self.resource_name)

    def update(self):
        params = libutils.heat_params_from_templates(
            self.tuskarclient.plans.templates(self.plan.uuid))
        timestamp = int(time.time())
        params['parameters'] = {
            'BlockStorageUpdateTimestamp': timestamp,
            'CephStorageUpdateTimestamp': timestamp,
            'ComputeUpdateTimestamp': timestamp,
            'ControllerUpdateTimestamp': timestamp,
            'ObjectStorageUpdateTimestamp': timestamp,
        }
        env = yaml.load(params['environment'])
        template_utils.deep_update(env, {
            'resource_registry': {
                'resources': {
                    self.resource_name: {'hooks': 'pre-update'}
                }
            }
        })
        params['environment'] = env
        LOG.info('updating stack: {0}', self.stack.stack_name)
        self.heatclient.stacks.update(self.stack.id, **params)
