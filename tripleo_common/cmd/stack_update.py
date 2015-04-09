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

import argparse
import logging
import textwrap

from tripleo_common.cmd.utils import _clients as clients
from tripleo_common.cmd.utils import environment
from tripleo_common import updates


def parse_args():
    description = textwrap.dedent("""
    Run stack update.
    """)

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-s', '--stack', dest='stack', required=True,
                        help='Name or ID of a stack to update')
    parser.add_argument('-c', '--continue', dest='continue_in_update',
                        action='store_true',
                        help='Name or ID of a stack with update in progress')
    parser.add_argument('-n', '--name', dest='update_name',
                        help='Name for the update stack')
    parser.add_argument('-i', '--interactive', dest='interactive',
                        action='store_true',
                        help='Run update process in interactive mode')
    environment._add_logging_arguments(parser)
    return parser.parse_args()


def main():
    args = parse_args()
    environment._configure_logging(args)
    try:
        environment._ensure()
        client = clients.get_heat_client()
        update = updates.UpdateManager(
            heatclient=clients.get_heat_client(),
            tuskarclient=clients.get_tuskar_client(),
            stack_id=args.stack)
        if not args.continue_in_update:
            update.start()

        if args.interactive:
            update.do_interactive_update()
        else:
            print("status: {0} ({1})".format(update.get_status()))
    except Exception:
        logging.exception("Unexpected error during command execution")
        return 1
    return 0
