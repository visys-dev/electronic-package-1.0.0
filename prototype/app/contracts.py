from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text150 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]
Text2000 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
Version = Annotated[int, Field(strict=True, ge=1)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null(cls, value):
        if isinstance(value, dict) and any(item is None for item in value.values()):
            raise ValueError("Explicit null is not allowed by the input contract")
        return value


class Login(Input):
    login: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
    password: Annotated[str, StringConstraints(min_length=1, max_length=64)]


class CreateTicket(Input):
    title: Text150
    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
    ]
    categoryId: UUID
    previousTicketId: UUID | None = None


class Assignment(Input):
    expectedVersion: Version
    assigneeId: UUID
    reason: Text2000 | None = None


class StateChange(Input):
    expectedVersion: Version
    toState: Literal["in_progress", "waiting_requester", "resolved", "closed"]
    text: Text2000 | None = None
    solutionCommentId: UUID | None = None


class CommentInput(Input):
    expectedVersion: Version
    body: Text2000
    visibility: Literal["public", "internal"]
