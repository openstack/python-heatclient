import os
import sys

import setuptools

from heatclient.openstack.common import setup


requires = setup.parse_requirements()
dependency_links = setup.parse_dependency_links()
tests_require = setup.parse_requirements(['tools/test-requires'])

if sys.version_info < (2, 6):
    requires.append('simplejson')


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setuptools.setup(
    name="python-heatclient",
    version=setup.get_post_version('heatclient'),
    description="Client library for Heat orchestration API",
    long_description=read('README.rst'),
    url='https://github.com/heat-api/python-heatclient',
    license='Apache',
    author='Heat API Developers',
    author_email='discuss@heat-api.org',
    packages=setuptools.find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    cmdclass=setup.get_cmdclass(),
    install_requires=requires,
    dependency_links=dependency_links,
    tests_require=tests_require,
    setup_requires=['setuptools-git>=0.4'],
    test_suite="nose.collector",
    entry_points={'console_scripts': ['heat = heatclient.shell:main']},
)
