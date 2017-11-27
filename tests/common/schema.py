import asyncio
import re

import inflection
from graphene import Schema, ObjectType
from graphql.execution.executors.asyncio import AsyncioExecutor

from graphene_peewee_async.fields import PeeweeNodeField, PeeweeConnectionField, PeeweeConnection
from graphene_peewee_async.registry import Registry
from graphene_peewee_async.types import PeeweeObjectType
from graphene_peewee_async.mutations import (
    CreateOneMutation,
    CreateManyMutation,
    UpdateOneMutation,
    UpdateManyMutation,
    DeleteOneMutation,
    DeleteManyMutation,
    CloneOneMutation,
)


def get_many_field_name(one_field_name):
    return '{}s'.format(one_field_name)


def get_node(manager, model, registry):
    meta_class = type('Meta', (), {'registry': registry,
                                   'model': model,
                                   'manager': manager,
                                   'interfaces': ()})
    node_class = type(model.__name__,
                      (PeeweeObjectType,),
                      {meta_class.__name__: meta_class})
    return node_class


def get_connection(node_class):
    connection_meta_class = type('Meta', (), {'node': node_class})
    connection_class = type('{}Connection'.format(node_class.__name__),
                            (PeeweeConnection,),
                            {connection_meta_class.__name__: connection_meta_class})
    return connection_class


def generate_schema(manager, models):
    query_classes = {}
    mutation_classes = {}
    registry = Registry()
    for model in models:
        node_class = get_node(manager, model, registry)
        connection_class = get_connection(node_class)
        node_name = node_class.__name__
        entity_name = inflection.underscore(node_name)
        entities_name = get_many_field_name(entity_name)
        query_classes.update({
            entity_name: PeeweeNodeField(node_class),
            entities_name: PeeweeConnectionField(connection_class),
        })
        for mutation_class in (
            CreateOneMutation,
            CreateManyMutation,
            UpdateOneMutation,
            UpdateManyMutation,
            DeleteOneMutation,
            DeleteManyMutation,
            CloneOneMutation,
        ):
            mutation_name = re.sub(
                r'(.*)(One|Many)Mutation',
                lambda m: m.group(1) + (node_name if m.group(2) == 'One' else get_many_field_name(node_name)),
                mutation_class.__name__
            )
            mutation_classes[inflection.underscore(mutation_name)] = mutation_class.generate(node_class, connection_class).Field()
    query_class = type('Query', (ObjectType,), query_classes)
    mutation_class = type('Mutation', (ObjectType,), mutation_classes)
    executor = AsyncioExecutor()
    schema = Schema(query=query_class,
                    mutation=mutation_class,
                    auto_camelcase=False)
    return schema, executor
