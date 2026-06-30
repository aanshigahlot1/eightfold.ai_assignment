import phonenumbers
from typing import Any, Optional
import re

class DataNormalizer:
    """
    Responsibility: Pure functions to standardize atomic data types before merging.
    """
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """Emails -> Lowercase, Trim whitespace"""
        if not email:
            return ""
        return email.strip().lower()

    @staticmethod
    def normalize_phone(phone: str) -> Optional[str]:
        """Phones -> Convert to E.164"""
        if not phone:
            return None
        try:
            parsed = phonenumbers.parse(phone, "US") # Default region
            # We use is_possible_number instead of is_valid_number because
            # valid number rejects fake '555' area codes which are common in tests.
            if phonenumbers.is_possible_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            pass
        return None

    @staticmethod
    def normalize_skill(skill: str) -> str:
        """
        Skills -> Canonical names
        Example: NodeJS -> Node.js
        """
        if not skill:
            return ""
        skill = skill.strip()
        # A mock canonicalization dictionary
        canonical_map = {
            "nodejs": "Node.js",
            "reactjs": "React",
            "vuejs": "Vue"
        }
        return canonical_map.get(skill.lower(), skill)
        
    @staticmethod
    def normalize(field: str, value: Any) -> Any:
        """Route to appropriate normalizer based on field name"""
        # If it's a list, recursively normalize each item
        if isinstance(value, list):
            return [DataNormalizer.normalize(field, item) for item in value]
            
        if not isinstance(value, str):
            return value
            
        if field == "emails":
            return DataNormalizer.normalize_email(value)
        elif field == "phones":
            return DataNormalizer.normalize_phone(value)
        elif field == "skills":
            return DataNormalizer.normalize_skill(value)
            
        return value.strip() if isinstance(value, str) else value
