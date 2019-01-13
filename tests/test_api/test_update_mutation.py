import json
from unittest.mock import ANY

from tests.common import ApiTest, Author, Book


class TestUpdateMutation(ApiTest):

    def test_update_one(self):
        author = self.loop.run_until_complete(
            self.manager.create(Author, name='foo', rating=42)
        )
        new_name = 'bar'

        result = self.loop.run_until_complete(self.query('''
            mutation {
                update_author (
                    id: ''' + str(author.id) + ''',
                    name: "''' + new_name + '''"
                ) {
                    affected {
                        id
                        name
                        rating
                    }
                }
            }
        '''))

        self.assertIsNone(result.errors)
        self.assertEqual(
            result.data,
            {
                'update_author': {
                    'affected': {
                        'id': author.id,
                        'name': new_name,
                        'rating': author.rating
                    }
                }
            }
        )

    def test_update_many(self):
        author1 = self.loop.run_until_complete(
            self.manager.create(Author, name='foo', rating=42)
        )
        author2 = self.loop.run_until_complete(
            self.manager.create(Author, name='bar', rating=9000)
        )
        new_rating = 10

        result = self.loop.run_until_complete(self.query('''
            mutation {
                update_authors (
                    filters: {id__in: ''' + json.dumps([author1.id, author2.id]) + '''},
                    data: {rating: ''' + str(new_rating) + '''}
                ) {
                    affected {
                        edges {
                            node {
                                id
                                name
                                rating
                            }
                        }
                    }
                }
            }
        '''))

        self.assertIsNone(result.errors)
        self.assertEqual(
            result.data,
            {
                'update_authors': {
                    'affected': {
                        'edges': [{
                            'node': {
                                'id': author1.id,
                                'name': author1.name,
                                'rating': new_rating
                            }
                        },
                        {
                            'node': {
                                'id': author2.id,
                                'name': author2.name,
                                'rating': new_rating
                            }
                        }]
                    }
                }
            }
        )

    def test_update_many__deep_filter(self):
        author = self.loop.run_until_complete(
            self.manager.create(Author, name='foo', rating=42)
        )
        book = self.loop.run_until_complete(
            self.manager.create(Book, name='bar', year=2000, author=author)
        )
        new_year = 2001 # ^_^

        result = self.loop.run_until_complete(self.query('''
            mutation {
                update_books (
                    filters: {author__name: ''' + json.dumps([author.name]) + '''},
                    data: {year: ''' + str(new_year) + '''}
                ) {
                    affected {
                        edges {
                            node {
                                id
                                name
                                year
                            }
                        }
                    }
                }
            }
        '''))

        self.assertIsNone(result.errors)
        self.assertEqual(
            result.data,
            {
                'update_books': {
                    'affected': {
                        'edges': [{
                            'node': {
                                'id': book.id,
                                'name': book.name,
                                'year': new_year
                            }
                        }]
                    }
                }
            }
        )

    def test_update_one__related(self):
        author = self.loop.run_until_complete(
            self.manager.create(Author, name='foo', rating=42)
        )
        new_name = 'bar'
        new_book_name = 'Test'
        new_book_year = 2000

        result = self.loop.run_until_complete(self.query('''
            mutation {
                update_author (
                    id: ''' + str(author.id) + ''',
                    name: "''' + new_name + '''",
                    book_set: [{
                        name: "''' + new_book_name + '''",
                        year: ''' + str(new_book_year) + '''
                    }]
                ) {
                    affected {
                        id
                        name
                        rating
                        book_set {
                            edges {
                                node {
                                    id
                                    name
                                    year
                                }
                            }
                        }
                    }
                }
            }
        '''))

        self.assertIsNone(result.errors)
        self.assertIsInstance(result.data['update_author']['affected']['book_set']['edges'][0]['node']['id'], int)
        self.assertEqual(
            result.data,
            {
                'update_author': {
                    'affected': {
                        'id': author.id,
                        'name': new_name,
                        'rating': author.rating,
                        'book_set': {
                            'edges': [{
                                'node': {
                                    'id': ANY,
                                    'name': new_book_name,
                                    'year': new_book_year
                                }
                            }]
                        }
                    }
                }
            }
        )
