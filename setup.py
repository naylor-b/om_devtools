
from setuptools import setup

setup_args = {
    'description': 'Some low level OpenMDAO develoment tools',
    'entry_points': {'openmdao_commands': ['dist_idxs=om_devtools.dist__idxs:_dist_idxs_setup']},
    'install_requires': ['openmdao>=2.9.1'],
    'keywords': ['openmdao_commands'],
    'license': 'Apache License, Version 2.0',
    'name': 'om_devtools',
    'packages': ['om_devtools', 'om_devtools.test'],
    'version': '1.0'
 }

setup(**setup_args)
