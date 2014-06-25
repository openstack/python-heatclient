#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Command-line interface to the Heat API.
"""

from __future__ import print_function

import argparse
import logging
import six
import sys

from keystoneclient.v2_0 import client as ksclient

import heatclient
from heatclient import client as heat_client
from heatclient.common import utils
from heatclient import exc
from heatclient.openstack.common import strutils

logger = logging.getLogger(__name__)


class HeatShell(object):

    def get_base_parser(self):
        parser = argparse.ArgumentParser(
            prog='heat',
            description=__doc__.strip(),
            epilog='See "heat help COMMAND" '
                   'for help on a specific command.',
            add_help=False,
            formatter_class=HelpFormatter,
        )

        # Global arguments
        parser.add_argument('-h', '--help',
                            action='store_true',
                            help=argparse.SUPPRESS)

        parser.add_argument('--version',
                            action='version',
                            version=heatclient.__version__,
                            help="Shows the client version and exits.")

        parser.add_argument('-d', '--debug',
                            default=bool(utils.env('HEATCLIENT_DEBUG')),
                            action='store_true',
                            help='Defaults to env[HEATCLIENT_DEBUG].')

        parser.add_argument('-v', '--verbose',
                            default=False, action="store_true",
                            help="Print more verbose output.")

        parser.add_argument('-k', '--insecure',
                            default=False,
                            action='store_true',
                            help="Explicitly allow the client to perform "
                            "\"insecure\" SSL (https) requests. The server's "
                            "certificate will not be verified against any "
                            "certificate authorities. "
                            "This option should be used with caution.")

        parser.add_argument('--os-cacert',
                            metavar='<ca-certificate>',
                            default=utils.env('OS_CACERT', default=None),
                            help='Specify a CA bundle file to use in '
                            'verifying a TLS (https) server certificate. '
                            'Defaults to env[OS_CACERT]')

        parser.add_argument('--cert-file',
                            help='Path of certificate file to use in SSL '
                            'connection. This file can optionally be '
                            'prepended with the private key.')

        parser.add_argument('--key-file',
                            help='Path of client key to use in SSL connection.'
                            'This option is not necessary if your key is'
                            ' prepended to your cert file.')

        parser.add_argument('--ca-file',
                            help='Path of CA SSL certificate(s) used to verify'
                            ' the remote server\'s certificate. Without this'
                            ' option the client looks'
                            ' for the default system CA certificates.')

        parser.add_argument('--api-timeout',
                            help='Number of seconds to wait for an '
                                 'API response, '
                                 'defaults to system socket timeout')

        parser.add_argument('--os-username',
                            default=utils.env('OS_USERNAME'),
                            help='Defaults to env[OS_USERNAME].')

        parser.add_argument('--os_username',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-password',
                            default=utils.env('OS_PASSWORD'),
                            help='Defaults to env[OS_PASSWORD].')

        parser.add_argument('--os_password',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-tenant-id',
                            default=utils.env('OS_TENANT_ID'),
                            help='Defaults to env[OS_TENANT_ID].')

        parser.add_argument('--os_tenant_id',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-tenant-name',
                            default=utils.env('OS_TENANT_NAME'),
                            help='Defaults to env[OS_TENANT_NAME].')

        parser.add_argument('--os_tenant_name',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-auth-url',
                            default=utils.env('OS_AUTH_URL'),
                            help='Defaults to env[OS_AUTH_URL].')

        parser.add_argument('--os_auth_url',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-region-name',
                            default=utils.env('OS_REGION_NAME'),
                            help='Defaults to env[OS_REGION_NAME].')

        parser.add_argument('--os_region_name',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-auth-token',
                            default=utils.env('OS_AUTH_TOKEN'),
                            help='Defaults to env[OS_AUTH_TOKEN].')

        parser.add_argument('--os_auth_token',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-no-client-auth',
                            default=utils.env('OS_NO_CLIENT_AUTH'),
                            action='store_true',
                            help="Do not contact keystone for a token. "
                                 "Defaults to env[OS_NO_CLIENT_AUTH].")

        parser.add_argument('--heat-url',
                            default=utils.env('HEAT_URL'),
                            help='Defaults to env[HEAT_URL].')

        parser.add_argument('--heat_url',
                            help=argparse.SUPPRESS)

        parser.add_argument('--heat-api-version',
                            default=utils.env('HEAT_API_VERSION', default='1'),
                            help='Defaults to env[HEAT_API_VERSION] or 1.')

        parser.add_argument('--heat_api_version',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-service-type',
                            default=utils.env('OS_SERVICE_TYPE'),
                            help='Defaults to env[OS_SERVICE_TYPE].')

        parser.add_argument('--os_service_type',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-endpoint-type',
                            default=utils.env('OS_ENDPOINT_TYPE'),
                            help='Defaults to env[OS_ENDPOINT_TYPE].')

        parser.add_argument('--os_endpoint_type',
                            help=argparse.SUPPRESS)

        # This unused option should remain so that scripts that
        # use it do not break. It is suppressed so it will not
        # appear in the help.
        parser.add_argument('-t', '--token-only',
                            default=bool(False),
                            action='store_true',
                            help=argparse.SUPPRESS)

        parser.add_argument('--include-password',
                            default=bool(utils.env('HEAT_INCLUDE_PASSWORD')),
                            action='store_true',
                            help='Send os-username and os-password to heat.')

        return parser

    def get_subcommand_parser(self, version):
        parser = self.get_base_parser()

        self.subcommands = {}
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        submodule = utils.import_versioned_module(version, 'shell')
        self._find_actions(subparsers, submodule)
        self._find_actions(subparsers, self)
        self._add_bash_completion_subparser(subparsers)

        return parser

    def _add_bash_completion_subparser(self, subparsers):
        subparser = subparsers.add_parser(
            'bash_completion',
            add_help=False,
            formatter_class=HelpFormatter
        )
        self.subcommands['bash_completion'] = subparser
        subparser.set_defaults(func=self.do_bash_completion)

    def _find_actions(self, subparsers, actions_module):
        for attr in (a for a in dir(actions_module) if a.startswith('do_')):
            # I prefer to be hyphen-separated instead of underscores.
            command = attr[3:].replace('_', '-')
            callback = getattr(actions_module, attr)
            desc = callback.__doc__ or ''
            help = desc.strip().split('\n')[0]
            arguments = getattr(callback, 'arguments', [])

            subparser = subparsers.add_parser(command,
                                              help=help,
                                              description=desc,
                                              add_help=False,
                                              formatter_class=HelpFormatter)
            subparser.add_argument('-h', '--help',
                                   action='help',
                                   help=argparse.SUPPRESS)
            self.subcommands[command] = subparser
            for (args, kwargs) in arguments:
                subparser.add_argument(*args, **kwargs)
            subparser.set_defaults(func=callback)

    def _get_ksclient(self, **kwargs):
        """Get an endpoint and auth token from Keystone.

        :param username: name of user
        :param password: user's password
        :param tenant_id: unique identifier of tenant
        :param tenant_name: name of tenant
        :param auth_url: endpoint to authenticate against
        :param token: token to use instead of username/password
        """
        kc_args = {'auth_url': kwargs.get('auth_url'),
                   'insecure': kwargs.get('insecure'),
                   'cacert': kwargs.get('cacert')}

        if kwargs.get('tenant_id'):
            kc_args['tenant_id'] = kwargs.get('tenant_id')
        else:
            kc_args['tenant_name'] = kwargs.get('tenant_name')

        if kwargs.get('token'):
            kc_args['token'] = kwargs.get('token')
        else:
            kc_args['username'] = kwargs.get('username')
            kc_args['password'] = kwargs.get('password')

        return ksclient.Client(**kc_args)

    def _get_endpoint(self, client, **kwargs):
        """Get an endpoint using the provided keystone client."""
        if kwargs.get('region_name'):
            return client.service_catalog.url_for(
                service_type=kwargs.get('service_type') or 'orchestration',
                attr='region',
                filter_value=kwargs.get('region_name'),
                endpoint_type=kwargs.get('endpoint_type') or 'publicURL')
        return client.service_catalog.url_for(
            service_type=kwargs.get('service_type') or 'orchestration',
            endpoint_type=kwargs.get('endpoint_type') or 'publicURL')

    def _setup_logging(self, debug):
        log_lvl = logging.DEBUG if debug else logging.WARNING
        logging.basicConfig(
            format="%(levelname)s (%(module)s) %(message)s",
            level=log_lvl)
        logging.getLogger('iso8601').setLevel(logging.WARNING)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

    def _setup_verbose(self, verbose):
        if verbose:
            exc.verbose = 1

    def main(self, argv):
        # Parse args once to find version
        parser = self.get_base_parser()
        (options, args) = parser.parse_known_args(argv)
        self._setup_logging(options.debug)
        self._setup_verbose(options.verbose)

        # build available subcommands based on version
        api_version = options.heat_api_version
        subcommand_parser = self.get_subcommand_parser(api_version)
        self.parser = subcommand_parser

        # Handle top-level --help/-h before attempting to parse
        # a command off the command line
        if not args and options.help or not argv:
            self.do_help(options)
            return 0

        # Parse args again and call whatever callback was selected
        args = subcommand_parser.parse_args(argv)

        # Short-circuit and deal with help command right away.
        if args.func == self.do_help:
            self.do_help(args)
            return 0
        elif args.func == self.do_bash_completion:
            self.do_bash_completion(args)
            return 0

        if not args.os_username and not args.os_auth_token:
            raise exc.CommandError("You must provide a username via"
                                   " either --os-username or env[OS_USERNAME]"
                                   " or a token via --os-auth-token or"
                                   " env[OS_AUTH_TOKEN]")

        if not args.os_password and not args.os_auth_token:
            raise exc.CommandError("You must provide a password via"
                                   " either --os-password or env[OS_PASSWORD]"
                                   " or a token via --os-auth-token or"
                                   " env[OS_AUTH_TOKEN]")

        if args.os_no_client_auth:
            if not args.heat_url:
                raise exc.CommandError("If you specify --os-no-client-auth"
                                       " you must also specify a Heat API URL"
                                       " via either --heat-url or"
                                       " env[HEAT_URL]")
        else:
            # Tenant name or ID is needed to make keystoneclient retrieve a
            # service catalog, it's not required if os_no_client_auth is
            # specified, neither is the auth URL
            if not (args.os_tenant_id or args.os_tenant_name):
                raise exc.CommandError("You must provide a tenant_id via"
                                       " either --os-tenant-id or via"
                                       " env[OS_TENANT_ID]")

            if not args.os_auth_url:
                raise exc.CommandError("You must provide an auth url via"
                                       " either --os-auth-url or via"
                                       " env[OS_AUTH_URL]")

        kwargs = {
            'username': args.os_username,
            'password': args.os_password,
            'token': args.os_auth_token,
            'tenant_id': args.os_tenant_id,
            'tenant_name': args.os_tenant_name,
            'auth_url': args.os_auth_url,
            'service_type': args.os_service_type,
            'endpoint_type': args.os_endpoint_type,
            'insecure': args.insecure,
            'cacert': args.os_cacert,
            'include_pass': args.include_password
        }

        endpoint = args.heat_url

        if not args.os_no_client_auth:
            _ksclient = self._get_ksclient(**kwargs)
            token = args.os_auth_token or _ksclient.auth_token

            kwargs = {
                'token': token,
                'insecure': args.insecure,
                'ca_file': args.ca_file,
                'cert_file': args.cert_file,
                'key_file': args.key_file,
                'username': args.os_username,
                'password': args.os_password,
                'endpoint_type': args.os_endpoint_type,
                'include_pass': args.include_password
            }

            if args.os_region_name:
                kwargs['region_name'] = args.os_region_name

            if not endpoint:
                endpoint = self._get_endpoint(_ksclient, **kwargs)

        if args.api_timeout:
            kwargs['timeout'] = args.api_timeout

        client = heat_client.Client(api_version, endpoint, **kwargs)

        args.func(client, args)

    def do_bash_completion(self, args):
        """Prints all of the commands and options to stdout.

        The heat.bash_completion script doesn't have to hard code them.
        """
        commands = set()
        options = set()
        for sc_str, sc in self.subcommands.items():
            commands.add(sc_str)
            for option in list(sc._optionals._option_string_actions):
                options.add(option)

        commands.remove('bash-completion')
        commands.remove('bash_completion')
        print(' '.join(commands | options))

    @utils.arg('command', metavar='<subcommand>', nargs='?',
               help='Display help for <subcommand>.')
    def do_help(self, args):
        """Display help about this program or one of its subcommands."""
        if getattr(args, 'command', None):
            if args.command in self.subcommands:
                self.subcommands[args.command].print_help()
            else:
                raise exc.CommandError("'%s' is not a valid subcommand" %
                                       args.command)
        else:
            self.parser.print_help()


class HelpFormatter(argparse.HelpFormatter):
    def start_section(self, heading):
        # Title-case the headings
        heading = '%s%s' % (heading[0].upper(), heading[1:])
        super(HelpFormatter, self).start_section(heading)


def main(args=None):
    try:
        if args is None:
            args = sys.argv[1:]

        HeatShell().main(args)
    except Exception as e:
        if '--debug' in args or '-d' in args:
            raise
        else:
            print(strutils.safe_encode(six.text_type(e)), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
