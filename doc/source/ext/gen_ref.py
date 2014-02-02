# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))

sys.path.insert(0, ROOT)
sys.path.insert(0, BASE_DIR)


def gen_ref(ver, title, names):
    refdir = os.path.join(BASE_DIR, "ref")
    pkg = "heatclient"
    if ver:
        pkg = "%s.%s" % (pkg, ver)
        refdir = os.path.join(refdir, ver)
    if not os.path.exists(refdir):
        os.makedirs(refdir)
    idxpath = os.path.join(refdir, "index.rst")
    with open(idxpath, "w") as idx:
        idx.write(("%(title)s\n"
                   "%(signs)s\n"
                   "\n"
                   ".. toctree::\n"
                   "   :maxdepth: 1\n"
                   "\n") % {"title": title, "signs": "=" * len(title)})
        for name in names:
            idx.write("   %s\n" % name)
            rstpath = os.path.join(refdir, "%s.rst" % name)
            with open(rstpath, "w") as rst:
                rst.write(("%(title)s\n"
                           "%(signs)s\n"
                           "\n"
                           ".. automodule:: %(pkg)s.%(name)s\n"
                           "   :members:\n"
                           "   :undoc-members:\n"
                           "   :show-inheritance:\n"
                           "   :noindex:\n")
                          % {"title": name.capitalize(),
                             "signs": "=" * len(name),
                             "pkg": pkg, "name": name})

gen_ref("", "Client Reference", ["client", "exc"])
gen_ref("v1", "Version 1 API Reference",
        ["stacks", "resources", "events", "actions",
         "software_configs", "software_deployments"])
