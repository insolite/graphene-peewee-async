# Changelog

## Main versions

### [3.X.X (latest)](https://github.com/insolite/graphene-peewee-async/releases/tag/v3.0.0)

 * `Python>=3.5`
 * `peewee>=3.1`
 * `peewee-async>=0.6`
 * `graphene>=2.0`

### [2.X.X](https://github.com/insolite/graphene-peewee-async/releases/tag/v2.2.1)

 * `Python>=3.4`
 * `peewee>=2.10,<3`
 * `peewee-async>=0.5,<0.6`
 * `graphene>=2.0`

### [1.X.X](https://github.com/insolite/graphene-peewee-async/releases/tag/v1.0.7)

**Not maintained**

 * `Python>=3.4`
 * `peewee>=2.10,<3`
 * `peewee-async>=0.5,<0.6`
 * `graphene>=1.0,<2`

## Version history

### 3.0.0

**Backward-incompatible changes**

 * [[#12](https://github.com/insolite/graphene-peewee-async/issues/12)] Stop support of `peewee<3` and `Python<3.5`
   in order to support `peewee>=3`.
   This also requires `peewee-async>=0.6.0a0`
   to work with `peewee>=3`.

### 2.2.1

**Bugfixes**

 * [[#11](https://github.com/insolite/graphene-peewee-async/issues/11)]
   Restrict `promise` dependency version at `<2.2.1`
   as it breaks compatibility with Python 3.4.
 * [[7d5e8c](https://github.com/insolite/graphene-peewee-async/commit/379f77728787401dd6486811cacb4e85b47d5e8c#diff-498cf53d35427897613cdfc4b76fc6eaR5)]
   Fix Python 3.7 syntax compatibility issue (`async` keyword usage).

### 2.2.0

**Features, improvements**

 * [[b237d49](https://github.com/insolite/graphene-peewee-async/commit/b237d4985459c686c71814905b5ee2153d0d42f9)]
   Add ability to filter subset queries

**Bugfixes**

 * [[b237d49](https://github.com/insolite/graphene-peewee-async/commit/b237d4985459c686c71814905b5ee2153d0d42f9)]
   Fix sync queries at subset fetching.
   Allows to use `db.set_allow_sync(False)` along with _set fields.

### 2.1.4

**Bugfixes**

 * [[#8](https://github.com/insolite/graphene-peewee-async/issues/8)]
   Fix Pip 10 compatibility issues (stop using `requirements.txt`).

### TODO: decribe releases for this period

**Backward-incompatible changes**

**Features, improvements**

**Bugfixes**

### 2.0.0

**Backward-incompatible changes**

 * Stop support of `graphene<2` in order to support `graphene>=2`.
