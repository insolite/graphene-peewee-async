import re
import os
from setuptools import find_packages, setup


package_name = 'graphene_peewee_async'
hyphen_package_name = package_name.replace('_', '-')


def read_version():
    regexp = re.compile(r"^__version__\s*=\s*'([\d.abrc]+)'")
    init_py = os.path.join(os.path.dirname(__file__), package_name, '__init__.py')
    with open(init_py) as f:
        for line in f:
            match = regexp.match(line)
            if match is not None:
                return match.group(1)
        else:
            raise RuntimeError('Cannot find version in {}'.format(init_py))


setup(
    name=hyphen_package_name,
    version=read_version(),

    description='Graphene peewee-async integration',
    long_description=open('README.rst').read(),

    url='https://github.com/insolite/{}'.format(hyphen_package_name),

    author='Oleg Krasnikov',
    author_email='a.insolite@gmail.com',

    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],

    keywords='api graphql protocol rest relay graphene',

    packages=find_packages(exclude=['tests']),

    install_requires=[
        'graphene>=2.0',
        'peewee>=2.10,<3',
        'peewee_async>=0.5',
        'singledispatch>=3.4',
        'iso8601>=0.1',
    ],
    tests_require=[
        'inflection>=0.13',
        'aiopg>=0.3',
    ],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
)
