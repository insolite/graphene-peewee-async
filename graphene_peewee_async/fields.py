import asyncio
from functools import partial

from graphene import Field, List, ConnectionField, Argument, String, Int, Connection
from graphene.types.generic import GenericScalar
from peewee import Query

from .queries import get_query, TOTAL_FIELD


FILTERS_FIELD = 'filters'
ORDER_BY_FIELD = 'order_by'
PAGE_FIELD = 'page'
PAGINATE_BY_FIELD = 'paginate_by'


class PeeweeConnection(Connection):

    count = Int()
    total = Int()

    def resolve_count(self, info, **args):
        return len(self.edges)

    def resolve_total(self, info, **args):
        if self.edges:
            result = getattr(self.edges[0].node, TOTAL_FIELD, None)
            if result is None:
                return len(self.edges)
            return result
        return 0

    class Meta:
        abstract = True


class PeeweeNodeField(Field):

    def __init__(self, type, *args, **kwargs):
        self.primary_key_name = type._meta.model._meta.primary_key.name
        kwargs.update({
            self.primary_key_name: Int(), # required=True
            # FILTERS_FIELD: Argument(GenericScalar),
        })
        super(PeeweeNodeField, self).__init__(
            type,
            *args,
            **kwargs
        )

    @asyncio.coroutine
    def node_resolver(self, resolver, root, info, **args):
        query = resolver(root, info, **args)
        if query is None:
            # filters = args.get(FILTERS_FIELD, {})
            query = yield from self._type.get_node(info, args[self.primary_key_name])
        return query

    def get_resolver(self, parent_resolver):
        return super().get_resolver(partial(self.node_resolver, parent_resolver))


class PeeweeConnectionField(ConnectionField):

    def __init__(self, type, *args, **kwargs):
        kwargs.update({
            FILTERS_FIELD: Argument(GenericScalar),
            ORDER_BY_FIELD: Argument(List(String)),
            PAGE_FIELD: Argument(Int),
            PAGINATE_BY_FIELD: Argument(Int),
        })
        super(PeeweeConnectionField, self).__init__(type, *args, **kwargs)

    @property
    def model(self):
        return self.type._meta.node._meta.model

    @property
    def manager(self):
        return self.type._meta.node._meta.manager

    @asyncio.coroutine
    def query_resolver(self, resolver, root, info, **args):
        query = resolver(root, info, **args)
        if query is None or isinstance(query, Query):
            if query is None:
                query = self.model
            filters = args.get(FILTERS_FIELD, {})
            order_by = args.get(ORDER_BY_FIELD, [])
            page = args.get(PAGE_FIELD, None)
            paginate_by = args.get(PAGINATE_BY_FIELD, None)
            query = get_query(query, info, filters=filters, order_by=order_by,
                              page=page, paginate_by=paginate_by)
            query = (yield from self.manager.execute(query))
        return query

    def get_resolver(self, parent_resolver):
        return super().get_resolver(partial(self.query_resolver, parent_resolver))


class PeeweeListField(Field):

    def __init__(self, _type, *args, **kwargs):
        super(PeeweeListField, self).__init__(List(_type), *args, **kwargs)
