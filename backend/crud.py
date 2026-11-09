from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.models import (
    Bird,
    WalletCredit,
    UsedTransaction
)


def bird_to_dict(bird: Bird):
    return {
        "id": bird.id,
        "image_name": bird.image_name,
        "predicted_species": bird.predicted_species,
        "confidence": bird.confidence,
        "analysis_date": bird.analysis_date.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }


def create_bird(
    db: Session,
    image_name: str,
    species: str,
    confidence: float
):
    bird = Bird(
        image_name=image_name,
        predicted_species=species,
        confidence=confidence
    )

    db.add(bird)
    db.commit()
    db.refresh(bird)

    return bird


def get_bird(
    db: Session,
    bird_id: int
):
    return db.scalar(
        select(Bird).where(
            Bird.id == bird_id
        )
    )


def delete_bird(
    db: Session,
    bird_id: int
):
    bird = get_bird(
        db,
        bird_id
    )

    if not bird:
        return False

    db.delete(bird)
    db.commit()

    return True


def get_history(
    db: Session
):
    birds = db.scalars(
        select(Bird)
        .order_by(Bird.id.desc())
    ).all()

    return [
        bird_to_dict(bird)
        for bird in birds
    ]


def search_birds(
    db: Session,
    name: str
):
    birds = db.scalars(
        select(Bird)
        .where(
            Bird.predicted_species.ilike(
                f"%{name}%"
            )
        )
        .order_by(Bird.id.desc())
    ).all()

    return [
        bird_to_dict(bird)
        for bird in birds
    ]


def get_statistics(
    db: Session
):
    total = db.scalar(
        select(
            func.count(Bird.id)
        )
    ) or 0


    most_common = db.execute(
        select(
            Bird.predicted_species,
            func.count(Bird.id).label(
                "count"
            )
        )
        .group_by(
            Bird.predicted_species
        )
        .order_by(
            func.count(Bird.id).desc()
        )
        .limit(1)
    ).first()


    highest = db.scalar(
        select(Bird)
        .order_by(
            Bird.confidence.desc()
        )
        .limit(1)
    )


    lowest = db.scalar(
        select(Bird)
        .order_by(
            Bird.confidence.asc()
        )
        .limit(1)
    )


    return {
        "total_images": total,

        "most_common_species": (
            {
                "species": most_common[0],
                "count": most_common[1]
            }
            if most_common
            else None
        ),

        "highest_confidence": (
            {
                "species":
                    highest.predicted_species,

                "confidence":
                    highest.confidence
            }
            if highest
            else None
        ),

        "lowest_confidence": (
            {
                "species":
                    lowest.predicted_species,

                "confidence":
                    lowest.confidence
            }
            if lowest
            else None
        )
    }


def get_wallet(
    db: Session,
    wallet_address: str
):
    wallet_address = wallet_address.lower()

    return db.scalar(
        select(WalletCredit)
        .where(
            WalletCredit.wallet_address
            == wallet_address
        )
    )


def get_or_create_wallet(
    db: Session,
    wallet_address: str
):
    wallet_address = wallet_address.lower()

    wallet = get_wallet(
        db,
        wallet_address
    )

    if wallet:
        return wallet


    wallet = WalletCredit(
        wallet_address=wallet_address,
        credits=0
    )

    db.add(wallet)
    db.commit()
    db.refresh(wallet)

    return wallet


def add_credits(
    db: Session,
    wallet_address: str,
    amount: int
):
    wallet = get_or_create_wallet(
        db,
        wallet_address
    )

    wallet.credits += amount

    db.commit()
    db.refresh(wallet)

    return wallet


def remove_credit(
    db: Session,
    wallet_address: str
):
    wallet = get_or_create_wallet(
        db,
        wallet_address
    )

    if wallet.credits <= 0:
        return False


    wallet.credits -= 1

    db.commit()
    db.refresh(wallet)

    return True


def transaction_used(
    db: Session,
    transaction_hash: str
):
    transaction = db.scalar(
        select(UsedTransaction)
        .where(
            UsedTransaction.transaction_hash
            == transaction_hash
        )
    )

    return transaction is not None


def save_transaction(
    db: Session,
    transaction_hash: str,
    wallet_address: str
):
    transaction = UsedTransaction(
        transaction_hash=transaction_hash,
        wallet_address=wallet_address.lower()
    )

    db.add(transaction)
    db.commit()

    return transaction