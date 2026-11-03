from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def audit(
    db: Session,
    owner: UUID,
    action: str,
    resource_type: str,
    identifier: UUID,
    **metadata: object,
) -> None:
    db.add(
        AuditEvent(
            user_id=owner,
            action=action,
            resource_type=resource_type,
            resource_id=identifier,
            metadata_json=metadata,
        )
    )
