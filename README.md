# Enterprise ETL Candidate Transformer

This project is a deterministic, multi-source Data Engineering pipeline designed to ingest candidate information from structured (CSV) and unstructured (PDF/Text) sources, resolve conflicts, and emit a perfectly shaped, schema-valid JSON canonical record.

## Architecture & Features

- **Strict Schema Enforcement:** Output is strictly validated against a 13-key canonical schema using `jsonschema`.
- **Advanced Merge Engine:** Resolves conflicts using Field-Priority (Winner-Takes-All) and Corroboration voting systems.
- **Projection Layer:** Decoupled architecture allowing runtime JSON configs to safely reshape the output (e.g., renaming fields, flattening arrays) without mutating the core canonical backend record.
- **Graceful Degradation:** Handles corrupted or missing inputs by emitting schema-valid JSON with warnings rather than throwing fatal Python crashes.
- **Deterministic Hashing:** `candidate_id` is generated via an MD5 hash of core normalized inputs, ensuring stable identifiers across identical runs.

## Setup & Installation

1. Ensure you have Python 3.9+ installed.
2. Clone this repository and navigate to the root folder.
3. (Recommended) Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

4. Install the required dependencies:

```bash
pip install -r requirements.txt
```

5. Download the spaCy language model used for resume NER extraction:

```bash
python -m spacy download en_core_web_sm
```

**Dependencies:** `pdfminer.six` · `spacy` · `phonenumbers` · `dateparser` · `pycountry` · `jsonschema`

## Pipeline Overview

The pipeline runs two parallel ingestion tracks — one for structured CSV data, one for unstructured resume text — that converge into a shared normalized shape before merging:

```
Recruiter CSV                     Resume PDF / Text
      │                                   │
      ▼                                   ▼
 CSV Field Mapper                 NLP Field Extractor
 (alias lookup table)             (regex + spaCy NER)
      │                                   │
      ▼                                   ▼
  DataNormalizer  ◄─────────────  DataNormalizer
  E.164 · YYYY-MM · ISO-3166 · lowercase email
      │
      ▼
 SourceRecord [ ]   ←  shared flat shape, both tracks
      │
      ▼
  MergeEngine
  cascading 3-factor weighted tuple:
  (ValidationScore, PriorityScore, SpecificityScore)
      │
      ▼
 fill_default_schema()
 guarantees all 13 canonical keys present
      │
      ▼
 Confidence Scorer
      │
      ├─────────────────────────┐
      ▼                         ▼
output_default.json     ProjectionEngine
(full 13-key schema)    (runtime config reshapes output)
                                │
                                ▼
                        output_custom.json
```

`run_pipeline()` always returns the full canonical schema, unmodified. The `ProjectionEngine` reads that canonical record and reshapes it for a specific output — it never mutates the underlying record.

## Canonical Structure

Every run of `run_pipeline()` produces a record with these 13 keys, always present — missing data becomes an explicit `null`, never an omitted key:

| Field | Type | Format |
|---|---|---|
| `candidate_id` | string | MD5 hash of normalised email/name+phone — stable across identical runs |
| `full_name` | string \| null | Winner per merge cascade |
| `emails` | string[] | lowercase, all distinct addresses kept |
| `phones` | string[] | E.164 (`+15551234567`) |
| `location` | object | `{city, region, country}` — country as ISO-3166 alpha-2 |
| `links` | object | `{linkedin, github, portfolio, other[]}` |
| `headline` | string \| null | — |
| `years_experience` | number \| null | Computed from experience date spans |
| `skills` | object[] | `[{name, confidence, sources[]}]` — canonical names |
| `experience` | object[] | `[{company, title, start, end, summary}]` — dates as `YYYY-MM` |
| `education` | object[] | `[{institution, degree, field, end_year}]` |
| `provenance` | object[] | `[{field, source, raw_value, normalized_value, method}]` |
| `overall_confidence` | number | Mean of field scores, rounded to 2 dp |

## Running the Pipeline

### 1. Default Canonical Output

To generate the strict 13-key canonical profile:

```bash
python pipeline.py --csv input/recruiter.csv --resume input/resume.txt --output output_default.json
```

### 2. Custom Projected Output

To apply a runtime configuration that reshapes the data based purely on a projection layer:

```bash
python pipeline.py --csv input/recruiter.csv --resume input/resume.txt --config input/config_custom.json --output output_custom.json
```

## Running the Test Suite

The project includes an automated test suite verifying the pipeline's robustness against fatal edge cases (corrupted PDFs, empty CSVs). To run the tests:

```bash
python -m unittest tests/test_robustness.py
```

## Output Examples

- `output_default.json`: The strict canonical schema with full provenance logging and algorithmic confidence scoring.
- `output_custom.json`: A reshaped API response derived securely from `config_custom.json`.
