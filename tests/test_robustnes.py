import unittest
import os
import json
from pipeline import run_pipeline
from src.validator.schema_validator import OutputValidator

class TestRobustness(unittest.TestCase):
    def setUp(self):
        # Create dummy corrupted inputs
        self.corrupt_pdf_path = "tests/corrupt_resume.pdf"
        self.empty_csv_path = "tests/empty.csv"
        
        with open(self.corrupt_pdf_path, "wb") as f:
            f.write(b"This is not a real PDF file! It should break the parser.")
            
        with open(self.empty_csv_path, "w") as f:
            f.write("candidate_id,name,email,phone\n") # headers only
            
    def tearDown(self):
        if os.path.exists(self.corrupt_pdf_path):
            os.remove(self.corrupt_pdf_path)
        if os.path.exists(self.empty_csv_path):
            os.remove(self.empty_csv_path)

    def test_pipeline_with_corrupt_pdf_and_empty_csv(self):
        """
        Verify that passing a corrupt PDF and empty CSV does not crash the pipeline,
        and still generates a fully formed 13-key canonical output.
        """
        canonical_dict = run_pipeline(csv_path=self.empty_csv_path, resume_path=self.corrupt_pdf_path)
        
        # Verify it didn't crash and returns the dict
        self.assertIsInstance(canonical_dict, dict)
        
        # Verify strict validation passes (the schema validator verifies the 13 keys)
        validator = OutputValidator({})
        is_valid = validator.validate(canonical_dict)
        self.assertTrue(is_valid, f"Validation failed: {canonical_dict.get('_validation_warning')}")
        
        # Verify confidence is low because it's empty
        self.assertEqual(canonical_dict["overall_confidence"], 0.0)

if __name__ == "__main__":
    unittest.main()