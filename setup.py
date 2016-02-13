import os
import setuptools
import sys

from setuptools import setup

# To support 2/3 installation
setup_version = int(setuptools.__version__.split('.')[0])
if setup_version < 18:
    print("Please upgrade your setuptools to install SoundScrape: ")
    print("pip install -U pip wheel setuptools")
    quit()

# Set external files
try:
    from pypandoc import convert
    README = convert('README.md', 'rst')	 
except ImportError:
    README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

with open(os.path.join(os.path.dirname(__file__), 'requirements.txt')) as f:
    required = f.read().splitlines()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

# Not happy about this..
# Should work for pip and pip3.
# Hopefully, mutagen will just publish the patch to pip and we can nuke this..
pkgs = lambda : list(__import__('pkg_resources').working_set)
pkg_names = lambda : [x.project_name for x in pkgs()]
if 'mutagen' not in pkg_names():
    pip_version = sys.argv[0]
    if 'pip' not in pip_version:
        pip_version = 'pip'
    os.system(pip_version + ' install https://bitbucket.org/lazka/mutagen/get/default.tar.gz')

setup(
    name='soundscrape',
    version='0.23.6',
    packages=['soundscrape'],
    install_requires=required,
    extras_require={ ':python_version < "3.0"': [ 'wsgiref>=0.1.2', ], },    
    include_package_data=True,
    license='MIT License',
    description='Scrape an artist from SoundCloud',
    long_description=README,
    url='https://github.com/Miserlou/SoundScrape',
    author='Rich Jones',
    author_email='rich@openwatch.net',
    entry_points={
        'console_scripts': [
            'soundscrape = soundscrape.soundscrape:main',
        ]
    },
    classifiers=[
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
