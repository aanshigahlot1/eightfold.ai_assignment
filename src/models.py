from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# INTERMEDIATE DOMAIN MODELS (Unified Candidate Record)
# ---------------------------------------------------------

class ExtractedField(BaseModel):
    """
    The fundamental unit of our ETL pipeline. 
    Instead of passing around giant flat dictionaries, Parsers/Mappers yield
    individual fields. This makes the Merge Engine purely functional and source-agnostic.
    """
    field: str           # The canonical field name (e.g., 'emails', 'phones')
    value: Any           # The parsed value (could be a string, dict, or list)
    source: str          # Where it came from (e.g., 'resume_pdf', 'csv')
    raw_value: Any       # The exact string before mapping/normalization for provenance tracking
    
    # Metadata for advanced tie-breakers
    timestamp: float = 0.0          # Unix epoch, for recency-based resolution
    specificity_score: int = 0      # Length of string or count of dict keys


# ---------------------------------------------------------
# CANONICAL OUTPUT MODELS (Final Source of Truth)
# ---------------------------------------------------------

class Location(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None

class Links(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    other: List[str] = Field(default_factory=list)

class Experience(BaseModel):
    company: str
    title: str
    start: Optional[str] = None
    end: Optional[str] = None
    summary: Optional[str] = None
    
    def __eq__(self, other):
        if not isinstance(other, Experience): return False
        return self.company == other.company and self.title == other.title

class Education(BaseModel):
    institution: str
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[int] = None
    
    def __eq__(self, other):
        if not isinstance(other, Education): return False
        return self.institution == other.institution

class Skill(BaseModel):
    name: str
    confidence: float
    sources: List[str]

class ProvenanceRecord(BaseModel):
    """Tracks exactly how a final value was decided upon."""
    field: str
    source: str
    raw_value: Any
    normalized_value: Any
    method: str

class CanonicalProfile(BaseModel):
    """
    The single internal source of truth.
    This is what the Merge Engine produces and what the Validator checks.
    """
    candidate_id: str
    full_name: str
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    location: Optional[Location] = None
    links: Links = Field(default_factory=Links)
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: List[Skill] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    
    # Metadata
    provenance: List[ProvenanceRecord] = Field(default_factory=list)
    field_confidence: Dict[str, float] = Field(default_factory=dict)
    overall_confidence: float = 0.0
