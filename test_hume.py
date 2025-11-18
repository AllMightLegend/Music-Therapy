import asyncio
from hume import AsyncHumeClient
from hume.expression_measurement.stream import Config

async def test():
    client = AsyncHumeClient(api_key='test')
    print('Testing connect method...')
    try:
        # Try without any parameters
        async with client.expression_measurement.stream.connect() as socket:
            print('Connected successfully with no params')
    except Exception as e:
        print(f'Error with no params: {e}')
    
    try:
        # Try with Config as first positional argument
        model_config = Config(face={})
        async with client.expression_measurement.stream.connect(model_config) as socket:
            print('Connected successfully with Config as positional arg')
    except Exception as e:
        print(f'Error with positional Config: {e}')

asyncio.run(test())
