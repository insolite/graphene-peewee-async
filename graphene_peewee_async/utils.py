import inspect

import peewee
from graphql.utils.ast_to_dict import ast_to_dict


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


def get_requested_models(related_model, field_names, alias_map={}, except_fields=()):
    # TODO: This function is full of workarounds like edges/nodes unfold and except_fields. Rewrite ASAP!
    if 'edges' in field_names.keys():
        field_names = field_names['edges']['node']
    models = []
    fields = []
    alias = related_model.alias()
    alias_map[related_model] = alias
    for key, child_fields in field_names.items():
        if key not in except_fields:
            field = getattr(alias, key)
            if child_fields != {}:
                child_model = field.rel_model
                models.append(get_requested_models(child_model, child_fields, alias_map))
            fields.append(field)
    return alias, models, fields
