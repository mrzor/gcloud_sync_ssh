from os import path
from setuptools import setup, find_packages


def read(rel_path):
    here = path.abspath(path.dirname(__file__))
    with open(path.join(here, rel_path), 'r', encoding='utf-8') as f:
        return f.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


setup(
    name='gcloud_sync_ssh',
    author='mrzor',
    version=get_version('gcloud_sync_ssh/__init__.py'),
    url="https://github.com/mrzor/gcloud_sync_ssh",
    description="A tool to synchronize GCP instances IP addresses to SSH config.",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    license="MIT",
    python_requires=">=3.6",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration"],
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        'click>=7.1',
        'loguru>=0.5',
        'ostruct>=4.0',
        'pydantic>=1.6',
        'colored>=1.4.2'
    ],
    entry_points='''
        [console_scripts]
        gcloud_sync_ssh=gcloud_sync_ssh.cli:cli
    ''',
)
