#!/usr/bin/env python
from setuptools import setup

setup(
      name='tap-grafana',
      version='0.1.0',
      description='Singer.io tap for extracting Grafana Loki search results.',
      author='P.A. Masse',
      url='http://www.split.io',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_grafana'],
      install_requires=[
            'singer-python>=5.0.12',
            'requests',
            'pendulum',
            'ujson',
            'voluptuous'
      ],
      entry_points='''
            [console_scripts]
            tap-grafana=tap_grafana:main
      ''',
      packages=['tap_grafana']
)
