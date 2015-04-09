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
from tripleo_common import scales


def parse_args():
    description = textwrap.dedent("""
    Scale up nodes.
    """)

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-s', '--stack', dest='stack',
                        help='Name or ID of a stack to scale')
    parser.add_argument('-p', '--plan', dest='plan',
                        help='Name or ID of a plan to scale')
    parser.add_argument('-c', '--continue', dest='stack_continue',
                        help='Name or ID of a stack with scale in progress')
    parser.add_argument('-r', '--role', dest='role',
                        help='Name or ID of a role to scale')
    parser.add_argument('-n', '--num', dest='scale_num',
                        help='How many nodes should be added')
    parser.add_argument('-i', '--interactive', dest='interactive',
                        action='store_true',
                        help='Run scale process in interactive mode')
    environment._add_logging_arguments(parser)
    return parser.parse_args()


def main():
    args = parse_args()
    environment._configure_logging(args)
    try:
        environment._ensure()
        heatclient = clients.get_heat_client()
        tuskarclient = clients.get_tuskar_client()
        if args.stack:
            scale = scales.ScaleManager(heatclient=heatclient,
                                        tuskarclient=tuskarclient,
                                        plan_id=args.plan,
                                        stack_id=args.stack)
            scale.scaleup(args.role, args.scale_num)
        elif args.stack_continue:
            scale = scales.ScaleManager(client=client,
                                           stack_id=args.stack_continue)
        if args.interactive:
            scales.do_interactive_scale()
        else:
            print("status: {0} ({1})".format(scales.get_status()))
    except Exception:
        logging.exception("Unexpected error during command execution")
        return 1
    return 0
