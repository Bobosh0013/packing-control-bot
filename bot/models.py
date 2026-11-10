from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Role(StrEnum):
    ADMIN = "admin"
    EMPLOYEE = "employee"
    PARTNER_MANAGER = "partner_manager"
    PARTNER_SENIOR = "partner_senior"
    OBSERVER = "observer"


class RequestStatus(StrEnum):
    DRAFT = "DRAFT"
    NEEDS_ACTION = "NEEDS_ACTION"
    IN_QUEUE = "IN_QUEUE"
    IN_WORK = "IN_WORK"
    PACKING = "PACKING"
    PACKED = "PACKED"
    BOXES_FORMED = "BOXES_FORMED"
    AWAITING_MARKETPLACE_LABEL = "AWAITING_MARKETPLACE_LABEL"
    READY = "READY"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(32), default=Role.OBSERVER)
    fio: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    regulation_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    marketplaces: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_name: Mapped[str] = mapped_column(String(255))
    sku: Mapped[str | None] = mapped_column(String(128))
    weight_category_g: Mapped[int] = mapped_column(Integer)
    units_count: Mapped[int] = mapped_column(Integer)
    total_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    marketplace: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(40), default=RequestStatus.DRAFT)
    service_fee_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    service_fee_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    partner: Mapped[Partner] = relationship()


class BoxGroup(Base):
    __tablename__ = "box_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), index=True)
    cluster: Mapped[str] = mapped_column(String(128))
    box_type: Mapped[str] = mapped_column(String(128))
    boxes_count: Mapped[int] = mapped_column(Integer)
    units_per_box: Mapped[int] = mapped_column(Integer)
    product_kg_per_box: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    gross_kg_per_box: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    dimensions: Mapped[str | None] = mapped_column(String(128))
    marketplace_barcode: Mapped[str | None] = mapped_column(String(255))
    photo_file_ids: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

