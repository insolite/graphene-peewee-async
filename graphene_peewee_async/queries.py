import operator
from functools import reduce

from peewee import (
    fn, SQL, Clause, Node, DQ, Expression, deque, ForeignKeyField, FieldProxy, ReverseRelationDescriptor,
    OP, DJANGO_MAP, ModelAlias, JOIN_LEFT_OUTER, Model, BaseModel, IntegerField, CharField, Query
)
from graphene.utils.str_converters import to_snake_case

from .utils import get_requested_models, get_field_from_selections


TOTAL_FIELD = '__total__'
MODELS_DELIMITER = '__'
DESC_ORDER_CHAR = '-'


def get_field(model, full_name, alias_map={}):
    name, *args = full_name.split(MODELS_DELIMITER, 1)
    field = getattr(alias_map.get(model, model), name)
    if args:  # Foreign key
        return get_field(field.rel_model, args[0], alias_map)
    return field


def ensure_join(query, lm, rm, on=None, **join_kwargs):
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


def convert_dict_to_node(query, qdict, alias_map={}):
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


def filter(query, filters, alias_map={}):
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
                new_query, joins = convert_dict_to_node(query, piece.query, alias_map)
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
        new_query = ensure_join(new_query, lm, rm, field_obj)
    return new_query.where(dq_node)


def join(query, models, src_model=None):
    src_model = src_model or query.model_class
    for model, child_models, requested_fields in models:
        query = query.select(*(query._select + requested_fields))
        query = query.switch(src_model)
        query = query.join(model, JOIN_LEFT_OUTER)  # TODO: on
        query = join(query, child_models, model)
    return query


def order(model, query, order, alias_map={}):
    if order:
        order_fields = []
        for order_item in order:
            if order_item.startswith(DESC_ORDER_CHAR):
                order_item = order_item.lstrip(DESC_ORDER_CHAR)
                order_field = get_field(model, to_snake_case(order_item), alias_map).desc()
            else:
                order_field = get_field(model, to_snake_case(order_item), alias_map)
            order_fields.append(order_field)
        query = query.order_by(*order_fields)
    return query


def paginate(query, page, paginate_by):
    if page and paginate_by:
        query = query.paginate(page, paginate_by)
    return query


def get_query(model, info, filters={}, order_by=[], page=None, paginate_by=None, total_query=None):
    query = None
    if isinstance(model, Query):
        query = model
        model = query.model_class
    if isinstance(model, (Model, BaseModel)):
        alias_map = {}
        selections = next(field for field in info.field_asts if field.name.value == info.field_name).selection_set.selections
        requested_model, requested_joins, requested_fields = get_requested_models(model, selections, alias_map)
        if query is None:
            query = requested_model.select(*requested_fields)
        if not requested_fields:
            query._select = ()
        query = join(query, requested_joins)
        query = filter(query, filters, alias_map)
        query = order(requested_model, query, order_by, alias_map)
        query = paginate(query, page, paginate_by)
        if page and paginate_by or get_field_from_selections(selections, 'total'):  # TODO: refactor 'total'
            if total_query:
                total = Clause(total_query).alias(TOTAL_FIELD)
            else:
                total = Clause(fn.Count(SQL('*')),
                               fn.Over(), glue=' ').alias(TOTAL_FIELD)
            query._select = tuple(query._select) + (total,)
        if not query._select:
            query = query.select(SQL('1'))  # bottleneck
        # query = query.aggregate_rows()
        return query
    return model
