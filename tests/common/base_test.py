import asyncio
from unittest import TestCase


class BaseTest(TestCase):

    loop = asyncio.get_event_loop()
