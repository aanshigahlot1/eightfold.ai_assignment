import csv
from typing import Dict, List, Any

class CSVParser:
    """
    Structured Parser Responsibility: Read structured sources, map raw columns, extract structured fields.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath

    def parse(self) -> List[Dict[str, Any]]:
        results = []
        try:
            with open(self.filepath, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Normalize columns by lowercasing and stripping
                    raw_dict = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
                    
                    # We output a raw extracted dictionary. The Canonical Mapper will handle standardization.
                    parsed_record = {
                        "_source": "csv",
                        "_raw": raw_dict,
                        "name": raw_dict.get("name"),
                        "email": raw_dict.get("email"),
                        "phone": raw_dict.get("phone"),
                        "company": raw_dict.get("company"),
                        "title": raw_dict.get("title")
                    }
                    # Remove Nones
                    results.append({k: v for k, v in parsed_record.items() if v})
        except Exception as e:
            # We don't crash the pipeline, we return empty
            print(f"Error parsing CSV {self.filepath}: {e}")
            
        return results
