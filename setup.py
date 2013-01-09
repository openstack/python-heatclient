#!/usr/bin/python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import setuptools

from heatclient.openstack.common import setup
from heatclient.version import version_info as version


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setuptools.setup(
    name="python-heatclient",
    version=version.canonical_version_string(always=True),
    author='Heat API Developers',
    author_email='discuss@heat-api.org',
    description="Client library for Heat orchestration API",
    long_description=read('README.md'),
    license='Apache',
    url='https://github.com/openstack/python-heatclient',
    packages=setuptools.find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    install_requires=setup.parse_requirements(),
    test_suite="nose.collector",
    cmdclass=setup.get_cmdclass(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: OpenStack',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    entry_points={
        'console_scripts': ['heat = heatclient.shell:main']
    },
    dependency_links=setup.parse_dependency_links(),
    tests_require=setup.parse_requirements(['tools/test-requires']),
    setup_requires=['setuptools-git>=0.4'],
    data_files=[('heatclient', ['heatclient/versioninfo'])]
)
