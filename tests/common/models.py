from peewee import (
    CharField,
    IntegerField,
    ForeignKeyField,
    Model,
)
from peewee_async import PooledPostgresqlDatabase


db = PooledPostgresqlDatabase('graphene_test', user='postgres', host='localhost')


class BaseModel(Model):

    class Meta:
        database = db


class Author(BaseModel):

    name = CharField()
    rating = IntegerField()


class Book(BaseModel):

    name = CharField()
    year = IntegerField()
    author = ForeignKeyField(Author)


db.create_tables([
    Author,
    Book,
], safe=True)
db.set_allow_sync(False)
