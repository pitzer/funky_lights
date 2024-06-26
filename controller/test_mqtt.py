import asyncio
import aiomqtt


async def main(mqtt_server, topic):
    reconnect_interval = 5  # In seconds
    while True:
        try:
            async with aiomqtt.Client(mqtt_server, max_queued_incoming_messages=1) as client:
                await client.subscribe(topic)
                async for message in client.messages:
                    print(message.payload.decode())
        except aiomqtt.MqttError as error:
            print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
            await asyncio.sleep(reconnect_interval)


if __name__ == "__main__":
    asyncio.run(main("localhost", "orientation/x"))