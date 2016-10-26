#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

import collections

from osc_lib.command import command

from heatclient._i18n import _
from heatclient.common import format_utils
from heatclient import exc


class ListStackFailures(command.Command):
    """Show information about failed stack resources."""

    def take_action(self, parsed_args):
        self.heat_client = self.app.client_manager.orchestration
        failures = self._build_failed_resources(parsed_args.stack)
        deployment_failures = self._build_software_deployments(failures)
        self._print_failures(failures, deployment_failures,
                             long=parsed_args.long)

    def get_parser(self, prog_name):
        parser = super(ListStackFailures, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Stack to display (name or ID)'),
        )
        parser.add_argument(
            '--long',
            action='store_true',
            default=False,
            help=_('Show full deployment logs in output'),
        )
        return parser

    def _build_failed_resources(self, stack):
        """List information about FAILED stack resources.

        Failed resources are added by recursing from the top level stack into
        failed nested stack resources. A failed nested stack resource is only
        added to the failed list if it contains no failed resources.
        """
        s = self.heat_client.stacks.get(stack)
        if s.status != 'FAILED':
            return []
        resources = self.heat_client.resources.list(s.id)
        failures = collections.OrderedDict()
        self._append_failed_resources(failures, resources, [s.stack_name])
        return failures

    def _append_failed_resources(self, failures, resources, resource_path):
        """Recursively build list of failed resources."""
        appended = False
        for r in resources:
            if not r.resource_status.endswith('FAILED'):
                continue
            # determine if this resources is a nested stack
            links_rel = list([l['rel'] for l in r.links])
            is_nested = 'nested' in links_rel
            nested_appended = False
            next_resource_path = list(resource_path)
            next_resource_path.append(r.resource_name)
            if is_nested:
                try:
                    nested_resources = self.heat_client.resources.list(
                        r.physical_resource_id)
                    nested_appended = self._append_failed_resources(
                        failures, nested_resources, next_resource_path)
                except exc.HTTPNotFound:
                    # there is a failed resource but no stack
                    pass
            if not nested_appended:
                failures['.'.join(next_resource_path)] = r
            appended = True
        return appended

    def _build_software_deployments(self, resources):
        """Build a dict of software deployments from the supplied resources.

        The key is the deployment ID.
        """
        df = {}
        if not resources:
            return df
        for r in resources.values():
            if r.resource_type not in ('OS::Heat::StructuredDeployment',
                                       'OS::Heat::SoftwareDeployment'):
                continue
            try:
                sd = self.heat_client.software_deployments.get(
                    deployment_id=r.physical_resource_id)
                df[r.physical_resource_id] = sd
            except exc.HTTPNotFound:
                pass
        return df

    def _print_failures(self, failures, deployment_failures, long=False):
        """Print failed resources.

        If the resource is a deployment resource, look up the deployment and
        print deploy_stdout and deploy_stderr.
        """
        out = self.app.stdout

        if not failures:
            return
        for k, f in failures.items():
            out.write('%s:\n' % k)
            out.write('  resource_type: %s\n' % f.resource_type)
            out.write('  physical_resource_id: %s\n' %
                      f.physical_resource_id)
            out.write('  status: %s\n' % f.resource_status)
            reason = format_utils.indent_and_truncate(
                f.resource_status_reason,
                spaces=4,
                truncate=not long,
                truncate_prefix='...\n')
            out.write('  status_reason: |\n%s\n' % reason)
            df = deployment_failures.get(f.physical_resource_id)
            if df:
                for output in ('deploy_stdout', 'deploy_stderr'):
                    format_utils.print_software_deployment_output(
                        data=df.output_values, name=output, long=long, out=out)
