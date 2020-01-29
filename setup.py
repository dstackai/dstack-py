from setuptools import setup

setup(
    name="dstack",
    version="0.1.0",
    author="swordhands",
    author_email="team@dstack.ai",
    packages=["dstack", "dstack.cli"],
    scripts=[],
    entry_points={
        "console_scripts": ['dstack=dstack.cli.main:main'],
    },
    url="http://pypi.python.org/pypi/dstack/",
    license="LICENSE",
    description="DStack Python API",
    long_description="",  # open("README").read(),
    install_requires=[
    ],
)
