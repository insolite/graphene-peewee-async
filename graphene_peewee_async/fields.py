from functools import partial
import asyncio
import peewee
from peewee import fn, SQL, Clause

from graphql_relay.connection.arrayconnection import connection_from_list_slice
from graphene import Field, List, ConnectionField, is_node, Argument, String, Int, PageInfo, Connection
from graphene.utils.str_converters import to_snake_case
from .utils import (
    get_type_for_model, maybe_query, get_fields, get_filtering_args,
    get_requested_models
)


ORDER_BY_FIELD = 'order_by'
PAGE_FIELD = 'page'
PAGINATE_BY_FIELD = 'paginate_by'
TOTAL_FIELD = '__total__'
DESC_ORDER_CHAR = '-'


class PeeweeConnectionField(ConnectionField):

    def __init__(self, type,
                 filters=None,
                 # order_by=None,
                 # page=None, paginate_by=None,
                 *args, **kwargs):
        node = type
        if issubclass(node, Connection):
            node = node._meta.node
        filters_args = get_filtering_args(node._meta.model,
                                          filters or node._meta.filters)
        # self.order_by = order_by or type._meta.order_by
        # self.page = page or type._meta.page
        # self.paginate_by = paginate_by or type._meta.paginate_by
        self.args = {}
        self.args.update(filters_args)
        self.args.update({ORDER_BY_FIELD: Argument(List(String)),
                          PAGE_FIELD: Argument(Int),
                          PAGINATE_BY_FIELD: Argument(Int)})
        kwargs.setdefault('args', {})
        kwargs['args'].update(**self.args)

        self.on = kwargs.pop('on', False)
        super(PeeweeConnectionField, self).__init__(type, *args, **kwargs)

    @property
    def model(self):
        return self.type._meta.node._meta.model

    def get_manager(self):
        if self.on:
            return getattr(self.model, self.on)
        else:
            return self.model

    @classmethod
    def async_connection_resolver(cls, resolver, connection, default_manager, root, args, context, info):
        iterable = resolver(root, args, context, info)
        if iterable is None:
            iterable = default_manager
        model = iterable
        query = cls.get_query(model, args, info)
        iterable = yield from iterable._meta.manager.execute(query)
        if False: #isinstance(iterable, QuerySet):
            _len = iterable.count()
        else:
            _len = len(iterable)
        connection = connection_from_list_slice(
            iterable,
            args,
            slice_start=0,
            list_length=_len,
            list_slice_length=_len,
            connection_type=connection,
            edge_type=connection.Edge,
            pageinfo_type=PageInfo,
        )
        connection.iterable = iterable
        connection.length = _len
        return connection

    @classmethod
    def connection_resolver(cls, resolver, connection, default_manager, root, args, context, info):
        return asyncio.async(
            PeeweeConnectionField.async_connection_resolver(resolver, connection, default_manager, root, args, context, info)
        )

    def get_resolver(self, parent_resolver):
        return partial(self.connection_resolver, parent_resolver, self.type, self.get_manager())

    @classmethod
    def get_field(cls, model, name):
        return getattr(model, name)

    @classmethod
    def filter(cls, query, args):
        if args:
            query = query.filter(**args)
        return query

    @classmethod
    def join(cls, query, models, src_model=None):
        src_model = src_model or query.model_class
        for model, child_models in models:
            model_alias = model.alias()
            query = query.select(model_alias, *query._select)
            query = query.switch(src_model)
            query = query.join(model_alias, peewee.JOIN_LEFT_OUTER)  # TODO: on
            query = cls.join(query, child_models, model_alias)
        return query

    @classmethod
    def order(cls, model, query, order):
        if order:
            order_fields = []
            for order_item in order:
                if order_item.startswith(DESC_ORDER_CHAR):
                    order_item = order_item.lstrip(DESC_ORDER_CHAR)
                    order_field = cls.get_field(model, to_snake_case(order_item)).desc()
                else:
                    order_field = cls.get_field(model, to_snake_case(order_item))
                order_fields.append(order_field)
            query = query.order_by(*order_fields)
        return query

    @classmethod
    def paginate(cls, query, page, paginate_by):
        if page and paginate_by:
            query = query.paginate(page, paginate_by)
            total = Clause(fn.Count(SQL('*')),
                           fn.Over(), glue=' ').alias(TOTAL_FIELD)
            query._select = tuple(query._select) + (total,)
        return query

    @classmethod
    def get_query(cls, model, args, info):
        if isinstance(model, (peewee.Model, peewee.BaseModel)):
            args = dict(args)
            order = args.pop(ORDER_BY_FIELD, []) # type._meta.order_by
            page = args.pop(PAGE_FIELD, None) # type._meta.page
            paginate_by = args.pop(PAGINATE_BY_FIELD, None) # type._meta.paginate_by
            requested_models = get_requested_models(get_fields(info), model)
            query = model.select(model)
            query = cls.join(query, requested_models)
            query = cls.filter(query, args)
            query = cls.order(model, query, order)
            query = cls.paginate(query, page, paginate_by)
            query = query.aggregate_rows()
            return query
        return model


class PeeweeListField(Field):

    def __init__(self, _type, *args, **kwargs):
        super(PeeweeListField, self).__init__(List(_type), *args, **kwargs)

    @property
    def model(self):
        return self.type.of_type._meta.node._meta.model

    @staticmethod
    def list_resolver(resolver, root, args, context, info):
        return maybe_query(resolver(root, args, context, info))

    def get_resolver(self, parent_resolver):
        return partial(self.list_resolver, parent_resolver)
