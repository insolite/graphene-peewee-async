import asyncio
from collections import OrderedDict

import six

from graphene import ObjectType, Field
from graphene.types.objecttype import ObjectTypeMeta
from graphene.types.options import Options
from graphene.types.utils import merge, yank_fields_from_attrs
from graphene.utils.is_base_type import is_base_type

from .registry import Registry, get_global_registry
from .converter import convert_peewee_field_with_choices, get_foreign_key_id_field
from .utils import get_reverse_fields, is_valid_peewee_model


def get_foreign_key_field_name(field_name):
    return '{}_id'.format(field_name)


def construct_fields(options):
    only_fields = options.only_fields
    reverse_fields = get_reverse_fields(options.model)
    all_fields = {field.name: field
                  for field in options.model._meta.declared_fields}
    all_fields.update(reverse_fields)
    already_created_fields = {f.attname for f in options.local_fields}

    fields = OrderedDict()
    for name, field in all_fields.items():
        is_not_in_only = only_fields and name not in only_fields
        is_already_created = name in already_created_fields
        is_excluded = ((name in options.exclude_fields)
                       or is_already_created)
        if is_not_in_only or is_excluded:
            # We skip this field if we specify only_fields and is not
            # in there. Or when we exclude this field in exclude_fields
            continue
        converted_field = convert_peewee_field_with_choices(field, options.registry)
        fields[name] = converted_field
        foreign_field = get_foreign_key_id_field(field)
        if foreign_field:
            fields[get_foreign_key_field_name(field.name)] = foreign_field
    return fields


class PeeweeObjectTypeMeta(ObjectTypeMeta):

    @staticmethod
    def __new__(cls, name, bases, attrs):
        # Also ensure initialization is only performed for subclasses of
        if not is_base_type(bases, PeeweeObjectTypeMeta):
            return type.__new__(cls, name, bases, attrs)

        defaults = dict(
            name=name,
            description=attrs.pop('__doc__', None),
            model=None,
            local_fields=None,
            only_fields=(),
            exclude_fields=(),
            interfaces=(),
            filters=None,
            order_by=None,
            page=None,
            paginate_by=None,
            registry=None
        )

        options = Options(
            attrs.pop('Meta', None),
            **defaults
        )
        if not options.registry:
            options.registry = get_global_registry()
        assert isinstance(options.registry, Registry), (
            'The attribute registry in {}.Meta needs to be an instance of '
            'Registry, received "{}".'
        ).format(name, options.registry)
        assert is_valid_peewee_model(options.model), (
            'You need to pass a valid Peewee Model in {}.Meta, received "{}".'
        ).format(name, options.model)

        cls = ObjectTypeMeta.__new__(cls, name, bases, dict(attrs, _meta=options))

        options.registry.register(cls)

        options.peewee_fields = yank_fields_from_attrs(
            construct_fields(options),
            _as=Field,
        )
        options.fields = merge(
            options.interface_fields,
            options.peewee_fields,
            options.base_fields,
            options.local_fields
        )

        return cls


class PeeweeObjectType(six.with_metaclass(
        PeeweeObjectTypeMeta, ObjectType)):

    def resolve_id(self, args, context, info):
        return self.get_id()

    @classmethod
    def is_type_of(cls, root, context, info):
        # if isinstance(root, SimpleLazyObject):
        #     root._setup()
        #     root = root._wrapped
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
    def async_get_node(cls, id, context, info):
        model = cls._meta.model
        try:
            return (yield from model._meta.manager.get(model, id=id))
        except model.DoesNotExist:
            return None

    @classmethod
    def get_node(cls, id, context, info):
        return asyncio.async(cls.async_get_node(id, context, info))
