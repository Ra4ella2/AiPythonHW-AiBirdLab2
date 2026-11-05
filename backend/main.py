import os

import httpx

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from fastapi.middleware.cors import (
    CORSMiddleware
)

from sqlalchemy.orm import Session

from backend.database import (
    Base,
    engine,
    get_db
)

from backend import crud

from backend.rabbit import (
    rabbit_request
)


AI_SERVER_URL = os.getenv(
    "AI_SERVER_URL",
    "http://ai_server:8001/predict"
)


app = FastAPI(title="AI Bird Lab Central Server")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


Base.metadata.create_all(
    bind=engine
)


@app.get("/")
def home():

    return {
        "message":
        "AI Bird Lab Backend працює"
    }


@app.get("/health")
def health():

    return {
        "status": "ok"
    }


#ANALYZE

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
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


    file_bytes = await file.read()


    try:

        async with httpx.AsyncClient() as client:

            response = await client.post(

                AI_SERVER_URL,

                files={
                    "file": (
                        filename,
                        file_bytes,
                        file.content_type
                    )
                },

                timeout=120
            )

    except Exception as error:

        raise HTTPException(
            status_code=503,
            detail=(
                f"AI Server недоступний: "
                f"{error}"
            )
        )


    if response.status_code != 200:

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )


    data = response.json()

    results = data["results"]

    best = results[0]


    bird = crud.create_bird(
        db=db,
        image_name=filename,
        species=best["species"],
        confidence=best["confidence"]
    )


    return {

        "id": bird.id,

        "image_name": filename,

        "best_result": best,

        "top_3": results
    }


#GET

@app.get("/birds/{bird_id}")
def get_bird(
    bird_id: int,
    db: Session = Depends(get_db)
):

    bird = crud.get_bird(
        db,
        bird_id
    )

    if not bird:

        raise HTTPException(
            status_code=404,
            detail="Запис не знайдено"
        )

    return crud.bird_to_dict(
        bird
    )


#DELETE

@app.delete("/birds/{bird_id}")
def delete_bird(
    bird_id: int,
    db: Session = Depends(get_db)
):

    deleted = crud.delete_bird(
        db,
        bird_id
    )

    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Запис не знайдено"
        )

    return {
        "message": "Запис видалено"
    }


#RABBIT WORKER

async def call_worker(data):

    try:

        return await rabbit_request(
            data
        )

    except Exception as error:

        raise HTTPException(
            status_code=503,
            detail=(
                f"RabbitMQ worker "
                f"недоступний: {error}"
            )
        )


#HISTORY

@app.get("/history")
async def history():

    return await call_worker({
        "action": "history"
    })


#SEARCH

@app.get("/search")
async def search(name: str):

    return await call_worker({

        "action": "search",

        "name": name
    })


#STATISTICS

@app.get("/statistics")
async def statistics():

    return await call_worker({
        "action": "statistics"
    })


#CSV

@app.post("/export")
async def export_csv():

    return await call_worker({
        "action": "export"
    })