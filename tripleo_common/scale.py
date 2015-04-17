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
import os
import tempfile

from heatclient.common import template_utils
from tripleo_common import libutils
from tuskarclient.common import utils as tuskarutils

LOG = logging.getLogger(__name__)


class ScaleManager(object):
    def __init__(self, tuskarclient, heatclient, plan_id=None, stack_id=None):
        self.tuskarclient = tuskarclient
        self.heatclient = heatclient
        self.stack_id = stack_id
        self.plan = tuskarutils.find_resource(self.tuskarclient.plans, plan_id)

    def scaleup(self, role, num):
        LOG.debug('updating role %s count to %s', role, num)
        self.plan = self.tuskarclient.plans.patch(
            self.plan.uuid, [{'name': '{0}::count'.format(role),
                              'value': num}])

        tpl_dir = self._write_templates(
            self.tuskarclient.plans.templates(self.plan.uuid))
        tpl_files, template = template_utils.get_template_contents(
            os.path.join(tpl_dir, 'plan.yaml'))
        env_files, env = template_utils.process_multiple_environments_and_files(env_paths=[os.path.join(tpl_dir, 'environment.yaml')])
        fields = {
            'stack_id': self.stack_id,
            'template': template,
            'files': dict(list(tpl_files.items()) + list(env_files.items())),
            'environment': env
        }

        self.heatclient.stacks.update(**fields)

    # passing files fetched from tuskar directly to heat doesn't work:
    # it seems there is an issue with relative paths when using "get_file" in
    # puppet subdir, saving template files and let heatclient process it
    # works as expected
    def _write_templates(self, templates):
        output_dir = tempfile.mkdtemp()
        print "xxxxxxxxxxxxxx {0}".format(output_dir)
        for template_name, template_content in templates.items():

            # It's possible to organize the role templates and their dependent
            # files into directories, in which case the template_name will carry
            # the directory information. If that's the case, first create the
            # directory structure (if it hasn't already been created by another
            # file in the templates list).
            template_dir = os.path.dirname(template_name)
            output_template_dir = os.path.join(output_dir, template_dir)
            if template_dir and not os.path.exists(output_template_dir):
                os.makedirs(output_template_dir)

            filename = os.path.join(output_dir, template_name)
            with open(filename, 'w+') as template_file:
                template_file.write(template_content)
        return output_dir
