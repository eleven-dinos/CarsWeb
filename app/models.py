from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base, engine

VEHICLE_STATUSES = ["Available", "Reserved", "Sold"]


def utc_now():
    now = datetime.now(timezone.utc)
    return now.replace(tzinfo=None)


def cents_to_price(cents):
    euros = cents // 100
    rest = cents % 100
    return str(euros) + "." + str(rest).zfill(2)


class Yard(Base):
    __tablename__ = "yards"
    __table_args__ = (
        CheckConstraint("length(name) BETWEEN 1 AND 100"),
        CheckConstraint("length(location) BETWEEN 1 AND 200"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    location = Column(String(200), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint("length(name) BETWEEN 1 AND 100"),
        CheckConstraint("length(email) BETWEEN 3 AND 254"),
        CheckConstraint("length(country) BETWEEN 1 AND 100"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(254), nullable=False)
    country = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("length(stock_number) BETWEEN 1 AND 20"),
        CheckConstraint("length(chassis_number) BETWEEN 1 AND 30"),
        CheckConstraint("length(make) BETWEEN 1 AND 100"),
        CheckConstraint("length(model) BETWEEN 1 AND 100"),
        CheckConstraint("year BETWEEN 1 AND 9999"),
        CheckConstraint("price_cents > 0"),
        CheckConstraint("status IN ('Available', 'Reserved', 'Sold')"),
    )

    id = Column(Integer, primary_key=True)
    stock_number = Column(String(20), unique=True, nullable=False)
    chassis_number = Column(String(30), unique=True, nullable=False)
    make = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False)
    price_cents = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=True)
    yard_id = Column(Integer, ForeignKey("yards.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    client = relationship("Client")
    yard = relationship("Yard")

    def price_text(self):
        return cents_to_price(self.price_cents)


def create_tables():
    Base.metadata.create_all(bind=engine)
