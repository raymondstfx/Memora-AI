from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from redis import Redis
from rq import Queue
from rq.serializers import JSONSerializer
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import EmailApproval, EmailOutbox
from app.db.session import session_factory
from app.schemas.meetings import Approval, EmailOut, EmailPatch
from app.services.audit import audit
from app.services.llm.provider import ChatError
from app.services.mail_transport import MailFailure, SMTPTransport, mail_config


class EmailService:
    def __init__(self, engine: Engine, settings: Settings):
        self.settings, self.sessions = settings, session_factory(engine)
        self.redis = Redis.from_url(
            settings.redis_url.get_secret_value(),
            socket_timeout=3,
            socket_connect_timeout=3,
        )
        self.transport = SMTPTransport(settings)

    def owned(
        self, db: Session, owner: UUID, identifier: UUID, lock: bool = False
    ) -> EmailOutbox:
        q = select(EmailOutbox).where(
            EmailOutbox.id == identifier, EmailOutbox.user_id == owner
        )
        row = db.scalar(q.with_for_update() if lock else q)
        if row is None:
            raise ChatError("NOT_FOUND", "Email not found.", 404)
        return row

    def get(self, owner: UUID, identifier: UUID) -> EmailOut:
        with self.sessions.begin() as db:
            row = self.owned(db, owner, identifier, True)
            if row.send_status in (
                "sending",
                "queued",
            ) and row.updated_at < datetime.now(UTC) - timedelta(
                seconds=self.settings.ingest_job_timeout_seconds + 60
            ):
                row.error_code = (
                    "SMTP_DELIVERY_UNCERTAIN"
                    if row.send_status == "sending"
                    else "EMAIL_JOB_INTERRUPTED"
                )
                row.send_status = "failed"
                audit(
                    db,
                    owner,
                    "email_interrupted",
                    "email",
                    identifier,
                    error_code=row.error_code,
                )
            return EmailOut.model_validate(row)

    def edit(self, owner: UUID, identifier: UUID, body: EmailPatch) -> EmailOut:
        with self.sessions.begin() as db:
            row = self.owned(db, owner, identifier, True)
            if (
                row.revision != body.revision
                or row.send_status in ("queued", "sending", "sent")
                or row.error_code == "SMTP_DELIVERY_UNCERTAIN"
            ):
                raise ChatError(
                    "EMAIL_LOCKED",
                    (
                        "Reload the current revision; sent/in-flight/uncertai"
                        "n emails cannot be edited or resent."
                    ),
                    409,
                )
            if body.recipients is not None:
                row.recipients_json = body.recipients
            if body.subject is not None:
                row.subject = body.subject
            if body.body is not None:
                row.body = body.body
            row.revision += 1
            row.approval_status = "awaiting_approval"
            row.send_status = "awaiting_approval"
            row.approved_revision = row.approved_at = row.idempotency_key = (
                row.error_code
            ) = None
            audit(db, owner, "email_edited", "email", identifier, revision=row.revision)
            return EmailOut.model_validate(row)

    def enqueue(self, identifier: UUID) -> None:
        Queue("documents", connection=self.redis, serializer=JSONSerializer).enqueue(
            "app.workers.phase3.send_email",
            str(identifier),
            job_id=str(uuid4()),
            job_timeout=60,
            result_ttl=3600,
        )

    def approve(self, owner: UUID, identifier: UUID, body: Approval) -> EmailOut:
        queued = False
        with self.sessions.begin() as db:
            # Serialize idempotency-key registration across emails for this owner.
            from app.db.models import User

            db.scalar(select(User).where(User.id == owner).with_for_update())
            row = self.owned(db, owner, identifier, True)
            previous = db.scalar(
                select(EmailApproval).where(
                    EmailApproval.user_id == owner,
                    EmailApproval.idempotency_key == body.idempotency_key,
                )
            )
            if previous:
                if (
                    previous.email_id != identifier
                    or previous.revision != body.revision
                ):
                    raise ChatError(
                        "IDEMPOTENCY_CONFLICT",
                        "Approval key belongs to a different email/revision.",
                        409,
                    )
                return EmailOut.model_validate(row)
            if row.revision != body.revision:
                raise ChatError(
                    "EMAIL_REVISION_CHANGED",
                    "Draft changed; review and approve the current revision.",
                    409,
                )
            if row.send_status in ("queued", "sending", "sent"):
                return EmailOut.model_validate(row)
            if row.error_code == "SMTP_DELIVERY_UNCERTAIN":
                raise ChatError(
                    "EMAIL_RECONCILIATION_REQUIRED",
                    (
                        "SMTP outcome is uncertain. Check the mailbox; automa"
                        "tic resend is prohibited."
                    ),
                    409,
                )
            mail_config(self.settings, row.recipients_json)
            db.add(
                EmailApproval(
                    user_id=owner,
                    email_id=identifier,
                    idempotency_key=body.idempotency_key,
                    revision=body.revision,
                )
            )
            row.idempotency_key, row.approved_revision = (
                body.idempotency_key,
                row.revision,
            )
            row.approved_at, row.approval_status, row.send_status = (
                datetime.now(UTC),
                "approved",
                "queued",
            )
            row.error_code = None
            audit(
                db,
                owner,
                "email_approved",
                "email",
                identifier,
                revision=row.revision,
                approval_key=str(body.idempotency_key),
            )
            queued = True
        if queued:
            try:
                self.enqueue(identifier)
            except Exception:
                with self.sessions.begin() as db:
                    row = self.owned(db, owner, identifier, True)
                    if row.send_status == "queued":
                        row.send_status, row.error_code = "failed", "QUEUE_UNAVAILABLE"
                        audit(db, owner, "email_queue_failed", "email", identifier)
        return self.get(owner, identifier)

    def send(self, identifier: UUID) -> None:
        with self.sessions.begin() as db:
            row = db.get(EmailOutbox, identifier, with_for_update=True)
            if (
                row is None
                or row.send_status != "queued"
                or row.approval_status != "approved"
                or row.approved_revision != row.revision
            ):
                return
            owner = row.user_id
            row.send_status = "sending"
            message_id = f"<{row.id}.{row.revision}@memora.local>"
            row.provider_message_id = message_id
            recipients, subject, body = list(row.recipients_json), row.subject, row.body
            audit(
                db,
                owner,
                "email_send_claimed",
                "email",
                identifier,
                revision=row.revision,
            )
        try:
            self.transport.send(recipients, subject, body, message_id)
            error = None
        except MailFailure as exc:
            error = "SMTP_DELIVERY_UNCERTAIN" if exc.ambiguous else exc.code
        except ChatError as exc:
            error = exc.code
        except Exception:
            error = "SMTP_DELIVERY_UNCERTAIN"
        with self.sessions.begin() as db:
            row = db.get(EmailOutbox, identifier, with_for_update=True)
            if row is None:
                return
            row.send_status, row.error_code = (
                ("sent" if error is None else "failed"),
                error,
            )
            if error is None:
                row.sent_at = datetime.now(UTC)
            audit(
                db,
                owner,
                "email_sent" if error is None else "email_send_failed",
                "email",
                identifier,
                error_code=error,
                message_id=message_id,
            )
