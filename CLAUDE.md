# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Presidio is a context-aware, pluggable PII (Personally Identifiable Information) de-identification service for text and images. It consists of multiple Python packages:

- **presidio-analyzer**: Detects PII entities in text using NLP models, regex patterns, and custom recognizers
- **presidio-anonymizer**: Anonymizes/de-identifies detected PII entities using various operators (redact, replace, encrypt, etc.)
- **presidio-image-redactor**: Redacts PII from images (including DICOM medical images) using OCR
- **presidio-structured**: Handles PII detection and anonymization in structured data (CSV, JSON, etc.)
- **presidio-cli**: Command-line interface for Presidio

## Development Commands

### Setting up Development Environment

```bash
# Install Poetry (used for dependency management)
pip install poetry

# For each package (e.g., presidio-analyzer)
cd presidio-analyzer
poetry install --all-extras

# Download spaCy models (for analyzer)
poetry run python -m spacy download en_core_web_lg
```

### Running Tests

```bash
# Run tests for a specific package
cd presidio-analyzer  # or presidio-anonymizer, etc.
poetry run pytest

# Run specific test file
poetry run pytest tests/test_analyzer_engine.py

# Run with verbose output
poetry run pytest -vv
```

### Linting and Code Quality

```bash
# Run linting with ruff (from project root)
ruff check

# Auto-fix linting issues
ruff check --fix

# Format code
ruff format
```

### Building Packages

```bash
# Build wheel for a package
cd presidio-analyzer
python -m build --wheel
```

### Running Services

```bash
# Run analyzer as HTTP server
cd presidio-analyzer
python app.py  # Runs on port 3000

# Using Docker
docker-compose up

# Run specific service with Docker
docker run -p 5002:3000 presidio-analyzer
```

### E2E Tests

```bash
# Run end-to-end tests
cd e2e-tests
pip install -r requirements.txt
pytest
```

## Architecture Overview

### Core Flow
1. **Text Analysis**: `AnalyzerEngine` processes text → identifies PII entities → returns `RecognizerResult` objects
2. **Anonymization**: `AnonymizerEngine` takes analyzer results → applies operators → returns anonymized text
3. **Image Processing**: `ImageRedactorEngine` uses OCR → analyzes text → redacts PII regions

### Key Components

**AnalyzerEngine**:
- Central orchestrator for PII detection
- Manages `RecognizerRegistry` (collection of entity recognizers)
- Uses `NlpEngine` (spaCy/Stanza/Transformers) for NER
- Applies `ContextAwareEnhancer` to improve detection accuracy

**Entity Recognizers**:
- `PatternRecognizer`: Regex-based detection
- NLP recognizers: SpacyRecognizer, TransformersRecognizer, StanzaRecognizer
- Custom recognizers: Extend `EntityRecognizer` base class
- Predefined recognizers organized by:
  - `generic/`: Credit cards, emails, URLs, etc.
  - `country_specific/<country>/`: SSN, passport numbers, etc.
  - `third_party/`: Azure AI Language, AHDS integrations

**Configuration**:
- YAML configuration files in `conf/` directories
- Default recognizers: `default_recognizers.yaml`
- NLP engine configs: `spacy.yaml`, `transformers.yaml`, `stanza.yaml`

### Adding New Recognizers

1. Create recognizer class in appropriate folder:
   - `predefined_recognizers/country_specific/<country>/` for country-specific
   - `predefined_recognizers/generic/` for universal patterns
2. Add to `conf/default_recognizers.yaml`
3. Update `__init__.py` imports
4. Add comprehensive tests

### Korean-Specific Components

The repository includes Korean PII handling:
- `kr_rrn_recognizer.py`: Korean Resident Registration Number detection
- `korea_expressway_pii_remover.py`: Custom script for Korean highway data
- Excel files with Korean test data

## Testing Best Practices

- Each package has its own `tests/` directory
- Use `pytest` fixtures in `conftest.py`
- Mock external dependencies using `pytest-mock`
- Test recognizers with various valid/invalid patterns
- Include edge cases and language-specific tests

## Important Notes

- Uses Poetry for dependency management (not pip directly)
- Supports Python 3.9-3.12
- NLP models must be downloaded separately
- Docker images available for all services
- Azure Pipelines for CI/CD