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
                clone_author (id: ''' + str(author.id) + ''', data: {name: "''' + new_name + '''"}) {
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
        self.assertEqual(result.data,
                         {'clone_author': {'affected': {'id': ANY,
                                                        'name': new_name,
                                                        'rating': author.rating}}})

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
                clone_author (id: ''' + str(author.id) + ''', data: {name: "''' + new_name + '''"}, related: ["book_set"]) {
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
        self.assertEqual(result.data,
                         {'clone_author': {'affected': {'id': ANY,
                                                        'name': new_name,
                                                        'rating': author.rating}}})
