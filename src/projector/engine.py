from typing import Dict, Any, List
import re

DEFAULT_SCHEMA_KEYS = [
    "candidate_id", "full_name", "emails", "phones", "location", "links",
    "headline", "years_experience", "skills", "experience", "education",
    "provenance", "overall_confidence",
]

EMPTY_DEFAULTS = {
    "emails": [], "phones": [], "skills": [], "experience": [],
    "education": [], "provenance": [],
    "location": {"city": None, "region": None, "country": None},
    "links":    {"linkedin": None, "github": None, "portfolio": None, "other": []},
    "full_name": None, "headline": None, "years_experience": None,
    "overall_confidence": 0.0,
}

def fill_default_schema(canonical: dict) -> dict:
    for key in DEFAULT_SCHEMA_KEYS:
        if key not in canonical or canonical[key] is None:
            canonical[key] = EMPTY_DEFAULTS.get(key)
    
    canonical["overall_confidence"] = round(canonical.get("overall_confidence", 0.0), 2)
    
    for skill in canonical.get("skills", []):
        skill["confidence"] = round(skill["confidence"], 2)
        
    for exp in canonical.get("experience", []):
        for k in ["company", "title", "start", "end", "summary"]:
            if k not in exp:
                exp[k] = None
                
    return canonical

class ProjectionEngine:
    """
    Responsibility: Read runtime config and generate custom output without mutating the canonical record.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def project(self, canonical_dict: Dict[str, Any]) -> Dict[str, Any]:
        if not self.config:
            return canonical_dict
            
        data = canonical_dict
        result = {}
        fields_config = self.config.get("fields", [])
        on_missing = self.config.get("on_missing", "null")
        
        for field in fields_config:
            target_path = field.get("path")
            if not target_path:
                continue
                
            source_path = field.get("from", target_path)
            
            val = self._extract_value(data, source_path)
            
            # Apply missing value policy
            if val is None or val == "" or val == []:
                if on_missing == "omit":
                    continue
                elif on_missing == "error":
                    raise ValueError(f"Strict Policy Error: Field '{source_path}' is missing.")
                val = None

            result[target_path] = val

        if self.config.get("include_confidence", False):
            result["overall_confidence"] = data.get("overall_confidence", 0.0)
            result["field_confidence"] = data.get("field_confidence", {})
            
        if self.config.get("include_provenance", False):
            result["provenance"] = data.get("provenance", [])

        return result

    def _extract_value(self, data: Dict[str, Any], path: str) -> Any:
        """Lightweight JSON-path evaluator for e.g. emails[0] or skills[].name"""
        current = data
        parts = path.split('.')
        
        for part in parts:
            if current is None:
                return None
                
            match = re.match(r"([a-zA-Z0-9_]+)\[(\d*)\]", part)
            if match:
                key = match.group(1)
                idx_str = match.group(2)
                
                if isinstance(current, dict):
                    current = current.get(key, [])
                
                if not isinstance(current, list):
                    return None
                    
                if idx_str: # Specific index e.g. emails[0]
                    idx = int(idx_str)
                    if idx < len(current):
                        current = current[idx]
                    else:
                        return None
                else: # Wildcard array e.g. skills[]
                    # The remainder of the path needs to be mapped over the array
                    remaining_path = ".".join(parts[parts.index(part)+1:])
                    if not remaining_path:
                        return current # Just return the array
                    return [self._extract_value(item, remaining_path) for item in current if item is not None]
                    
            else:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
                    
        return current
