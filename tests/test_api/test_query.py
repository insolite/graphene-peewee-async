from tests.common import ApiTest, Author, Book


class TestQuery(ApiTest):

    def test_query_one(self):
        author = self.loop.run_until_complete(
            self.manager.create(Author, name='foo', rating=42)
        )
        book = self.loop.run_until_complete(
            self.manager.create(Book, name='bar', year=2000, author=author)
        )

        result = self.loop.run_until_complete(self.query('''
            query {
                book (id: ''' + str(book.id) + ''') {
                    id
                    name
                    year
                    author {
                        id
                        name
                        rating
                    }
                }
            }
        '''))

        self.assertIsNone(result.errors)
        self.assertEqual(result.data, {'book': {'id': book.id,
                                                'name': book.name,
                                                'year': book.year,
                                                'author': {
                                                    'id': author.id,
                                                    'name': author.name,
                                                    'rating': author.rating}}})

    def test_query_many(self):
        author = self.loop.run_until_complete(
            self.manager.create(Author, name='foo', rating=42)
        )
        book1 = self.loop.run_until_complete(
            self.manager.create(Book, name='bar1', year=2001, author=author)
        )
        book2 = self.loop.run_until_complete(
            self.manager.create(Book, name='bar2', year=2002, author=author)
        )

        result = self.loop.run_until_complete(self.query('''
            query {
                books (filters: {author__rating: ''' + str(author.rating) + '''}, order_by: ["year"]) {
                    total
                    count
                    edges {
                        node {
                            id
                            name
                            year
                            author {
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
        self.assertEqual(result.data, {'books': {'count': 2,
                                                 'total': 2,
                                                 'edges': [
                                                     {'node': {'id': book1.id,
                                                               'name': book1.name,
                                                               'year': book1.year,
                                                               'author': {
                                                                   'id': author.id,
                                                                   'name': author.name,
                                                                   'rating': author.rating}}},
                                                     {'node': {'id': book2.id,
                                                               'name': book2.name,
                                                               'year': book2.year,
                                                               'author': {
                                                                   'id': author.id,
                                                                   'name': author.name,
                                                                   'rating': author.rating}}}]}})

    def test_filter_subset_query(self):
        author = self.loop.run_until_complete(
            self.manager.create(Author, name='foo', rating=42)
        )
        book1 = self.loop.run_until_complete(
            self.manager.create(Book, name='bar1', year=2001, author=author)
        )
        book2 = self.loop.run_until_complete(
            self.manager.create(Book, name='bar2', year=2002, author=author)
        )

        result = self.loop.run_until_complete(self.query('''
            query {
                authors {
                    count
                    total
                    edges {
                        node {
                            id
                            name
                            book_set (filters: {name: "bar1"}) {
                                count
                                total
                                edges {
                                    node {
                                        id
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            }
        '''))

        self.assertIsNone(result.errors)
        self.assertEqual(result.data, {'authors': {'count': 1,
                                                   'total': 1,
                                                   'edges': [
                                                       {'node': {'id': author.id,
                                                                 'name': author.name,
                                                                 'book_set': {
                                                                     'count': 1,
                                                                     'total': 1,
                                                                     'edges': [
                                                                         {'node': {'id': book1.id,
                                                                                   'name': book1.name}}]}}}]}})
