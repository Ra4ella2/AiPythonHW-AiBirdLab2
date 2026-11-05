from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    Float,
    DateTime
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from backend.database import Base


class Bird(Base):

    __tablename__ = "birds"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    image_name: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    predicted_species: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    analysis_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )