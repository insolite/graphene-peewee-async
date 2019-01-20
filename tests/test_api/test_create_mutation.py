from unittest.mock import ANY

from tests.common import ApiTest


class TestCreateMutation(ApiTest):

    def test_create_one(self):
        name = 'foo'
        rating = 42

        result = self.loop.run_until_complete(self.query('''
            mutation {
                create_author (name: "''' + name + '''", rating: ''' + str(rating) + ''') {
                    affected {
                        id
                        name
                        rating
                    }
                }
            }
        '''))

        self.assertIsNone(result.errors)
        self.assertIsInstance(result.data['create_author']['affected']['id'], int)
        self.assertEqual(
            result.data,
            {
                'create_author': {
                    'affected': {
                        'id': ANY,
                        'name': name,
                        'rating': rating
                    }
                }
            }
        )

    def test_create_many(self):
        name1 = 'foo'
        rating1 = 42
        name2 = 'bar'
        rating2 = 9000

        result = self.loop.run_until_complete(self.query('''
            mutation {
                create_authors (data: [{name: "''' + name1 + '''", rating: ''' + str(rating1) + '''}, {name: "''' + name2 + '''", rating: ''' + str(rating2) + '''}]) {
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
        for edge in result.data['create_authors']['affected']['edges']:
            self.assertIsInstance(edge['node']['id'], int)
        self.assertEqual(
            result.data,
            {
                'create_authors': {
                    'affected': {
                        'edges': [{
                            'node': {
                                'id': ANY,
                                'name': name1,
                                'rating': rating1
                            }
                        }, {
                            'node': {
                                'id': ANY,
                                'name': name2,
                                'rating': rating2
                            }
                        }]
                    }
                }
            }
        )

    def test_create_one__related(self):
        name = 'foo'
        rating = 42
        book_name = 'bar'
        book_year = 2000

        result = self.loop.run_until_complete(self.query('''
            mutation {
                create_author (
                    name: "''' + name + '''",
                    rating: ''' + str(rating) + '''
                    book_set: [{name: "''' + book_name + '''", year: ''' + str(book_year) + '''}]
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
        self.assertIsInstance(result.data['create_author']['affected']['id'], int)
        self.assertIsInstance(result.data['create_author']['affected']['book_set']['edges'][0]['node']['id'], int)
        self.assertEqual(
            result.data,
            {
                'create_author': {
                    'affected': {
                        'id': ANY,
                        'name': name,
                        'rating': rating,
                        'book_set': {
                            'edges': [{
                                'node': {
                                    'id': ANY,
                                    'name': book_name,
                                    'year': book_year
                                }
                            }]
                        }
                    }
                }
            }
        )
