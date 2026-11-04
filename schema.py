from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class WorkType(str, Enum):
    PLUMBING = "plomberie"
    ELECTRICITY = "electricite"
    RENOVATION = "renovation"
    PAINTING = "peinture"
    JOINERY = "menuiserie"
    OTHER = "autre"


class Urgency(str, Enum):
    URGENT = "urgent"
    NORMAL = "normal"
    FLEXIBLE = "flexible"
    UNKNOWN = "inconnu"


class QuoteRequest(BaseModel):
    is_quote_request: bool = Field(
        True,
        description="True if the message asks for a quote or for work to be done. False for anything else (questions about opening hours, spam, complaints...)",)
    
    # Contact
    name: Optional[str] = Field(None, description="Full name of the prospect")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")

    # Job
    site_address: Optional[str] = Field(None, description="Address of the work site")
    work_types: list[WorkType] = Field(default_factory=list, description="Types of work requested")
    description: Optional[str] = Field(None, description="Short summary of the need")

    # Timing
    urgency: Urgency = Field(Urgency.UNKNOWN, description="Urgency level")
    availability: Optional[str] = Field(None, description="When the prospect is available")

    # Qualification
    missing_fields: list[str] = Field(default_factory=list, description="Important information not given in the message")
    
    @field_validator(
        "name", "email", "phone", "site_address", "availability", "description",
        mode="before",
    )
    @classmethod
    def empty_if_no_content(cls, value):
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        placeholders = {"null", "none", "n/a", "na", "inconnu", "non précisé", "non renseigné"}
        if not any(c.isalnum() for c in cleaned) or cleaned.lower() in placeholders:
            return None
        return cleaned
    
if __name__ == "__main__":
    test = QuoteRequest(name="Marie Dupont", work_types=[WorkType.PLUMBING])
    print(test.model_dump_json(indent=2))