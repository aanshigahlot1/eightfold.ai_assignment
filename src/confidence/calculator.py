from typing import List, Dict
from src.models import ExtractedField

class ConfidenceCalculator:
    """
    Responsibility: Calculate per-field and overall confidence based on deterministic rules.
    """
    
    # Source reliability matrix
    SOURCE_RELIABILITY = {
        "resume_pdf": 0.9,
        "csv": 0.8,
        "github": 0.95
    }

    @classmethod
    def calculate_field_confidence(cls, winning_field: ExtractedField, all_candidates: List[ExtractedField]) -> float:
        """
        Calculates confidence for a single resolved field.
        Confidence = base_reliability * agreement_multiplier
        """
        base_conf = cls.SOURCE_RELIABILITY.get(winning_field.source, 0.5)
        
        if len(all_candidates) <= 1:
            return base_conf
            
        # Check agreement across sources (deterministic)
        agreements = sum(1 for f in all_candidates if f.value == winning_field.value)
        total_sources = len(all_candidates)
        
        # If all sources agree perfectly, boost confidence slightly
        if agreements == total_sources:
            return min(1.0, base_conf + 0.05)
            
        # If there are conflicts, penalize confidence slightly based on number of conflicts
        conflict_ratio = (total_sources - agreements) / total_sources
        penalty = conflict_ratio * 0.1
        
        return max(0.0, base_conf - penalty)

    @classmethod
    def calculate_overall(cls, field_confidences: Dict[str, float]) -> float:
        """Simple average of populated fields for overall confidence."""
        if not field_confidences:
            return 0.0
        return sum(field_confidences.values()) / len(field_confidences)
