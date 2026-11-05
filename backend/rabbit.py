import os
import json
import uuid
import asyncio

import aio_pika


RABBIT_URL = os.getenv(
    "RABBIT_URL",
    "amqp://guest:guest@rabbitmq/"
)

QUEUE_NAME = "bird_requests"


async def rabbit_request(data: dict):

    connection = await aio_pika.connect_robust(
        RABBIT_URL
    )

    channel = await connection.channel()

    callback_queue = await channel.declare_queue(
        exclusive=True,
        auto_delete=True
    )

    correlation_id = str(
        uuid.uuid4()
    )

    loop = asyncio.get_running_loop()

    future = loop.create_future()


    async def on_response(message):

        if (
            message.correlation_id
            == correlation_id
        ):

            result = json.loads(
                message.body.decode()
            )

            if not future.done():
                future.set_result(result)


    await callback_queue.consume(
        on_response,
        no_ack=True
    )


    message = aio_pika.Message(

        body=json.dumps(
            data
        ).encode(),

        correlation_id=correlation_id,

        reply_to=callback_queue.name
    )


    await channel.default_exchange.publish(
        message,
        routing_key=QUEUE_NAME
    )


    try:

        result = await asyncio.wait_for(
            future,
            timeout=10
        )

        if (
            isinstance(result, dict)
            and "error" in result
        ):
            raise RuntimeError(
                result["error"]
            )

        return result

    finally:

        await connection.close()