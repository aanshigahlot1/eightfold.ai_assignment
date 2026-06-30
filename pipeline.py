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
            try:
                csv_parser = CSVParser(self.csv_path)
                for record in csv_parser.parse():
                    record["_timestamp"] = 2.0 # Simulate newer CSV
                    fields = mapper.map_record(record)
                    all_fields.extend(fields)
            except Exception as e:
                print(f"Failed to process CSV {self.csv_path}: {e}")
                
        # 2. Route to Resume Parsers
        if self.resume_path:
            text_extractor = ResumeTextExtractor(self.resume_path)
            raw_text = text_extractor.extract_text()
            
            info_extractor = ResumeInformationExtractor(raw_text)
            record = info_extractor.extract()
            
            if record:
                record["_timestamp"] = 1.0 # Simulate older Resume
                fields = mapper.map_record(record)
                all_fields.extend(fields)
            
        return all_fields

def run_pipeline(csv_path: str, resume_path: str) -> Dict[str, Any]:
    """Runs extraction and merging, returning the strict, fully-shaped default canonical schema."""
    manager = SourceManager(csv_path=csv_path, resume_path=resume_path)
    all_fields = manager.process()
    
    # If no data extracted, pass empty fields to MergeEngine. It will generate an empty profile.
    if not all_fields:
        print("Warning: No data extracted from any sources. Generating empty canonical record.")
        
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
    parser.add_argument("--output", required=True, help="Path to save the output JSON file")
    args = parser.parse_args()
    
    # 1. Generate Canonical Record (Default Schema)
    canonical_dict = run_pipeline(args.csv, args.resume)
    
    # 2. Apply Custom Projected Record (If Config Provided)
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Failed to load config: {e}")
            sys.exit(1)
            
        projector = ProjectionEngine(config)
        final_json = projector.project(canonical_dict)
    else:
        config = {}
        final_json = canonical_dict
        
    # 3. Validate
    validator = OutputValidator(config)
    validator.validate(final_json)
    
    if "_validation_warning" in final_json:
        print(f"Validation Warning: {final_json['_validation_warning']}")
        
    # 4. Save Output
    try:
        with open(args.output, "w") as f:
            json.dump(final_json, f, indent=2)
        print(f"Successfully generated {args.output} (Overall Confidence: {final_json.get('overall_confidence', 0.0)})")
    except Exception as e:
        print(f"Failed to write output to {args.output}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
