from sqlalchemy import (
    select,
    func
)

from sqlalchemy.orm import Session

from backend.models import Bird


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
        select(Bird)
        .where(Bird.id == bird_id)
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


def get_history(db: Session):

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


def get_statistics(db: Session):

    total = db.scalar(
        select(
            func.count(Bird.id)
        )
    ) or 0


    most_common = db.execute(
        select(
            Bird.predicted_species,
            func.count(Bird.id).label("count")
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
                "species": highest.predicted_species,
                "confidence": highest.confidence
            }
            if highest
            else None
        ),

        "lowest_confidence": (
            {
                "species": lowest.predicted_species,
                "confidence": lowest.confidence
            }
            if lowest
            else None
        )
    }