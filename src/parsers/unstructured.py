import re
from typing import Dict, Any, List

class ResumeTextExtractor:
    """
    Responsibility: Extract raw text from PDF. Do not perform parsing.
    For this assignment's current scope, we will simulate this by reading a text file,
    but this class is where PyPDF2 or pdfplumber logic would go without polluting the parser.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath

    def extract_text(self) -> str:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading resume {self.filepath}: {e}")
            return ""


class ResumeInformationExtractor:
    """
    Responsibility: Extract Name, Email, Phone, Skills, Experience, Education using regex.
    """
    def __init__(self, text: str):
        self.text = text

    def extract(self) -> Dict[str, Any]:
        if not self.text.strip():
            return {}

        parsed_record = {
            "_source": "resume_pdf",
            "_raw": {"text": self.text}
        }

        # 1. Email Extraction
        result = {"_source": "resume_pdf"}
        
        name_match = re.search(r"Name:\s*(.+)", self.text)
        if name_match: result["full_name"] = name_match.group(1).strip()
            
        email_match = re.search(r"Email:\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", self.text)
        if email_match: result["emails"] = email_match.group(1).strip()
            
        phone_match = re.search(r"Phone:\s*(.+)", self.text)
        if phone_match: result["phones"] = phone_match.group(1).strip()
        
        loc_match = re.search(r"Location:\s*(.+)", self.text)
        if loc_match:
            parts = [p.strip() for p in loc_match.group(1).split(',')]
            from src.models import Location
            result["location"] = Location(
                city=parts[0] if len(parts) > 0 else None,
                region=parts[1] if len(parts) > 1 else None,
                country=parts[2] if len(parts) > 2 else None
            )
            
        head_match = re.search(r"Headline:\s*(.+)", self.text)
        if head_match: result["headline"] = head_match.group(1).strip()
            
        skills_match = re.search(r"Skills:\s*(.+)", self.text)
        if skills_match:
            skills = [s.strip() for s in skills_match.group(1).split(',')]
            result["skills"] = skills
            
        edu_match = re.search(r"Education:\s*(.+)", self.text)
        if edu_match:
            parts = [p.strip() for p in edu_match.group(1).split(',')]
            from src.models import Education
            result["education"] = [Education(
                degree=parts[0].split()[0] if parts else None,
                field=" ".join(parts[0].split()[1:]) if parts else None,
                institution=parts[1] if len(parts) > 1 else "Unknown",
                end_year=int(parts[2]) if len(parts) > 2 else None
            )]
            
        exp_match = re.search(r"Experience:\s*(.+?)\s*-\s*(.+?)\s*\((.+?)\)", self.text)
        if exp_match:
            result["company"] = exp_match.group(1).strip()
            result["title"] = exp_match.group(2).strip()
            result["summary"] = exp_match.group(3).strip()
            
        return result
