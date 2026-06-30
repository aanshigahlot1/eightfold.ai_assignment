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
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", self.text)
        if emails:
            parsed_record["email"] = emails[0] # Grab first email

        # 2. Phone Extraction (Basic regex looking for 10+ digits or formatted phones)
        phone_match = re.search(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", self.text)
        if phone_match:
            parsed_record["phone"] = phone_match.group(0)

        # 3. Name Extraction (Heuristic: Look for lines at the top, or explicitly labeled)
        name_match = re.search(r"(?i)(?:Name|Candidate):\s*([A-Za-z ]+)", self.text)
        if name_match:
            parsed_record["name"] = name_match.group(1).strip()
        
        # 4. Skills Extraction (Heuristic)
        skills_match = re.search(r"(?i)Skills:\s*(.+)(?:\n|$)", self.text)
        if skills_match:
            raw_skills = [s.strip() for s in re.split(r"[,|;]", skills_match.group(1))]
            parsed_record["skills"] = [s for s in raw_skills if s]

        return {k: v for k, v in parsed_record.items() if v}
