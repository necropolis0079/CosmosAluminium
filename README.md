# LCMGoCloud-CAGenAI

GenAI HR Assistant for Cosmos Aluminium - Industrial Manufacturing Recruitment System

## Overview

AI-powered CV processing and candidate search system for Greek/English manufacturing recruitment.

### Key Features

- **Triple OCR Pipeline**: Claude Vision + Tesseract + AWS Textract
- **Text-to-SQL Queries**: Natural language to SQL with 54% cost savings
- **Multilingual**: Greek + English with Greeklish detection
- **Vector Search**: Cohere Embed v3 + OpenSearch hybrid search
- **GDPR Compliant**: Built-in data protection

## Architecture

- **Region**: eu-north-1 (Stockholm)
- **Compute**: AWS Lambda (Python 3.11)
- **Database**: PostgreSQL (RDS) + OpenSearch
- **AI**: Claude 4.5 (Sonnet/Opus) via Amazon Bedrock
- **State**: DynamoDB for CV processing state machine

## Project Structure

```
lcmgocloud_ca_genai_2026/
├── src/lcmgo_cagenai/       # Main package
│   ├── llm/                  # LLM abstraction layer
│   ├── ocr/                  # OCR processing
│   ├── query/                # Query translation & SQL generation
│   ├── models/               # Data models
│   └── utils/                # Utilities
├── lambda/                   # Lambda handlers
├── tests/                    # Test suite
├── infra/terraform/          # Infrastructure as Code
├── prompts/                  # Versioned prompt templates
└── config/                   # Configuration files
```

## Naming Convention

All AWS resources follow: `lcmgo-cagenai-prod-{service}-{component}-eun1`

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install -r requirements-dev.txt
```

## Documentation

See `D:\CA\docs\` for full documentation:
- Architecture: `01-PROJECT-OVERVIEW.md`
- Database: `03-DATABASE-SCHEMA.md`
- API: `11-API-REFERENCE.md`

## License

Proprietary - LCMGoCloud / Cosmos Aluminium
