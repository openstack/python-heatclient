#!/usr/bin/env bash

# Client constraint file contains this client version pin that is in conflict
# with installing the client from source. We should remove the version pin in
# the constraints file before applying it for from-source installation.

CONSTRAINTS_FILE=$1
shift 1

set -e

localfile="$VIRTUAL_ENV/log/upper-constraints.txt"

if [[ $CONSTRAINTS_FILE != http* ]]; then
    CONSTRAINTS_FILE=file://$CONSTRAINTS_FILE
fi

curl $CONSTRAINTS_FILE --insecure --progress-bar --output $localfile

pip install -c$localfile openstack-requirements

# This is the main purpose of the script: Allow local installation of
# the current repo. It is listed in constraints file and thus any
# install will be constrained and we need to unconstrain it.
edit-constraints $localfile -- $CLIENT_NAME

pip install -c$localfile -U $*
exit $?
