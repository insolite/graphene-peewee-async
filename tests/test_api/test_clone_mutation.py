from unittest.mock import ANY

from tests.common import ApiTest, Author, Book


class TestCloneMutation(ApiTest):

    def test_clone_one(self):
        author = self.loop.run_until_complete(
            self.manager.create(Author, name='foo', rating=42)
        )
        new_name = 'bar'

        result = self.loop.run_until_complete(self.query('''
            mutation {
                clone_author (
                    id: ''' + str(author.id) + ''',
                    data: {name: "''' + new_name + '''"}
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
        new_id = result.data['clone_author']['affected']['id']
        self.assertIsInstance(new_id, int)
        self.assertNotEqual(new_id, author.id)
        self.assertEqual(
            result.data,
            {
                'clone_author': {
                    'affected': {
                        'id': ANY,
                        'name': new_name,
                        'rating': author.rating
                    }
                }
            }
        )

    def test_clone_one__with_related(self):
        author = self.loop.run_until_complete(
            self.manager.create(Author, name='foo', rating=42)
        )
        book = self.loop.run_until_complete(
            self.manager.create(Book, name='bar', year=2000, author=author)
        )
        new_name = 'bar'

        result = self.loop.run_until_complete(self.query('''
            mutation {
                clone_author (
                    id: ''' + str(author.id) + ''',
                    data: {name: "''' + new_name + '''"},
                    related: ["book_set"]
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
                                    author_id
                                }
                            }
                        }
                    }
                }
            }
        '''))

        self.assertIsNone(result.errors)
        new_id = result.data['clone_author']['affected']['id']
        new_book_id = result.data['clone_author']['affected']['book_set']['edges'][0]['node']['id']
        self.assertIsInstance(new_id, int)
        self.assertIsInstance(new_book_id, int)
        self.assertNotEqual(new_id, author.id)
        self.assertNotEqual(new_book_id, book.id)
        self.assertEqual(
            result.data,
            {
                'clone_author': {
                    'affected': {
                        'id': ANY,
                        'name': new_name,
                        'rating': author.rating,
                        'book_set': {
                            'edges': [{
                                'node': {
                                    'id': ANY,
                                    'name': book.name,
                                    'author_id': new_id,
                                }
                            }]
                        }
                    }
                }
            }
        )
