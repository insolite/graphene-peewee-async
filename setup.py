from setuptools import find_packages, setup

setup(
    name='graphene-peewee-async',
    version='1.0.1',

    description='Graphene peewee-async integration',
    long_description=open('README.rst').read(),

    url='https://github.com/insolite/graphene-peewee-async',

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
        'six>=1.10.0',
        'graphene>=1.0',
        'peewee_async',
        'iso8601',
        'singledispatch>=3.4.0.3',
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
        'mock',
    ],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
)
