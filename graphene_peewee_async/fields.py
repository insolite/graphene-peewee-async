from functools import partial, reduce
import asyncio
import peewee
import operator
from peewee import fn, SQL, Clause, Node, DQ, Expression, deque, ForeignKeyField, FieldProxy, ReverseRelationDescriptor, OP, DJANGO_MAP, ModelAlias

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
MODELS_DELIMITER = '__'


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
    @asyncio.coroutine
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
        return cls.async_connection_resolver(resolver, connection, default_manager, root, args, context, info)

    def get_resolver(self, parent_resolver):
        return partial(self.connection_resolver, parent_resolver, self.type, self.get_manager())

    @classmethod
    def get_field(cls, model, full_name, alias_map={}):
        name, *args = full_name.split(MODELS_DELIMITER, 1)
        field = getattr(alias_map.get(model, model), name)
        if args: # Foreign key
            return cls.get_field(field.rel_model, args[0], alias_map)
        return field

    @classmethod
    def ensure_join(cls, query, lm, rm, on=None, **join_kwargs):
        ctx = query._query_ctx
        if isinstance(rm, ModelAlias):
            rm = rm.model_class
        for join in query._joins.get(lm, []):
            dest = join.dest
            if isinstance(dest, ModelAlias):
                dest = dest.model_class
            if dest == rm:
                return query
        return query.switch(lm).join(rm, on=on, **join_kwargs).switch(ctx)

    @classmethod
    def convert_dict_to_node(cls, query, qdict, alias_map={}):
        accum = []
        joins = []
        relationship = (ForeignKeyField, ReverseRelationDescriptor)
        for key, value in sorted(qdict.items()):
            curr = query.model_class
            if '__' in key and key.rsplit('__', 1)[1] in DJANGO_MAP:
                key, op = key.rsplit('__', 1)
                op = DJANGO_MAP[op]
            elif value is None:
                op = OP.IS
            else:
                op = OP.EQ
            for piece in key.split('__'):
                model_attr = getattr(curr, piece)
                if isinstance(model_attr, FieldProxy):
                    actual_model_attr = model_attr.field_instance
                else:
                    actual_model_attr = model_attr
                if value is not None and isinstance(actual_model_attr, relationship):
                    curr = model_attr.rel_model
                    curr = alias_map.get(curr, curr)
                    joins.append(model_attr)
            accum.append(Expression(model_attr, op, value))
        return accum, joins

    @classmethod
    def filter(cls, query, filters, alias_map={}):
        # normalize args and kwargs into a new expression
        # Note: This is a modified peewee's Query.filter method.
        # Inner methods convert_dict_to_node and ensure_join also changed.
        # That is done to support FieldProxy generated from aliases to prevent unnecessary joins (see issue link below).
        # https://github.com/coleifer/peewee/issues/1338
        if filters:
            dq_node = Node() & DQ(**filters)
        else:
            return query

        # dq_node should now be an Expression, lhs = Node(), rhs = ...
        q = deque([dq_node])
        dq_joins = set()
        while q:
            curr = q.popleft()
            if not isinstance(curr, Expression):
                continue
            for side, piece in (('lhs', curr.lhs), ('rhs', curr.rhs)):
                if isinstance(piece, DQ):
                    new_query, joins = cls.convert_dict_to_node(query, piece.query, alias_map)
                    dq_joins.update(joins)
                    expression = reduce(operator.and_, new_query)
                    # Apply values from the DQ object.
                    expression._negated = piece._negated
                    expression._alias = piece._alias
                    setattr(curr, side, expression)
                else:
                    q.append(piece)

        dq_node = dq_node.rhs

        new_query = query.clone()
        for field in dq_joins:
            if isinstance(field, (ForeignKeyField, FieldProxy)):
                lm, rm = field.model_class, field.rel_model
                field_obj = field
            elif isinstance(field, ReverseRelationDescriptor):
                lm, rm = field.field.rel_model, field.rel_model
                field_obj = field.field
            new_query = cls.ensure_join(new_query, lm, rm, field_obj)
        return new_query.where(dq_node)

    @classmethod
    def join(cls, query, models, src_model=None):
        src_model = src_model or query.model_class
        for model, child_models, requested_fields in models:
            query = query.select(*(query._select + requested_fields))
            query = query.switch(src_model)
            query = query.join(model, peewee.JOIN_LEFT_OUTER)  # TODO: on
            query = cls.join(query, child_models, model)
        return query

    @classmethod
    def order(cls, model, query, order, alias_map={}):
        if order:
            order_fields = []
            for order_item in order:
                if order_item.startswith(DESC_ORDER_CHAR):
                    order_item = order_item.lstrip(DESC_ORDER_CHAR)
                    order_field = cls.get_field(model, to_snake_case(order_item), alias_map).desc()
                else:
                    order_field = cls.get_field(model, to_snake_case(order_item), alias_map)
                order_fields.append(order_field)
            query = query.order_by(*order_fields)
        return query

    @classmethod
    def paginate(cls, query, page, paginate_by):
        if page and paginate_by:
            query = query.paginate(page, paginate_by)
        return query

    @classmethod
    def get_query(cls, model, args, info):
        if isinstance(model, (peewee.Model, peewee.BaseModel)):
            args = dict(args)
            order = args.pop(ORDER_BY_FIELD, []) # type._meta.order_by
            page = args.pop(PAGE_FIELD, None) # type._meta.page
            paginate_by = args.pop(PAGINATE_BY_FIELD, None) # type._meta.paginate_by
            alias_map = {}
            fields = get_fields(info)
            requested_model, requested_joins, requested_fields = get_requested_models(model, fields, alias_map, info.return_type.fields.keys())
            query = requested_model.select(*requested_fields)
            if not requested_fields:
                query._select = ()
            query = cls.join(query, requested_joins)
            query = cls.filter(query, args, alias_map)
            query = cls.order(requested_model, query, order, alias_map)
            query = cls.paginate(query, page, paginate_by)
            if page and paginate_by or 'total' in fields: # TODO: refactor 'total'
                total = Clause(fn.Count(SQL('*')),
                               fn.Over(), glue=' ').alias(TOTAL_FIELD)
                query._select = tuple(query._select) + (total,)
            if not query._select:
                query = query.select(SQL('1')) # bottleneck
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
