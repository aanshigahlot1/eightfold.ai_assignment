import json
import argparse
import sys
from typing import List, Dict, Any

from src.extractors.structured import CSVParser
from src.extractors.unstructured import ResumeTextExtractor, ResumeInformationExtractor
from src.mapper.canonical_mapper import CanonicalMapper
from src.merger.engine import MergeEngine
from src.projector.engine import ProjectionEngine, fill_default_schema
from src.validator.schema_validator import OutputValidator
from src.models import ExtractedField

class SourceManager:
    """
    Responsibility: Detect files, validate inputs, route to appropriate parser.
    """
    def __init__(self, csv_path: str = None, resume_path: str = None):
        self.csv_path = csv_path
        self.resume_path = resume_path
        
    def process(self) -> List[ExtractedField]:
        mapper = CanonicalMapper()
        all_fields = []
        
        # 1. Route to CSV Parser
        if self.csv_path:
            csv_parser = CSVParser(self.csv_path)
            for record in csv_parser.parse():
                record["_timestamp"] = 2.0 # Simulate newer CSV
                fields = mapper.map_record(record)
                all_fields.extend(fields)
                
        # 2. Route to Resume Parsers
        if self.resume_path:
            text_extractor = ResumeTextExtractor(self.resume_path)
            raw_text = text_extractor.extract_text()
            
            info_extractor = ResumeInformationExtractor(raw_text)
            record = info_extractor.extract()
            record["_timestamp"] = 1.0 # Simulate older Resume
            
            fields = mapper.map_record(record)
            all_fields.extend(fields)
            
        return all_fields

def run_pipeline(csv_path: str, resume_path: str) -> Dict[str, Any]:
    """Runs extraction and merging, returning the strict, fully-shaped default canonical schema."""
    manager = SourceManager(csv_path=csv_path, resume_path=resume_path)
    all_fields = manager.process()
    
    if not all_fields:
        print("No data extracted. Exiting.")
        sys.exit(0)
        
    engine = MergeEngine()
    canonical_profile = engine.merge(all_fields)
    
    # Dump avoiding exclude_none to preserve all keys, then enforce the strict default schema
    canonical_dict = canonical_profile.model_dump(exclude_none=False)
    canonical_dict = fill_default_schema(canonical_dict)
    
    return canonical_dict

def main():
    parser = argparse.ArgumentParser(description="Enterprise ETL Candidate Transformer")
    parser.add_argument("--csv", help="Path to the recruiter CSV export")
    parser.add_argument("--resume", help="Path to the Resume text/pdf file")
    parser.add_argument("--config", help="Path to the JSON runtime configuration (optional)")
    args = parser.parse_args()
    
    # 1. Generate Canonical Record (Default Schema)
    canonical_dict = run_pipeline(args.csv, args.resume)
    
    with open("output_default.json", "w") as f:
        json.dump(canonical_dict, f, indent=2)
    print("Generated output_default.json (Canonical Default Schema)")
    
    # 2. Generate Custom Projected Record (If Config Provided)
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Failed to load config: {e}")
            sys.exit(1)
            
        projector = ProjectionEngine(config)
        validator = OutputValidator(config)
        
        try:
            final_json = projector.project(canonical_dict)
            validator.validate(final_json)
            with open("output_custom.json", "w") as f:
                json.dump(final_json, f, indent=2)
            print("Generated output_custom.json (Projected Output)")
        except ValueError as e:
            print(f"Pipeline failed at Validation Layer: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
