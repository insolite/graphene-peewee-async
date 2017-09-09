import asyncio
import operator
from functools import partial, reduce

from peewee import (
    fn, SQL, Clause, Node, DQ, Expression, deque, ForeignKeyField, FieldProxy, ReverseRelationDescriptor,
    OP, DJANGO_MAP, ModelAlias, JOIN_LEFT_OUTER, Model, BaseModel
)
from graphene import Field, List, ConnectionField, is_node, Argument, String, Int, PageInfo, Connection, Context
from graphene.types.generic import GenericScalar
from graphene.utils.str_converters import to_snake_case

from .utils import maybe_query, get_fields, get_requested_models


FILTERS_FIELD = 'filters'
ORDER_BY_FIELD = 'order_by'
PAGE_FIELD = 'page'
PAGINATE_BY_FIELD = 'paginate_by'
TOTAL_FIELD = '__total__'
DESC_ORDER_CHAR = '-'
MODELS_DELIMITER = '__'


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


class PeeweeConnectionField(ConnectionField):

    def __init__(self, type, *args, **kwargs):
        kwargs.update({
            FILTERS_FIELD: Argument(GenericScalar),
            ORDER_BY_FIELD: Argument(List(String)),
            PAGE_FIELD: Argument(Int),
            PAGINATE_BY_FIELD: Argument(Int)
        })
        super(PeeweeConnectionField, self).__init__(type, *args, **kwargs)

    @property
    def model(self):
        return self.type._meta.node._meta.model

    @asyncio.coroutine
    def query_resolver(self, resolver, root, info, **args):
        query = resolver(root, info, **args)
        if query is None:
            query = self.get_query(self.model, args, info)
        return (yield from self.model._meta.manager.execute(query))

    def get_resolver(self, parent_resolver):
        return super().get_resolver(partial(self.query_resolver, parent_resolver))

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
            query = query.join(model, JOIN_LEFT_OUTER)  # TODO: on
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
        if isinstance(model, (Model, BaseModel)):
            filters = args.get(FILTERS_FIELD, {})
            order = args.get(ORDER_BY_FIELD, []) # type._meta.order_by
            page = args.get(PAGE_FIELD, None)
            paginate_by = args.get(PAGINATE_BY_FIELD, None) # type._meta.paginate_by
            alias_map = {}
            fields = get_fields(info)
            requested_model, requested_joins, requested_fields = get_requested_models(model, fields, alias_map, info.return_type.fields.keys())
            query = requested_model.select(*requested_fields)
            if not requested_fields:
                query._select = ()
            query = cls.join(query, requested_joins)
            query = cls.filter(query, filters, alias_map)
            query = cls.order(requested_model, query, order, alias_map)
            query = cls.paginate(query, page, paginate_by)
            if page and paginate_by or 'total' in fields: # TODO: refactor 'total'
                total = Clause(fn.Count(SQL('*')),
                               fn.Over(), glue=' ').alias(TOTAL_FIELD)
                query._select = tuple(query._select) + (total,)
            if not query._select:
                query = query.select(SQL('1')) # bottleneck
            # query = query.aggregate_rows()
            return query
        return model


class PeeweeListField(Field):

    def __init__(self, _type, *args, **kwargs):
        super(PeeweeListField, self).__init__(List(_type), *args, **kwargs)

    @property
    def model(self):
        return self.type.of_type._meta.node._meta.model

    @staticmethod
    def list_resolver(resolver, root, info, **args):
        return maybe_query(resolver(root, info, **args))

    def get_resolver(self, parent_resolver):
        return partial(self.list_resolver, parent_resolver)
