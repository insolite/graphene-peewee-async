import inspect

from peewee import Model, ReverseRelationDescriptor


DELIM = '__'


def get_reverse_fields(model):
    fields = {}
    for name in model._meta.reverse_rel.keys():
        fields[name] = getattr(model, name)
    return fields


def is_valid_peewee_model(model):
    return inspect.isclass(model) and issubclass(model, Model)


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


def get_arg_name(prefix, name, lookup):
    return '{}{}'.format(prefix,
                         (name + DELIM + lookup)
                         if lookup else name)


def get_field_from_selections(selections, name):
    try:
        return next(field for field in selections if field.name.value == name)
    except StopIteration:
        return None


def get_requested_models(related_model, selections, alias_map={}):

    # TODO: edges/nodes unfolding below is a workaround, refactor ASAP
    edges_field = get_field_from_selections(selections, 'edges')
    if edges_field:
        selections = edges_field.selection_set.selections[0].selection_set.selections
    elif get_field_from_selections(selections, 'total') or get_field_from_selections(selections, 'count'):
        selections = []

    models = []
    fields = []
    alias = related_model.alias()
    alias_map[related_model] = alias
    for f in selections:
        f_name = f.name.value
        field = getattr(alias, f_name)
        if not isinstance(field, ReverseRelationDescriptor):
            if f.selection_set:
                child_model = field.rel_model
                models.append(get_requested_models(child_model, f.selection_set.selections, alias_map))
            fields.append(field)
    return alias, models, fields
