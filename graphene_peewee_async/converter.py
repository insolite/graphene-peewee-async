import peewee

from graphene import Enum, Field, ID, Boolean, Float, Int, String, Dynamic, is_node
from graphene.types.datetime import DateTime
from graphene.utils.str_converters import to_const

from.fields import PeeweeListField, PeeweeConnectionField
from .utils import get_related_model, import_single_dispatch


singledispatch = import_single_dispatch()


def convert_choices(choices):
    for value, name in choices:
        if isinstance(name, (tuple, list)):
            for choice in convert_choices(name):
                yield choice
        else:
            yield to_const(str(name)), value


def get_foreign_key_id_field(field):
    if isinstance(field, peewee.ForeignKeyField):
        return Int(description=field.help_text)


def convert_peewee_field_with_choices(field, registry=None):
    choices = getattr(field, 'choices', None)
    if choices:
        meta = field.model_class._meta
        name = '{}_{}'.format(meta.name, field.name)
        graphql_choices = list(convert_choices(choices))
        return Enum(name.upper(), graphql_choices, description=field.help_text)
    return convert_peewee_field(field, registry)


def add_nonnull_to_field(convert_field, registry=None):
    return convert_field


@singledispatch
def convert_peewee_field(field, registry=None):
    raise Exception(
        "Don't know how to convert the Peewee field %s (%s)" %
        (field, field.__class__))


@convert_peewee_field.register(peewee.CharField)
@convert_peewee_field.register(peewee.TextField)
@convert_peewee_field.register(peewee.FixedCharField)
@convert_peewee_field.register(peewee.BlobField)
@convert_peewee_field.register(peewee.TimeField)
@convert_peewee_field.register(peewee.UUIDField)
@add_nonnull_to_field
def convert_field_to_string(field, registry=None):
    return String(description=field.help_text)


@convert_peewee_field.register(peewee.PrimaryKeyField)
@add_nonnull_to_field
def convert_field_to_id(field, registry=None):
    return ID(description=field.help_text, required=True)


@convert_peewee_field.register(peewee.SmallIntegerField)
@convert_peewee_field.register(peewee.BigIntegerField)
@convert_peewee_field.register(peewee.IntegerField)
@convert_peewee_field.register(peewee.TimestampField)
@add_nonnull_to_field
def convert_field_to_int(field, registry=None):
    return Int(description=field.help_text)


@convert_peewee_field.register(peewee.BooleanField)
def convert_field_to_nullboolean(field, registry=None):
    return Boolean(description=field.help_text)


@convert_peewee_field.register(peewee.DecimalField)
@convert_peewee_field.register(peewee.FloatField)
@add_nonnull_to_field
def convert_field_to_float(field, registry=None):
    return Float(description=field.help_text)


@convert_peewee_field.register(peewee.DateField)
@convert_peewee_field.register(peewee.DateTimeField)
@add_nonnull_to_field
def convert_date_to_string(field, registry=None):
    return DateTime(description=field.help_text)


@convert_peewee_field.register(peewee.ReverseRelationDescriptor)
def convert_field_to_list_or_connection(field, registry=None):
    model = get_related_model(field)

    def dynamic_type():
        _type = registry.get_type_for_model(model)
        if not _type:
            return

        if is_node(_type):
            return PeeweeConnectionField(_type)

        return PeeweeListField(_type)

    return Dynamic(dynamic_type)


@convert_peewee_field.register(peewee.ForeignKeyField)
@add_nonnull_to_field
def convert_field_to_peeweemodel(field, registry=None):
    model = get_related_model(field)
    def dynamic_type():
        _type = registry.get_type_for_model(model)
        if not _type:
            return

        return Field(_type, description=field.help_text, required=not field.null)
    return Dynamic(dynamic_type)
