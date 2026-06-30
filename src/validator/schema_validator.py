import jsonschema
from typing import Dict, Any, List

CANONICAL_SCHEMA = {
    "type": "object",
    "required": [
        "candidate_id", "full_name", "emails", "phones", "location", "links",
        "headline", "years_experience", "skills", "experience", "education",
        "provenance", "overall_confidence"
    ],
    "properties": {
        "candidate_id": {"type": "string"},
        "full_name": {"type": ["string", "null"]},
        "emails": {"type": "array", "items": {"type": "string"}},
        "phones": {"type": "array", "items": {"type": "string"}},
        "location": {"type": "object"},
        "links": {"type": "object"},
        "headline": {"type": ["string", "null"]},
        "years_experience": {"type": ["number", "null"]},
        "skills": {"type": "array"},
        "experience": {"type": "array"},
        "education": {"type": "array"},
        "provenance": {"type": "array"},
        "overall_confidence": {"type": "number"}
    }
}

class OutputValidator:
    """
    Responsibility: Validate output schema against strict Canonical Schema.
    Degrades gracefully by injecting a warning instead of crashing.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def validate(self, projected_data: Dict[str, Any]) -> bool:
        """
        Validates the output against CANONICAL_SCHEMA if no config is present (Default Schema),
        or against custom rules if config is present.
        """
        if not self.config:
            # Validate against strict canonical schema
            try:
                jsonschema.validate(instance=projected_data, schema=CANONICAL_SCHEMA)
            except jsonschema.exceptions.ValidationError as e:
                projected_data["_validation_warning"] = f"Canonical Schema Violation: {e.message}"
                return False
            return True
            
        # Custom projection validation
        fields_config = self.config.get("fields", [])
        warnings = []
        for field in fields_config:
            target_path = field.get("path")
            is_required = field.get("required", False)
            expected_type = field.get("type", None)
            
            val = projected_data.get(target_path)
            
            if is_required and val is None:
                warnings.append(f"Required field '{target_path}' is missing.")
                
            if val is not None and expected_type:
                if expected_type == "string" and not isinstance(val, str):
                     warnings.append(f"'{target_path}' must be a string, got {type(val)}")
                elif expected_type == "string[]" and not isinstance(val, list):
                     warnings.append(f"'{target_path}' must be a list, got {type(val)}")
                     
        if warnings:
            projected_data["_validation_warning"] = " | ".join(warnings)
            return False
            
        return True
