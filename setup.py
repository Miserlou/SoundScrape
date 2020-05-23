import os
import soundscrape

from setuptools import setup

# Set external files
try:
    from pypandoc import convert

    README = convert("README.md", "rst")
except ImportError:
    README = open(os.path.join(os.path.dirname(__file__), "README.md")).read()

with open(os.path.join(os.path.dirname(__file__), "requirements.txt")) as f:
    required = f.read().splitlines()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name="soundscrape",
    version=soundscrape.__version__,
    packages=["soundscrape"],
    install_requires=required,
    extras_requires={"tests": ["pytest"],},
    include_package_data=True,
    license="MIT License",
    description="Scrape an artist from SoundCloud",
    long_description=README,
    url="https://github.com/Miserlou/SoundScrape",
    author="Rich Jones",
    author_email="rich@openwatch.net",
    entry_points={"console_scripts": ["soundscrape = soundscrape.soundscrape:main",]},
    classifiers=[
        "Environment :: Console",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
)
