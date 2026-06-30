# Enterprise ETL Candidate Transformer

This project is a deterministic, multi-source Data Engineering pipeline designed to ingest candidate information from structured (CSV) and unstructured (PDF/Text) sources, resolve conflicts, and emit a perfectly shaped, schema-valid JSON canonical record.

## Features
- **Strict Schema Enforcement:** Output is strictly validated against a 13-key canonical schema using `jsonschema`.
- **Advanced Merge Engine:** Resolves conflicts using Field-Priority, Recency, and Corroboration voting.
- **Projection Layer:** Decoupled architecture allowing runtime JSON configs to safely reshape the output without mutating the core canonical record.
- **Graceful Degradation:** Handles corrupted or missing inputs by emitting schema-valid JSON with warnings rather than fatal crashes.
- **Algorithmic Confidence:** Dynamically assigns trust scores based on source reliability and cross-source corroboration.

## Setup & Installation
1. Ensure you have Python 3.9+ installed.
2. Clone this repository and navigate to the root folder.
3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Pipeline

### 1. Default Canonical Output
To generate the strict 13-key canonical profile:
```bash
python pipeline.py --csv input/recruiter.csv --resume input/resume.txt --output output_default.json
```

### 2. Custom Projected Output
To apply a runtime configuration that reshapes the data (e.g., renaming fields, omitting provenance):
```bash
python pipeline.py --csv input/recruiter.csv --resume input/resume.txt --config input/config_custom.json --output output_custom.json
```

## Running the Test Suite
The project includes an automated test suite verifying the pipeline's robustness against fatal edge cases (corrupted PDFs, empty CSVs). To run the tests:
```bash
python -m unittest tests/test_robustness.py
```

## Output Examples
- **`output_default.json`**: The strict canonical schema with full provenance logging and confidence scoring.
- **`output_custom.json`**: A reshaped API response derived from `config_custom.json`.
