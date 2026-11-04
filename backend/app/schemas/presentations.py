from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.services.language import response_language


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class SearchRequest(Strict):
    query: str = Field(min_length=2, max_length=500)


class WebSource(Strict):
    title: str = Field(max_length=300)
    url: str = Field(max_length=2000)
    snippet: str = Field(max_length=1500)
    published_at: str | None = None
    retrieved_at: datetime


class WebSearchResult(Strict):
    sources: list[WebSource]
    cached: bool = False


class DeckRequest(Strict):
    request_key: UUID
    instruction: str = Field(min_length=5, max_length=2000)
    language: Literal["en", "zh"] = "zh"
    slide_count: int = Field(ge=1, le=12)
    document_ids: list[UUID] = Field(default_factory=list, max_length=5)
    meeting_ids: list[UUID] = Field(default_factory=list, max_length=5)
    use_memories: bool = True
    web_query: str | None = Field(default=None, min_length=2, max_length=500)

    @model_validator(mode="after")
    def requested_language(self) -> "DeckRequest":
        self.language = response_language(self.instruction, self.language)  # type: ignore[assignment]
        return self

    @field_validator("instruction")
    @classmethod
    def instruction_text(cls, value: str) -> str:
        if len(value.strip()) < 5:
            raise ValueError("Instruction needs at least five nonblank characters")
        return value.strip()


class Statement(Strict):
    kind: Literal["fact", "inference", "suggestion"]
    source_ref: str
    quote: str = Field(min_length=1, max_length=65)
    text: str = Field(default="", max_length=65)


class Slide(Strict):
    type: Literal[
        "cover",
        "section",
        "bullets",
        "two_column",
        "timeline",
        "risk_matrix",
        "summary",
    ]
    title: str = Field(min_length=1, max_length=90)
    bullets: list[str] = Field(min_length=1, max_length=6)
    speaker_notes: str = Field(default="", max_length=1200)
    visual_spec: Literal["none"] = "none"
    source_refs: list[str] = Field(default_factory=list, max_length=5)
    statements: list[Statement] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def bounded(self) -> "Slide":
        if not self.title.strip():
            raise ValueError("Slide title cannot be blank")
        if any(not b.strip() or len(b) > 160 for b in self.bullets):
            raise ValueError("Bullet must be 1-160 characters")
        return self


class Outline(Strict):
    presentation_title: str = Field(min_length=1, max_length=100)
    theme: Literal["memora"] = "memora"
    language: Literal["en", "zh"]
    slide_count: int = Field(ge=1, le=12)
    slides: list[Slide] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def count(self) -> "Outline":
        if len(self.slides) != self.slide_count:
            raise ValueError("Slide count must exactly match")
        return self


class PlannedSlide(Strict):
    type: Literal[
        "cover",
        "section",
        "bullets",
        "two_column",
        "timeline",
        "risk_matrix",
        "summary",
    ]
    title: str = Field(min_length=1, max_length=90)
    statements: list[Statement] = Field(min_length=1, max_length=3)


class PlannedOutline(Strict):
    presentation_title: str = Field(min_length=1, max_length=100)
    slides: list[PlannedSlide] = Field(min_length=1, max_length=12)


class DeckOut(Strict):
    id: UUID
    status: str
    stage: str
    progress: int
    error_code: str | None
    page_count: int | None
    attempts: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def job_id(self) -> UUID:
        return self.id

    outline_json: dict[str, object]
    sources_json: list[dict[str, object]]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def error_message(self) -> str | None:
        if not self.error_code:
            return None
        return {
            "PRESENTATION_NODE_MISSING": (
                "Install Node.js and renderer dependencies; check PRESENTATION_NODE."
            ),
            "PRESENTATION_LIBREOFFICE_MISSING": (
                "Install LibreOffice/CJK fonts; check PRESENTATION_LIBREOFFICE."
            ),
            "PREVIEW_CONVERSION_FAILED": (
                "LibreOffice could not convert the presentation. Check the "
                "runtime installation."
            ),
            "PRESENTATION_RENDER_FAILED": (
                "Renderer rejected the layout or text overflow. Reduce text"
                " and regenerate."
            ),
            "PRESENTATION_PROCESS_TIMEOUT": (
                "Rendering/conversion timed out. Check runtime resources be"
                "fore retrying."
            ),
            "PRESENTATION_CONTEXT_TOO_LARGE": (
                "Select fewer sources or raise the configured context budget."
            ),
            "OUTLINE_INVALID_CITATIONS": (
                "Model output contained missing or unknown citations; no fi"
                "le published."
            ),
            "OUTLINE_INVALID": (
                "Model output failed schema/count/language validation; no f"
                "ile published."
            ),
            "SEARCH_NOT_CONFIGURED": (
                "Set SEARCH_API_KEY in root .env or disable optional web research."
            ),
            "SEARCH_RATE_LIMITED": (
                "Search quota/rate limit reached. Retry explicitly later; n"
                "o auto retry."
            ),
        }.get(
            self.error_code,
            (
                "Generation failed. Check backend configuration and sources"
                " before explicitly retrying."
            ),
        )
