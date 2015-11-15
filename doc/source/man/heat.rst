====
heat
====

.. program:: heat

SYNOPSIS
========

  `heat` [options] <command> [command-options]

  `heat help`

  `heat help` <command>


DESCRIPTION
===========

`heat` is a command line client for controlling OpenStack Heat.

Before the `heat` command is issued, ensure the environment contains
the necessary variables so that the CLI can pass user credentials to
the server.
See `Getting Credentials for a CLI`  section of `OpenStack CLI Guide`
for more info.


OPTIONS
=======

To get a list of available commands and options run::

    heat help

To get usage and options of a command run::

    heat help <command>


EXAMPLES
========

Get information about stack-create command::

    heat help stack-create

List available stacks::

    heat stack-list

List available resources in a stack::

    heat resource-list <stack name>

Create a stack::

    heat stack-create mystack -f some-template.yaml -P "KeyName=mine"

View stack information::

    heat stack-show mystack

List stack outputs::

    heat output-list <stack name>

Show the value of a single output::

    heat output-show <stack name> <output key>

List events::

    heat event-list mystack

Delete a stack::

    heat stack-delete mystack

Abandon a stack::

    heat stack-abandon mystack

Adopt a stack ::

    heat stack-adopt -a <adopt_file> mystack

List heat-engines running status ::

    heat service-list

Note: stack-adopt and stack-abandon commands are not available by default.
Please ask your OpenStack operator to enable this feature.

BUGS
====

Heat client is hosted in Launchpad so you can view current bugs at https://bugs.launchpad.net/python-heatclient/.
