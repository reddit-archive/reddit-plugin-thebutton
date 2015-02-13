#!/usr/bin/env python
from setuptools import setup, find_packages

setup(name='reddit_thebutton',
    description='reddit button',
    version='0.1',
    author='Brian Simpson',
    author_email='brian@reddit.com',
    packages=find_packages(),
    install_requires=[
        'r2',
    ],
    entry_points={
        'r2.plugin':
            ['thebutton = reddit_thebutton:TheButton']
    },
    zip_safe=False,
)
