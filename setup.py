import re

from setuptools import setup

__version__ = re.findall(r"""__version__ = ["']+([0-9\.]*)["']+""",
                        open('om_devtools/__init__.py').read())[0]


setup_args = {
    'name': 'om_devtools',
    'version': __version__,
    'description': 'Some low level OpenMDAO develoment tools',
    'classifiers': [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Topic :: Scientific/Engineering',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    'keywords': ['openmdao', 'openmdao_commands'],
    'entry_points': {
        'openmdao_commands': [
            'dist_idxs=om_devtools.dist_idxs:_dist_idxs_setup',
            'memtop=om_devtools.memtop:_memtop_setup',
        ]
    },
    'license': 'Apache License, Version 2.0',
    'packages': [
        'om_devtools',
        'om_devtools.test'
    ],
    'install_requires': [
        'openmdao>=2.9.1'
    ],
 }

setup(**setup_args)
