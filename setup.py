from setuptools import setup

from dstack.version import __version__

setup(
    name="dstack",
    version=__version__,
    author="swordhands",
    author_email="team@dstack.ai",
    packages=["dstack", "dstack.cli"],
    scripts=[],
    entry_points={
        "console_scripts": ["dstack=dstack.cli.main:main"],
    },
    url="https://dstack.ai",
    license="LICENSE",
    description="An open-source library to publish plots",
    long_description="",  # open("README").read(),
    install_requires=[
        "PyYAML>=5.1"
    ],
)
