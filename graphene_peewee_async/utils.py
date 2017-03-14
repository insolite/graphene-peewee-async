import inspect

import peewee
from graphql.utils.ast_to_dict import ast_to_dict
from graphene import List, Argument


DELIM = '__'


def get_type_for_model(schema, model):
    schema = schema
    types = schema.types.values()
    for _type in types:
        type_model = hasattr(_type, '_meta') and getattr(
            _type._meta, 'model', None)
        if model == type_model:
            return _type


def get_reverse_fields(model):
    fields = {}
    for name in model._meta.reverse_rel.keys():
        fields[name] = getattr(model, name)
    return fields


def maybe_query(value):
    # if isinstance(value, peewee.Query):
    #     return WrappedQuery(value)
    return value


def get_related_model(field):
    return field.rel_model


def is_valid_peewee_model(model):
    return inspect.isclass(model) and issubclass(model, peewee.Model)


def import_single_dispatch():
    try:
        from functools import singledispatch
    except ImportError:
        singledispatch = None

    if not singledispatch:
        try:
            from singledispatch import singledispatch
        except ImportError:
            pass

    if not singledispatch:
        raise Exception(
            "It seems your python version does not include "
            "functools.singledispatch. Please install the 'singledispatch' "
            "package. More information here: "
            "https://pypi.python.org/pypi/singledispatch"
        )

    return singledispatch


def collect_fields(node, fragments):
    """Recursively collects fields from the AST
    Args:
        node (dict): A node in the AST
        fragments (dict): Fragment definitions
    Returns:
        A dict mapping each field found, along with their sub fields.
        {'name': {},
         'sentimentsPerLanguage': {'id': {},
                                   'name': {},
                                   'totalSentiments': {}},
         'slug': {}}
    """

    field = {}

    if node.get('selection_set'):
        for leaf in node['selection_set']['selections']:
            if leaf['kind'] == 'Field':
                field.update({
                    leaf['name']['value']: collect_fields(leaf, fragments)
                })
            elif leaf['kind'] == 'FragmentSpread':
                field.update(collect_fields(fragments[leaf['name']['value']],
                                            fragments))

    return field


def get_fields(info):
    """A convenience function to call collect_fields with info
    Args:
        info (ResolveInfo)
    Returns:
        dict: Returned from collect_fields
    """

    fragments = {}
    node = ast_to_dict(info.field_asts[0])

    for name, value in info.fragments.items():
        fragments[name] = ast_to_dict(value)

    return collect_fields(node, fragments)


def get_arg_name(prefix, name, lookup):
    return '{}{}'.format(prefix,
                         (name + DELIM + lookup)
                         if lookup else name)


def get_filtering_args(model, filters, prefix=''):
    """ Inspect a model and produce the arguments to pass to
        a Graphene Field. These arguments will be available to
        filter against in the GraphQL
    """
    from .converter import convert_peewee_field

    all_lookups = list(peewee.DJANGO_MAP.keys())
    lookup_wrappers = {'in': List}

    fields = {}
    fields.update(model._meta.fields)
    # fields.update(get_reverse_fields(model))

    if filters is None:
        filters = list(fields.keys())
    if isinstance(filters, (list, tuple)):
        filters = {key: (None
                         if isinstance(fields[key], peewee.ForeignKeyField)
                         else all_lookups) for key in filters}

    result = {}
    for key, val in filters.items():
        field = fields[key]
        is_fkey = isinstance(field, peewee.ForeignKeyField)
        if is_fkey and model is not field.rel_model:
            extra = get_filtering_args(field.rel_model, val,
                                       '{}{}{}'.format(prefix, key, DELIM))
            result.update(extra)
            pk_field = field.rel_model._meta.primary_key
            for lookup in (all_lookups + ['']):
                field_name = '{}_{}'.format(key, pk_field.name)
                argument_name = get_arg_name(prefix, field_name, lookup)
                graphql_field = convert_peewee_field(pk_field)
                lookup_wrapper = lookup_wrappers.get(lookup)
                if lookup_wrapper:
                    graphql_field = lookup_wrapper(type(graphql_field))
                    argument = graphql_field.Argument()
                else:
                    argument = graphql_field.get_type()().Argument()
                result[argument_name] = argument
        elif not is_fkey:
            for lookup in (val + ['']):
                argument_name = get_arg_name(prefix, key, lookup)
                graphql_field = convert_peewee_field(field)
                lookup_wrapper = lookup_wrappers.get(lookup)
                if lookup_wrapper:
                    graphql_field = lookup_wrapper(type(graphql_field))
                    argument = graphql_field.Argument()
                else:
                    argument = graphql_field.get_type()().Argument()
                result[argument_name] = argument
    return result


def get_requested_models(fields, related_model):
    if 'edges' in fields.keys():
        fields = fields['edges']['node']
    models = []
    for key, val in fields.items():
        if val != {}:
            child_model = getattr(related_model, key).rel_model
            models.append((child_model, get_requested_models(val, child_model)))
    return models
