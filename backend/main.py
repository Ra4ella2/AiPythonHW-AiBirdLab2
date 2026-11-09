import os
import httpx

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Depends,
    Form
)

from fastapi.middleware.cors import (
    CORSMiddleware
)

from pydantic import BaseModel

from sqlalchemy.orm import Session

from web3 import Web3

from backend.database import (
    Base,
    engine,
    get_db
)

from backend import crud

from backend.rabbit import (
    rabbit_request
)

from backend.blockchain import (
    verify_payment
)


AI_SERVER_URL = os.getenv(
    "AI_SERVER_URL",
    "http://ai_server:8001/predict"
)

ETH_RPC_URL = os.getenv(
    "ETH_RPC_URL",
    "http://host.docker.internal:8545"
)

CONTRACT_ADDRESS = os.getenv(
    "CONTRACT_ADDRESS",
    ""
)

PACKAGE_PRICE_WEI = Web3.to_wei(
    0.002,
    "ether"
)


web3 = Web3(
    Web3.HTTPProvider(
        ETH_RPC_URL
    )
)


app = FastAPI(
    title="AI Bird Lab Central Server"
)


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


class PaymentRequest(BaseModel):
    wallet_address: str
    transaction_hash: str


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

#CREDITS

@app.get(
    "/credits/{wallet_address}"
)
def get_credits(
    wallet_address: str,
    db: Session = Depends(
        get_db
    )
):
    wallet = crud.get_or_create_wallet(
        db,
        wallet_address
    )

    return {
        "wallet_address":
            wallet.wallet_address,

        "credits":
            wallet.credits
    }

#PAYMENT

@app.post("/payment/verify")
def payment_verify(
    request: PaymentRequest,
    db: Session = Depends(
        get_db
    )
):
    transaction_hash = (
        request.transaction_hash
    )

    wallet_address = (
        request.wallet_address
    )


    if crud.transaction_used(
        db,
        transaction_hash
    ):
        raise HTTPException(
            status_code=400,
            detail="Transaction already used"
        )


    result = verify_payment(
        transaction_hash,
        wallet_address
    )


    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["error"]
        )


    wallet = crud.add_credits(
        db,
        wallet_address,
        5
    )


    crud.save_transaction(
        db,
        transaction_hash,
        wallet_address
    )


    return {
        "message":
            "Payment confirmed",

        "credits":
            wallet.credits
    }


@app.post("/payment/check/{wallet_address}")
def check_payment(
    wallet_address: str,
    db: Session = Depends(
        get_db
    )
):
    if not CONTRACT_ADDRESS:
        raise HTTPException(
            status_code=500,
            detail=(
                "CONTRACT_ADDRESS "
                "is not configured"
            )
        )


    if not web3.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Ethereum RPC is unavailable"
        )


    wallet_lower = (
        wallet_address.lower()
    )

    contract_lower = (
        CONTRACT_ADDRESS.lower()
    )


    latest_block = (
        web3.eth.block_number
    )

    start_block = max(
        0,
        latest_block - 100
    )


    for block_number in range(
        latest_block,
        start_block - 1,
        -1
    ):
        block = web3.eth.get_block(
            block_number,
            full_transactions=True
        )


        for transaction in reversed(
            block.transactions
        ):
            if not transaction["to"]:
                continue


            sender = (
                transaction["from"].lower()
            )

            receiver = (
                transaction["to"].lower()
            )


            if sender != wallet_lower:
                continue


            if receiver != contract_lower:
                continue


            if (
                transaction["value"]
                != PACKAGE_PRICE_WEI
            ):
                continue


            transaction_hash = (
                transaction["hash"].hex()
            )


            if crud.transaction_used(
                db,
                transaction_hash
            ):
                continue


            receipt = (
                web3.eth.get_transaction_receipt(
                    transaction["hash"]
                )
            )


            if receipt.status != 1:
                continue


            wallet = crud.add_credits(
                db,
                wallet_address,
                5
            )


            crud.save_transaction(
                db,
                transaction_hash,
                wallet_address
            )


            return {
                "message":
                    "Payment confirmed",

                "transaction_hash":
                    transaction_hash,

                "credits":
                    wallet.credits
            }


    raise HTTPException(
        status_code=404,
        detail="New payment not found"
    )

#ANALYZE

@app.post("/analyze")
async def analyze(
    wallet_address: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(
        get_db
    )
):
    wallet = crud.get_or_create_wallet(
        db,
        wallet_address
    )


    if wallet.credits <= 0:
        raise HTTPException(
            status_code=402,
            detail="Payment required"
        )


    filename = (
        file.filename
        or "bird.jpg"
    )


    extension = (
        filename.lower()
    )


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
                "Підтримуються "
                "тільки JPG, JPEG та PNG"
            )
        )


    file_bytes = await file.read()


    try:
        async with (
            httpx.AsyncClient()
        ) as client:

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

    results = data[
        "results"
    ]

    best = results[0]


    bird = crud.create_bird(
        db=db,
        image_name=filename,
        species=best["species"],
        confidence=best["confidence"]
    )


    crud.remove_credit(
        db,
        wallet_address
    )


    wallet = crud.get_wallet(
        db,
        wallet_address
    )


    return {
        "id":
            bird.id,

        "image_name":
            filename,

        "best_result":
            best,

        "top_3":
            results,

        "credits_left":
            wallet.credits
    }


#BIRDS

@app.get("/birds/{bird_id}")
def get_bird(
    bird_id: int,
    db: Session = Depends(
        get_db
    )
):
    bird = crud.get_bird(
        db,
        bird_id
    )


    if not bird:
        raise HTTPException(
            404,
            "Запис не знайдено"
        )


    return crud.bird_to_dict(
        bird
    )


@app.delete("/birds/{bird_id}")
def delete_bird(
    bird_id: int,
    db: Session = Depends(
        get_db
    )
):
    deleted = crud.delete_bird(
        db,
        bird_id
    )


    if not deleted:
        raise HTTPException(
            404,
            "Запис не знайдено"
        )


    return {
        "message":
            "Запис видалено"
    }

#RABBITMQ

async def call_worker(
    data
):
    try:
        return await rabbit_request(
            data
        )

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "RabbitMQ worker "
                f"недоступний: {error}"
            )
        )


@app.get("/history")
async def history():
    return await call_worker(
        {
            "action":
                "history"
        }
    )


@app.get("/search")
async def search(
    name: str
):
    return await call_worker(
        {
            "action":
                "search",

            "name":
                name
        }
    )


@app.get("/statistics")
async def statistics():
    return await call_worker(
        {
            "action":
                "statistics"
        }
    )


@app.post("/export")
async def export_csv():
    return await call_worker(
        {
            "action":
                "export"
        }
    )
