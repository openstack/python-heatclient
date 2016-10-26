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

import copy
import uuid

import six
from six.moves.urllib import parse as urlparse
from swiftclient import client as sc
from swiftclient import utils as swiftclient_utils

from heatclient._i18n import _
from heatclient import exc
from heatclient.v1 import software_configs


def build_derived_config_params(action, source, name, input_values,
                                server_id, signal_transport, signal_id=None):

    if isinstance(source, software_configs.SoftwareConfig):
        source = source.to_dict()
    input_values = input_values or {}
    inputs = copy.deepcopy(source.get('inputs')) or []

    for inp in inputs:
        input_key = inp['name']
        inp['value'] = input_values.pop(input_key, inp.get('default'))

    # for any input values that do not have a declared input, add
    # a derived declared input so that they can be used as config
    # inputs
    for inpk, inpv in input_values.items():
        inputs.append({
            'name': inpk,
            'type': 'String',
            'value': inpv
        })

    inputs.extend([{
        'name': 'deploy_server_id',
        'description': _('ID of the server being deployed to'),
        'type': 'String',
        'value': server_id
    }, {
        'name': 'deploy_action',
        'description': _('Name of the current action being deployed'),
        'type': 'String',
        'value': action
    }, {
        'name': 'deploy_signal_transport',
        'description': _('How the server should signal to heat with '
                         'the deployment output values.'),
        'type': 'String',
        'value': signal_transport
    }])

    if signal_transport == 'TEMP_URL_SIGNAL':
        inputs.append({
            'name': 'deploy_signal_id',
            'description': _('ID of signal to use for signaling '
                             'output values'),
            'type': 'String',
            'value': signal_id
        })
        inputs.append({
            'name': 'deploy_signal_verb',
            'description': _('HTTP verb to use for signaling '
                             'output values'),
            'type': 'String',
            'value': 'PUT'
        })
    elif signal_transport != 'NO_SIGNAL':
        raise exc.CommandError(
            _('Unsupported signal transport %s') % signal_transport)

    return {
        'group': source.get('group') or 'Heat::Ungrouped',
        'config': source.get('config') or '',
        'options': source.get('options') or {},
        'inputs': inputs,
        'outputs': source.get('outputs') or [],
        'name': name
    }


def create_temp_url(swift_client, name, timeout, container=None):

    container = container or '%(name)s-%(uuid)s' % {
        'name': name, 'uuid': uuid.uuid4()}
    object_name = str(uuid.uuid4())

    swift_client.put_container(container)
    key_header = 'x-account-meta-temp-url-key'
    if key_header not in swift_client.head_account():
        swift_client.post_account({
            key_header: six.text_type(uuid.uuid4())[:32]})

    key = swift_client.head_account()[key_header]
    project_path = swift_client.url.split('/')[-1]
    path = '/v1/%s/%s/%s' % (project_path, container, object_name)
    timeout_secs = timeout * 60
    tempurl = swiftclient_utils.generate_temp_url(path, timeout_secs, key,
                                                  'PUT')
    sw_url = urlparse.urlparse(swift_client.url)
    put_url = '%s://%s%s' % (sw_url.scheme, sw_url.netloc, tempurl)
    swift_client.put_object(container, object_name, '')
    return put_url


def build_signal_id(hc, args):
    if args.signal_transport != 'TEMP_URL_SIGNAL':
        return

    if args.os_no_client_auth:
        raise exc.CommandError(_(
            'Cannot use --os-no-client-auth, auth required to create '
            'a Swift TempURL.'))
    swift_client = create_swift_client(
        hc.http_client.auth, hc.http_client.session, args)

    return create_temp_url(swift_client, args.name, args.timeout)


def create_swift_client(auth, session, args):
    auth_token = auth.get_token(session)
    endpoint = auth.get_endpoint(session,
                                 service_type='object-store',
                                 region_name=args.os_region_name)
    project_name = args.os_project_name or args.os_tenant_name
    swift_args = {
        'auth_version': '2.0',
        'tenant_name': project_name,
        'user': args.os_username,
        'key': None,
        'authurl': None,
        'preauthtoken': auth_token,
        'preauthurl': endpoint,
        'cacert': args.os_cacert,
        'insecure': args.insecure
    }

    return sc.Connection(**swift_args)
