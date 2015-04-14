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

LOG = logging.getLogger(__name__)


def heat_params_from_templates(templates):
    master = templates.get('plan.yaml')
    env = templates.get('environment.yaml')

    files = {}
    for name in templates:
        if name != 'plan.yaml' and name != 'environment.yaml':
            # there is an issue with file path - in templates we use
            # relative paths so 'get_file xxx' doesn't include 'puppet/'
            # subdir, as a workaround 'puppet/' is removed from file names
            if name.startswith('puppet/manifests'):
                files[name[7:]] = templates[name]
            else:
                files[name] = templates[name]

    return {
        'template': master,
        'environment': env,
        'files': files,
    }
