=====================
graphene-peewee-async
=====================

`graphene <https://github.com/graphql-python/graphene>`_ + `peewee-async <https://github.com/05bit/peewee-async>`_ integration :heart:

`Changelog <https://github.com/insolite/graphene-peewee-async/blob/master/CHANGELOG.md>`_

Features
========

- Querying
    - Fields selection (considered by ``SELECT`` statement)
    - Related entities subselection (using foreign key joins)
    - Filters (django-style lookups, like ``peewee.SelectQuery.filter`` args)
    - Order (multiple fields, asc/dsc support)
    - Pagination (``page``, ``paginate_by`` support plus unpaginated ``total`` count auto-fetching)
- Mutations (both single object and bulk operating, filtering just like for querying)
    - Create
    - Update
    - Delete
    - Clone


Usage sample
============

.. code-block:: python

    # Define models

    class Author(Model):
        name = CharField()
        rating = IntegerField()

    class Book(Model):
        name = CharField()
        year = IntegerField()
        author = ForeignKeyField(Author)

    # Create nodes

    class BookNode(PeeweeObjectType):
        class Meta:
            model = Book
            manager = db_manager

    class AuthorNode(PeeweeObjectType):
        class Meta:
            model = Author
            manager = db_manager

    # Create connections

    class BookConnection(PeeweeConnection):
        class Meta:
            node = BookNode

    # Aggregate queries

    class Query(ObjectType):
        books = PeeweeConnectionField(BookConnection)

    # Create schema

    schema = Schema(query=Query, auto_camelcase=False)

    # Execute graphql query

    result = schema.execute('''
        query {
            books (filters: {author__name__ilike: "%Lovecraft%"}) {
                total
                edges {
                    node {
                        id
                        name
                        author {
                            id
                            name
                        }
                    }
                }
            }
        }''',
        return_promise=True,
        executor=AsyncioExecutor()
    )

    # Await result if required (failed queries are usually returning result
    #                           synchronously with non-empty `result.errors`
    #                           while successful ones requires awaiting
    #                           of peewee/DB level queries of course)

    if not isinstance(result, ExecutionResult):
        result = await result

    # Enjoy the result :)

    print(result.data)
    #
    # ===>
    #
    # {'books': {
    #     'total': 2,
    #     'edges': [
    #         {'node': {
    #             'id': 5,
    #             'name': 'Dagon',
    #             'author': {
    #                 'id': 1,
    #                 'name': 'Howard Lovecraft'
    #             }
    #         }},
    #         {'node': {
    #             'id': 6,
    #             'name': 'At the Mountains of Madness',
    #             'author': {
    #                 'id': 1,
    #                 'name': 'H.P. Lovecraft'
    #             }
    #         }}
    #     ]
    # }}


Advanced usage
==============

Be sure to check `API tests <https://github.com/insolite/graphene-peewee-async/tree/master/tests/test_api>`_
for advanced query/mutation usages and
`auto-generating <https://github.com/insolite/graphene-peewee-async/blob/master/tests/common/schema.py>`_
such schema for them.

Install
=======

Install as package:

.. code-block:: bash

    pip3 install graphene-peewee-async
