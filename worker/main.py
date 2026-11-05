import os
import csv
import json
import asyncio

import aio_pika

from backend.database import (
    SessionLocal,
    Base,
    engine
)

from backend import crud


RABBIT_URL = os.getenv(
    "RABBIT_URL",
    "amqp://guest:guest@rabbitmq/"
)

QUEUE_NAME = "bird_requests"

CSV_FILE = os.getenv(
    "CSV_FILE",
    "./data/bird_analysis.csv"
)


Base.metadata.create_all(
    bind=engine
)


def export_csv():
    db = SessionLocal()

    try:
        birds = crud.get_history(db)

        with open(
            CSV_FILE,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "image_name",
                "predicted_species",
                "confidence",
                "analysis_date"
            ])

            for bird in birds:
                writer.writerow([
                    bird["image_name"],
                    bird["predicted_species"],
                    bird["confidence"],
                    bird["analysis_date"]
                ])

        return {
            "message": "CSV створено",
            "file": CSV_FILE,
            "records": len(birds)
        }

    finally:
        db.close()


def execute_action(data):
    action = data.get("action")

    if action == "export":
        return export_csv()

    db = SessionLocal()

    try:
        if action == "history":
            return crud.get_history(db)

        if action == "search":
            return crud.search_birds(
                db,
                data.get("name", "")
            )

        if action == "statistics":
            return crud.get_statistics(db)

        return {
            "error": "Unknown action"
        }

    finally:
        db.close()


async def connect_rabbit():
    while True:
        try:
            print("Connecting to RabbitMQ...")

            connection = await aio_pika.connect_robust(
                RABBIT_URL
            )

            print("RabbitMQ connected")

            return connection

        except Exception as error:
            print(
                "RabbitMQ is not ready:",
                error
            )

            print(
                "Retry in 3 seconds..."
            )

            await asyncio.sleep(3)


async def main():
    connection = await connect_rabbit()

    channel = await connection.channel()

    await channel.set_qos(
        prefetch_count=1
    )

    queue = await channel.declare_queue(
        QUEUE_NAME,
        durable=True
    )

    print("RabbitMQ worker started")
    print(f"Waiting for messages in queue: {QUEUE_NAME}")

    async with queue.iterator() as queue_iter:

        async for message in queue_iter:

            async with message.process():

                print(
                    "Message received:",
                    message.body.decode()
                )

                try:
                    data = json.loads(
                        message.body.decode()
                    )

                    result = execute_action(
                        data
                    )

                except Exception as error:
                    result = {
                        "error": str(error)
                    }

                response = aio_pika.Message(
                    body=json.dumps(
                        result,
                        ensure_ascii=False,
                        default=str
                    ).encode("utf-8"),

                    correlation_id=(
                        message.correlation_id
                    )
                )

                if message.reply_to:

                    await channel.default_exchange.publish(
                        response,
                        routing_key=message.reply_to
                    )

                    print(
                        "Response sent"
                    )


if __name__ == "__main__":
    asyncio.run(main())