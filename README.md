# Enterprise ETL Candidate Transformer

A deterministic, multi-source data engineering pipeline that ingests candidate information from structured (CSV) and unstructured (Resume PDF/Text) sources, resolves conflicts using a cascading merge engine, and emits a perfectly shaped, schema-valid JSON canonical record.

## What It Does

Recruiters feed candidate data from multiple places — CSVs, resumes, ATS exports. The same person appears in several sources with conflicting or incomplete values. This pipeline ingests all of it, resolves every conflict with a documented policy, and outputs one clean, trustworthy profile per candidate. Every value is traceable to its source. Wrong-but-confident is never the outcome — unknown values become explicit `null`, never invented.

## Architecture

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

The canonical record and the projected output are two separate code paths. `run_pipeline()` always returns the full default schema, unmodified. `ProjectionEngine` is the only place renaming, field selection, and `on_missing` logic are allowed — it reads the canonical record but never mutates it.

## Canonical Output Schema

All 13 keys are always present in `output_default.json`. Missing data → explicit `null`, never an omitted key.

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

## Merge & Conflict Resolution

Instead of a naive last-in-wins rule, the `MergeEngine` evaluates each candidate value using a weighted tuple: `(ValidationScore, PriorityScore, SpecificityScore)`. Resolution follows a 5-step cascade — each tiebreaker only fires when the one above it fails to resolve the conflict.

| Step | Tiebreaker | Rule |
|---|---|---|
| 1 | Single source | Only one source has a value → use it immediately |
| 2 | Field priority | Resume wins for self-described fields (`full_name`, `headline`, `skills`, `experience`). CSV wins for recruiter-verified fields (`phones`, `emails`) |
| 3 | Specificity | More complete value wins regardless of step 2 — "Austin, TX" beats "USA" |
| 4 | Recency | More recently-dated source wins for time-sensitive fields (`headline`, `current_company`) |
| 5 | Format validity | Well-formed value wins as final tiebreaker (valid E.164 beats malformed string) |

Array fields (`emails`, `phones`, `skills`) use union + deduplication, not winner-takes-all. Every distinct normalised value is kept. For skills, corroboration voting applies: a skill seen in multiple sources, or from a high-trust source, receives confidence `0.95`; an uncorroborated low-trust skill receives `0.50`.

Provenance logs both winners (`field_priority_winner`) and overridden candidates (`ignored_lower_priority`) — every decision is 100% traceable.

## Runtime Config — Configurable Output

Pass a JSON config to the `ProjectionEngine` to reshape the output without touching any pipeline code. The config supports:

- Select a subset of fields to include
- Rename a field via the `from` key (reads from a canonical path, writes under a new key)
- Flatten arrays using `[]` path syntax — `skills[].name` maps over the array and plucks one subkey
- `on_missing` policy per field or globally: `null` (key present, value null) · `omit` (key absent) · `error` (raises, run stops)
- Toggle `include_confidence` and `include_provenance` on or off

Example config (`input/config_custom.json`):

```json
{
  "fields": [
    { "path": "full_name" },
    { "path": "primary_email",  "from": "emails[0]" },
    { "path": "phone",          "from": "phones[0]" },
    { "path": "skill_names",    "from": "skills[].name" }
  ],
  "include_confidence": true,
  "include_provenance": false,
  "on_missing": "null"
}
```

## Setup & Installation

Requires Python 3.9+.

```bash
git clone <your-repo-url>
cd candidate-transformer
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

**Dependencies:** `pdfminer.six` · `spacy` · `phonenumbers` · `dateparser` · `pycountry` · `jsonschema`

## Running the Pipeline

Default canonical output — full 13-key schema with provenance and confidence:

```bash
python pipeline.py --csv input/recruiter.csv --resume input/resume.txt --output output_default.json
```

Custom projected output — reshaped via a runtime config:

```bash
python pipeline.py --csv input/recruiter.csv --resume input/resume.txt \
  --config input/config_custom.json --output output_custom.json
```

Robustness runs — verify graceful degradation:

```bash
# Missing resume
python pipeline.py --csv input/recruiter.csv --output output_missing_resume.json

# Corrupted PDF
python pipeline.py --csv input/recruiter.csv --resume input/corrupt.pdf --output output_corrupt.json

# Empty CSV
python pipeline.py --csv input/empty.csv --resume input/resume.txt --output output_empty_csv.json
```

In each case the pipeline completes without raising. Fields from the absent/broken source fall back to `null`. A `_validation_warning` key is injected if the output fails schema validation — it never crashes.

## Running the Tests

```bash
python -m unittest tests/test_robustness.py
```

The test suite covers the corrupted-PDF and empty-CSV edge cases, asserting that all 13 canonical keys are present in the output and no exception is raised.

## Output Files

| File | Description |
|---|---|
| `output_default.json` | Full 13-key canonical schema — provenance, confidence, all fields |
| `output_custom.json` | Reshaped API response derived from `config_custom.json` |
| `output_missing_resume.json` | Canonical record produced with no resume input |
| `output_corrupt.json` | Canonical record produced with an unreadable PDF |
| `output_empty_csv.json` | Canonical record produced with a header-only CSV |

## Design Decisions & Descoped Features

| Feature | Decision |
|---|---|
| NLP/NER for resume extraction | Regex heuristics used instead of spaCy NER or LLM — keeps the pipeline fully deterministic. A production upgrade would swap in a lightweight Transformers model for better accuracy on free-form prose. |
| LinkedIn / ATS JSON sources | Field-map addition is trivial; descoped due to time. LinkedIn requires auth and cannot be scraped reliably. |
| OCR on scanned PDFs | Requires tesseract; heavy dependency. Image-only PDFs return empty text — pipeline handles this gracefully via null extraction. |
| Random vs deterministic `candidate_id` | Chose deterministic MD5 hash over UUID to satisfy the determinism constraint — same input always produces the same ID. |
