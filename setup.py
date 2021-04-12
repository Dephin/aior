import re

from setuptools import setup, find_packages

# in case of importing other dependencies
with open('aior/__init__.py', encoding='utf8') as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setup(
    name='aior',
    version=version,
    packages=find_packages(include=["aior*"]),
    url='',
    license='',
    author='Dephin',
    author_email='',
    description='.',
    install_requires=[
        'aiohttp>=3.6.2',
        'pydantic>=1.2',
    ],
    python_requires='>=3.7'
)
