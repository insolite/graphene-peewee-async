import asyncio


if not hasattr(asyncio, 'ensure_future'):
    asyncio.ensure_future = asyncio.async
