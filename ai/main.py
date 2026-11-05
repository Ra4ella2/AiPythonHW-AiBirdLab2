import io
import os

import torch

from PIL import Image

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)

from transformers import (
    AutoImageProcessor,
    AutoModelForImageClassification
)


MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "dennisjooo/Birds-Classifier-EfficientNetB2"
)


app = FastAPI(title="Bird AI Server")


print("Завантаження AI-моделі...")


try:

    processor = (
        AutoImageProcessor
        .from_pretrained(
            MODEL_NAME
        )
    )

    model = (
        AutoModelForImageClassification
        .from_pretrained(
            MODEL_NAME
        )
    )

    model.eval()

    print("AI-модель завантажено.")

except Exception as error:

    print("Помилка завантаження моделі:")

    print(error)

    raise


@app.get("/")
def home():

    return {
        "message":
        "Bird AI Server працює",

        "model":
        MODEL_NAME
    }


@app.get("/health")
def health():

    return {
        "status": "ok"
    }


@app.post("/predict")
async def predict(
    file: UploadFile = File(...)
):

    filename = (
        file.filename
        or "bird.jpg"
    )

    extension = filename.lower()


    if not extension.endswith(
        (
            ".jpg",
            ".jpeg",
            ".png"
        )
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Підтримуються тільки "
                "JPG, JPEG та PNG"
            )
        )


    try:

        image_bytes = await file.read()

        image = Image.open(
            io.BytesIO(
                image_bytes
            )
        ).convert("RGB")

    except Exception:

        raise HTTPException(
            status_code=400,
            detail=(
                "Не вдалося "
                "відкрити зображення"
            )
        )


    try:

        inputs = processor(
            images=image,
            return_tensors="pt"
        )


        with torch.no_grad():

            outputs = model(
                **inputs
            )


        probabilities = torch.softmax(
            outputs.logits,
            dim=-1
        )[0]


        count = min(
            3,
            probabilities.shape[0]
        )


        top_values, top_indexes = (
            torch.topk(
                probabilities,
                count
            )
        )


        results = []


        for score, index in zip(
            top_values,
            top_indexes
        ):

            species = (
                model.config.id2label[
                    index.item()
                ]
            )


            results.append({

                "species":
                species,

                "confidence":
                round(
                    score.item(),
                    4
                )
            })


        return {

            "image_name":
            filename,

            "results":
            results
        }


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )