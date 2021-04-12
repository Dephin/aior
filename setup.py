import re

from setuptools import setup, find_packages

# in case of importing other dependencies
with open('aior/__init__.py', encoding='utf8') as f:
    version = re.search(r"__version__ = '(.*?)'", f.read()).group(1)

setup(
    name='aior',
    version=version,
    packages=find_packages(include=["aior*"]),
    url='https://github.com/Dephin/aior',
    license='MIT License',
    author='Dephin',
    author_email='',
    description='Aior is a async, fast server/client framework based on aiohttp, which provides many out-of-box components for quickly developing restful http api and so on.',
    install_requires=[
        'aiohttp>=3.6.2',
        'pydantic>=1.2',
    ],
    python_requires='>=3.7'
)
