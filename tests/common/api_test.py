import asyncio
import json

from peewee_async import Manager

from graphql.execution import ExecutionResult

from .models import db, Book, Author
from .base_test import BaseTest
from .schema import generate_schema


class ApiTest(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = Manager(db, loop=cls.loop)
        cls.loop.run_until_complete(cls.manager.connect())
        cls.schema, cls.executor = generate_schema(cls.manager, [Book, Author])

    def setUp(self):
        self.loop.run_until_complete(
            self.manager.execute(Book.delete())
        )
        self.loop.run_until_complete(
            self.manager.execute(Author.delete())
        )

    @asyncio.coroutine
    def query(self, query, variables={}):
        pre_result = self.schema.execute(
            query,
            variable_values=variables,
            return_promise=True,
            executor=self.executor
        )
        if isinstance(pre_result, ExecutionResult):
            result = pre_result
        else:
            result = yield from pre_result
        # TODO: better way to convert OrderedDict to simple dict
        dumped_data = json.dumps(result.data)
        result.data = json.loads(dumped_data)
        return result
