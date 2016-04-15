from setuptools import setup

setup(
    name = 'depresolve',
    version = '0.4',
    description = 'Package dependency scraping, dependency conflict detection, and dependency conflict resolution, for PyPI, integrating with pip.',
    author = 'Sebastien Awwad',
    author_email = 'sebastien.awwad@gmail.com',
    url = 'https://github.com/awwad/depresolve',
    install_requires = ['six'],
    keywords = 'update updater pypi dependency dependencies',
    packages = ['depresolve']
)


