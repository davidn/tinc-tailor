#!/usr/bin/python

from distutils.core import setup

setup( name = 'TincTailor',
       description = 'Configure Tinc and GenieDB CloudFabric',
       version = '0.1',
       author = 'GenieDB Ltd.',
       author_email = 'tech@geniedb.com',
       packages = ['tailor', 'junitxml'],
       package_data = {'tailor': ['cloudfabric.conf','cloudfabric.firewall','tinc.conf','host.conf','nets.boot']},
       scripts = ['tinc-tailor'],
       requires = ['paramiko', 'argparse']
       )
