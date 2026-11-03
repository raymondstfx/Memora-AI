import re
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.schemas.meetings import (
    Claim,
    MeetingExtraction,
    MemoryClaim,
    Person,
    RiskExtract,
    TaskExtract,
    TranscriptLine,
)
from app.services.llm.provider import ChatError


def parse_txt(data: bytes, maximum: int) -> tuple[str, list[TranscriptLine]]:
    if not data or len(data) > maximum:
        raise ChatError(
            "TXT_SIZE_LIMIT", "TXT is empty or exceeds the upload limit.", 413
        )
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ChatError(
            "TXT_ENCODING", "Save the transcript as UTF-8 (optional BOM).", 422
        ) from exc
    if not text.strip() or any(ord(c) < 32 and c not in "\n\r\t" for c in text):
        raise ChatError(
            "TXT_INVALID",
            "TXT must contain readable text without binary controls.",
            422,
        )
    lines = []
    for i, line in enumerate(text.splitlines(), 1):
        speaker = re.match(r"^([^:\n：]{1,100})[:：]\s*(.+)$", line)
        lines.append(
            TranscriptLine(
                number=i, text=line, speaker=speaker[1].strip() if speaker else None
            )
        )
    return text, lines


def metadata(
    text: str, date_hint: str | None, zone_hint: str | None
) -> tuple[datetime | None, str | None, str | None, str | None]:
    def header(name: str) -> str | None:
        found = re.search(rf"^{name}:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        return found[1].strip() if found else None

    date_text, zone = date_hint or header("Date"), zone_hint or header("Timezone")
    occurred = None
    try:
        tz = ZoneInfo(zone) if zone else None
        if date_text:
            occurred = datetime.fromisoformat(date_text)
            if occurred.tzinfo is None:
                if tz is None:
                    raise ValueError("Timezone required")
                occurred = occurred.replace(tzinfo=tz)
            occurred = occurred.astimezone(UTC)
        if re.search(
            r"\b(tomorrow|today|yesterday|next|this week)\b|明天|今天|昨天|下周|本周",
            text,
            re.IGNORECASE,
        ) and (not occurred or not zone):
            raise ValueError("Relative deadlines need date/timezone")
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ChatError(
            "MEETING_DATE_REQUIRED",
            (
                "Provide an ISO meeting date and IANA timezone (e.g. "
                "2026-11-04 / Asia/Shanghai) to resolve relative dead"
                "lines."
            ),
            422,
        ) from exc
    return occurred, zone, header("Title"), header("Location")


def normalize_due(
    value: str | None, occurred: datetime | None, zone: str | None
) -> datetime | None:
    if not value or not zone:
        return None
    result: date | None = None
    absolute = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", value)
    try:
        if absolute:
            result = date.fromisoformat(absolute[1])
        elif occurred:
            base = occurred.astimezone(ZoneInfo(zone)).date()
            if value.lower() in ("tomorrow", "明天"):
                result = base + timedelta(days=1)
            elif value.lower() in ("today", "今天"):
                result = base
            else:
                for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d", "%b %d"):
                    try:
                        parsed = datetime.strptime(
                            value if "%Y" in fmt else f"{value}, {base.year}",
                            fmt if "%Y" in fmt else fmt + ", %Y",
                        )
                        result = parsed.date().replace(
                            year=parsed.year if "%Y" in fmt else base.year
                        )
                        break
                    except ValueError:
                        continue
        return (
            datetime.combine(result, time.min, ZoneInfo(zone)).astimezone(UTC)
            if result
            else None
        )
    except ValueError:
        return None


def validate_evidence(analysis: MeetingExtraction, lines: list[TranscriptLine]) -> None:
    evidence_items: list[Person | Claim | RiskExtract | TaskExtract | MemoryClaim] = [
        *analysis.people,
        *analysis.decisions,
        *analysis.risks,
        *analysis.tasks,
        *analysis.candidate_facts,
        *analysis.memory_claims,
    ]
    for item in evidence_items:
        evidence = item.evidence
        if evidence.line_end < evidence.line_start or evidence.line_end > len(lines):
            raise ValueError("Invalid evidence offsets")
        span = "\n".join(
            line.text for line in lines[evidence.line_start - 1 : evidence.line_end]
        )
        if evidence.quote not in span:
            raise ValueError("Evidence quote does not match source lines")
    for person in analysis.people:
        if person.name not in person.evidence.quote:
            raise ValueError("Participant has no source support")
        if person.role and person.role not in person.evidence.quote:
            raise ValueError("Role has no source support")
    for task in analysis.tasks:
        if task.owner_name and task.owner_name not in task.evidence.quote:
            raise ValueError("Owner not established by evidence")
        if task.due_text and task.due_text not in task.evidence.quote:
            raise ValueError("Deadline not established by evidence")
        if task.risk_index is not None and task.risk_index >= len(analysis.risks):
            raise ValueError("Unknown risk link")
    for claim in analysis.memory_claims:
        quote = claim.evidence.quote.casefold()
        if claim.predicate != "fact" and (
            claim.subject.casefold() not in quote or claim.value.casefold() not in quote
        ):
            raise ValueError("Memory claim subject/value missing from exact evidence")
