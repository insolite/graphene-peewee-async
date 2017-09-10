import asyncio
from collections import OrderedDict

from graphene import ObjectType, Field
from graphene.types.objecttype import ObjectTypeOptions
from graphene.types.utils import yank_fields_from_attrs

from .queries import get_query
from .registry import Registry, get_global_registry
from .converter import convert_peewee_field_with_choices, get_foreign_key_id_field
from .utils import get_reverse_fields, is_valid_peewee_model


def get_foreign_key_field_name(field_name):
    return '{}_id'.format(field_name)


def construct_fields(model, registry):
    reverse_fields = get_reverse_fields(model)
    all_fields = {field.name: field
                  for field in model._meta.declared_fields}
    all_fields.update(reverse_fields)

    fields = OrderedDict()
    for name, field in all_fields.items():
        converted_field = convert_peewee_field_with_choices(field, registry)
        fields[name] = converted_field
        foreign_field = get_foreign_key_id_field(field)
        if foreign_field:
            fields[get_foreign_key_field_name(field.name)] = foreign_field
    return fields


class PeeweeOptions(ObjectTypeOptions):

    registry = None
    model = None


class PeeweeObjectType(ObjectType):

    @classmethod
    def __init_subclass_with_meta__(cls, registry=None, model=None, **options):
        if not registry:
            registry = get_global_registry()
        assert isinstance(registry, Registry), (
            'The attribute registry in {}.Meta needs to be an instance of '
            'Registry, received "{}".'
        ).format(cls._meta.name, registry)
        assert is_valid_peewee_model(model), (
            'You need to pass a valid Peewee Model in {}.Meta, received "{}".'
        ).format(cls._meta.name, model)
        _meta = PeeweeOptions(cls)
        _meta.registry = registry
        _meta.model = model
        _meta.fields = yank_fields_from_attrs(
            construct_fields(model, registry),
            _as=Field,
        )

        super(PeeweeObjectType, cls).__init_subclass_with_meta__(_meta=_meta, **options)

        registry.register(cls)
        return cls

    @classmethod
    def resolve_id(cls, root, info, **args):
        return root.get_id()

    @classmethod
    def is_type_of(cls, root, info, **args):
        if isinstance(root, cls):
            return True
        if not is_valid_peewee_model(type(root)):
            raise Exception((
                'Received incompatible instance "{}".'
            ).format(root))
        model = root._meta.model_class
        return model == cls._meta.model

    @classmethod
    @asyncio.coroutine
    def async_get_node(cls, info, id):
        model = cls._meta.model
        try:
            return (yield from model._meta.manager.get(get_query(model, info, filters={'id': id})))
        except model.DoesNotExist:
            return None

    @classmethod
    def get_node(cls, info, id):
        return cls.async_get_node(info, id)
