Python bindings to the OpenStack Heat API
=========================================

This is a client for OpenStack Heat API. There's a Python API (the
:mod:`heatclient` module), a `python-openstackclient`_ plugin for command-line
use, and a legacy command-line script (installed as :program:`heat`).

==========
Python API
==========

In order to use the python api directly, you must first obtain an auth
token and identify which endpoint you wish to speak to::

  >>> tenant_id = 'b363706f891f48019483f8bd6503c54b'
  >>> heat_url = 'http://heat.example.org:8004/v1/%s' % tenant_id
  >>> auth_token = '3bcc3d3a03f44e3d8377f9247b0ad155'

Once you have done so, you can use the API like so::

  >>> from heatclient.client import Client
  >>> heat = Client('1', endpoint=heat_url, token=auth_token)

Alternatively, you can create a client instance using the keystoneauth session API::

  >>> from keystoneauth1 import loading
  >>> from keystoneauth1 import session
  >>> from heatclient import client
  >>> loader = loading.get_plugin_loader('password')
  >>> auth = loader.load_from_options(auth_url=AUTH_URL,
  ...                                 username=USERNAME,
  ...                                 password=PASSWORD,
  ...                                 project_id=PROJECT_ID)
  >>> sess = session.Session(auth=auth)
  >>> heat = client.Client('1', session=sess)
  >>> heat.stacks.list()

If you have PROJECT_NAME instead of a PROJECT_ID, use the project_name
parameter. Similarly, if your cloud uses keystone v3 and you have a DOMAIN_NAME
or DOMAIN_ID, provide it as `user_domain_(name|id)` and if you are using a
PROJECT_NAME also provide the domain information as `project_domain_(name|id)`.

For more information on keystoneauth API, see `Using Sessions`_.

.. _Using Sessions: https://docs.openstack.org/keystoneauth/latest/using-sessions.html

Reference
---------

.. toctree::
    :maxdepth: 1

    ref/index
    ref/v1/index

============================
OpenStackClient Command Line
============================

The preferred way of accessing Heat via the command line is using the
python-heatclient's plugin for `python-openstackclient`_. Heat commands are
available through the ``openstack`` CLI command when both python-heatclient and
python-openstackclient are installed.

.. toctree::
    :maxdepth: 2

    cli/index

.. _python-openstackclient: https://docs.openstack.org/python-openstackclient

========================
Legacy Command-line Tool
========================

The ``heat`` command is provided as a legacy CLI option. Users should prefer
using the python-openstackclient plugin via the ``openstack`` command instead.

In order to use the CLI, you must provide your OpenStack username,
password, tenant, and auth endpoint. Use the corresponding
configuration options (``--os-username``, ``--os-password``,
``--os-tenant-id``, and ``--os-auth-url``) or set them in environment
variables::

    export OS_USERNAME=user
    export OS_PASSWORD=pass
    export OS_TENANT_ID=b363706f891f48019483f8bd6503c54b
    export OS_AUTH_URL=http://auth.example.com:5000/v2.0

The command line tool will attempt to reauthenticate using your
provided credentials for every request. You can override this behavior
by manually supplying an auth token using ``--heat-url`` and
``--os-auth-token``. You can alternatively set these environment
variables::

    export HEAT_URL=http://heat.example.org:8004/v1/b363706f891f48019483f8bd6503c54b
    export OS_AUTH_TOKEN=3bcc3d3a03f44e3d8377f9247b0ad155

Once you've configured your authentication parameters, you can run
``heat help`` to see a complete listing of available commands.

Man Pages
---------

.. toctree::
    :maxdepth: 1

    man/heat


============
Contributing
============

Code is mirrored `on GitHub`_. Submit bugs to the python-heatclient project on
`Launchpad`_. Submit code to the openstack/python-heatclient project using
`Gerrit`_.

.. _on GitHub: https://github.com/openstack/python-heatclient
.. _Launchpad: https://launchpad.net/python-heatclient
.. _Gerrit: https://docs.openstack.org/infra/manual/developers.html#development-workflow
