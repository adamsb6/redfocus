#!/usr/bin/env python
import sys
from setuptools import setup
      
kwargs = {
    'name': 'redfocus',
    'version': '0.5',
    'description': 'Import Redmine issues into OmniFocus',
    'author': 'Brandon Adams',
    'author_email': 'brandon.adams@me.com',
    'packages': ['redfocus'],
    'install_requires': ['requests','appscript'],
    'entry_points': {
        'console_scripts': ['redfocus = redfocus:main'],
    },
}

if sys.version_info < (2, 7):
    kwargs['install_requires'].append('argparse==1.2.1')

setup(**kwargs)      
