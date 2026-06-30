from typing import List, Dict, Any
from src.models import ExtractedField

class CanonicalMapper:
    """
    Responsibility: Take raw dictionaries from ANY parser and map them to the EAV format (ExtractedField).
    After this stage, everything is source independent.
    """
    
    # Mapping of raw parser keys to Canonical Profile field names
    # e.g., 'mobile' -> 'phones', 'job_title' -> 'headline'
    KEY_MAPPINGS = {
        "email": "emails",
        "phone": "phones",
        "name": "full_name",
        "skills": "skills",
        "headline": "headline"
    }

    def map_record(self, parsed_record: Dict[str, Any]) -> List[ExtractedField]:
        fields: List[ExtractedField] = []
        source = parsed_record.get("_source", "unknown")
        timestamp = parsed_record.get("_timestamp", 0.0)
        
        def calc_specificity(val):
            if isinstance(val, str): return len(val)
            if isinstance(val, dict): return len([v for v in val.values() if v])
            if hasattr(val, "model_dump"): return len([v for v in val.model_dump().values() if v])
            if isinstance(val, list): return len(val)
            return 0
            
        # 1. Handle simple fields
        for raw_key, value in parsed_record.items():
            if raw_key.startswith("_") or raw_key in ("company", "title", "summary"):
                continue
                
            canonical_key = self.KEY_MAPPINGS.get(raw_key, raw_key)
            extracted = ExtractedField(
                field=canonical_key,
                value=value,
                source=source,
                raw_value=value,
                timestamp=timestamp,
                specificity_score=calc_specificity(value)
            )
            fields.append(extracted)
            
        # 2. Handle Experience mapping
        company = parsed_record.get("company")
        title = parsed_record.get("title")
        summary = parsed_record.get("summary")
        if company or title:
            from src.models import Experience
            exp = Experience(company=company or "", title=title or "", summary=summary)
            fields.append(ExtractedField(
                field="experience",
                value=[exp],  # Always wrap complex objects in lists if they belong to array fields
                source=source,
                raw_value={"company": company, "title": title, "summary": summary},
                timestamp=timestamp,
                specificity_score=calc_specificity(exp)
            ))
            
        return fields
