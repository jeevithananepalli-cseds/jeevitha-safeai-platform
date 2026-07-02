"""SQLAlchemy implementation of the ``EmergencyContactRepository`` port."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities.emergency_contact import EmergencyContact
from app.infrastructure.db.models.emergency_contact import EmergencyContactModel


class SqlAlchemyEmergencyContactRepository:
    """Persist and load emergency contacts. Implements the domain port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, contact: EmergencyContact) -> EmergencyContact:
        model = EmergencyContactModel(
            user_id=contact.user_id,
            contact_name=contact.contact_name,
            phone_number=contact.phone_number,
            relationship=contact.relationship,
        )
        self._session.add(model)
        self._session.flush()
        return self._to_entity(model)

    def list_for_user(self, user_id: int, *, limit: int, offset: int) -> list[EmergencyContact]:
        rows = self._session.scalars(
            select(EmergencyContactModel)
            .where(EmergencyContactModel.user_id == user_id)
            .order_by(EmergencyContactModel.id)
            .limit(limit)
            .offset(offset)
        ).all()
        return [self._to_entity(row) for row in rows]

    def all_for_user(self, user_id: int) -> list[EmergencyContact]:
        rows = self._session.scalars(
            select(EmergencyContactModel)
            .where(EmergencyContactModel.user_id == user_id)
            .order_by(EmergencyContactModel.id)
        ).all()
        return [self._to_entity(row) for row in rows]

    def count_for_user(self, user_id: int) -> int:
        total = self._session.scalar(
            select(func.count())
            .select_from(EmergencyContactModel)
            .where(EmergencyContactModel.user_id == user_id)
        )
        return total or 0

    def get_by_user_and_phone(self, user_id: int, phone_number: str) -> EmergencyContact | None:
        model = self._session.scalars(
            select(EmergencyContactModel)
            .where(EmergencyContactModel.user_id == user_id)
            .where(EmergencyContactModel.phone_number == phone_number)
        ).one_or_none()
        return self._to_entity(model) if model is not None else None

    @staticmethod
    def _to_entity(model: EmergencyContactModel) -> EmergencyContact:
        return EmergencyContact(
            id=model.id,
            user_id=model.user_id,
            contact_name=model.contact_name,
            phone_number=model.phone_number,
            relationship=model.relationship,
        )
