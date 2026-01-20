# Infrastructure Snapshot v1.1 - Pre-Deployment

**Snapshot Date**: 2026-01-20
**Git Commit**: `525b420a631fb8b0443799b3afb6ebe32ead9b41`
**Purpose**: Rollback reference before deploying HR Intelligence (Phases 1-4)

---

## 1. Git State

### 1.1 Current Branch
```
Branch: main
Commit: 525b420
Tag: (none - create before deployment)
```

### 1.2 Key Commits for Rollback

| Rollback Point | Commit | Description |
|----------------|--------|-------------|
| Pre-Phase 4 | `68b63b4` | Before Dynamic Taxonomy Aliases |
| Pre-Phase 3 | `9da65fd` | Before Query Lambda Integration |
| Pre-Phase 2 | `ba0e38e` | Before Job Posting Parser |
| Pre-Phase 1 | `2d36f11` | Before HR Intelligence Core |
| v1.0-stable | `47fa117` | Original stable baseline (Session 28) |

### 1.3 Create Rollback Tag

```bash
# Create tag before deployment
git tag v1.1-pre-deploy 525b420
git push origin v1.1-pre-deploy
git push github v1.1-pre-deploy

# Rollback command
git checkout v1.1-pre-deploy
```

---

## 2. Lambda Functions

### 2.1 Current Lambda State

| Function | Runtime | Memory | Timeout | Layer Version |
|----------|---------|--------|---------|---------------|
| lcmgo-cagenai-prod-query | Python 3.11 | 512 MB | 300s | v51 |
| lcmgo-cagenai-prod-cv-processor | Python 3.11 | 1024 MB | 600s | v51 |
| lcmgo-cagenai-prod-cv-parser | Python 3.11 | 1024 MB | 600s | v51 |
| lcmgo-cagenai-prod-upload | Python 3.11 | 256 MB | 30s | v51 |
| lcmgo-cagenai-prod-status | Python 3.11 | 256 MB | 30s | v51 |
| lcmgo-cagenai-prod-candidates | Python 3.11 | 512 MB | 60s | v51 |
| lcmgo-cagenai-prod-health | Python 3.11 | 256 MB | 10s | - |
| lcmgo-cagenai-prod-db-init | Python 3.11 | 256 MB | 60s | v1 (pg8000) |
| lcmgo-cagenai-prod-opensearch-init | Python 3.11 | 256 MB | 60s | v1 (opensearch) |

### 2.2 Lambda Layer Versions

| Layer | Current Version | Previous Stable |
|-------|-----------------|-----------------|
| lcmgo-cagenai-prod-lcmgo-package | **v51** | v41 |
| lcmgo-cagenai-prod-cv-processor | v6 | v6 |
| lcmgo-cagenai-prod-pg8000 | v1 | v1 |
| lcmgo-cagenai-prod-opensearch | v1 | v1 |
| lcmgo-cagenai-prod-tesseract-ocr | v1 | v1 |

### 2.3 Rollback Lambda Layer

```bash
# Rollback query Lambda to v41
aws lambda update-function-configuration \
  --function-name lcmgo-cagenai-prod-query \
  --layers arn:aws:lambda:eu-north-1:132934401449:layer:lcmgo-cagenai-prod-lcmgo-package:41 \
  --region eu-north-1

# Rollback cv-parser Lambda to v41
aws lambda update-function-configuration \
  --function-name lcmgo-cagenai-prod-cv-parser \
  --layers \
    arn:aws:lambda:eu-north-1:132934401449:layer:lcmgo-cagenai-prod-lcmgo-package:41 \
    arn:aws:lambda:eu-north-1:132934401449:layer:lcmgo-cagenai-prod-cv-processor:6 \
    arn:aws:lambda:eu-north-1:132934401449:layer:lcmgo-cagenai-prod-tesseract-ocr:1 \
  --region eu-north-1

# Rollback cv-processor Lambda to v41
aws lambda update-function-configuration \
  --function-name lcmgo-cagenai-prod-cv-processor \
  --layers \
    arn:aws:lambda:eu-north-1:132934401449:layer:lcmgo-cagenai-prod-lcmgo-package:41 \
    arn:aws:lambda:eu-north-1:132934401449:layer:lcmgo-cagenai-prod-cv-processor:6 \
    arn:aws:lambda:eu-north-1:132934401449:layer:lcmgo-cagenai-prod-tesseract-ocr:1 \
  --region eu-north-1
```

---

## 3. Database State

### 3.1 PostgreSQL

| Property | Value |
|----------|-------|
| Engine | PostgreSQL 15.10 |
| Endpoint | lcmgo-cagenai-prod-postgres.c324io6eq6iv.eu-north-1.rds.amazonaws.com |
| Database | cagenai |
| Schema Version | v4.0 |
| Tables | 33 |
| SQL Scripts | 19 (001-019) |

### 3.2 Key Tables (Counts)

| Table | Records |
|-------|---------|
| candidates | 31 |
| skill_taxonomy | 58 |
| role_taxonomy | 47 |
| software_taxonomy | 31 |
| certification_taxonomy | 38 |
| unmatched_taxonomy_items | ~100 |

### 3.3 Database Rollback

No schema changes in Phases 1-4. Data unchanged.

---

## 4. OpenSearch State

| Property | Value |
|----------|-------|
| Domain | lcmgo-cagenai-prod-search |
| Engine | OpenSearch 2.11 |
| Index | cosmos-hr-candidates-v1 |
| Documents | 31 |

### 4.1 OpenSearch Rollback

No index changes in Phases 1-4. Data unchanged.

---

## 5. S3 State

| Bucket | Objects | Purpose |
|--------|---------|---------|
| lcmgo-cagenai-prod-cv-uploads-eun1 | ~50 | CV uploads |
| lcmgo-cagenai-prod-processed-eun1 | ~50 | Processed CVs |
| lcmgo-cagenai-prod-lambda-artifacts-eun1 | ~20 | Lambda code |
| lcmgo-cagenai-prod-tfstate-eun1 | 1 | Terraform state |

---

## 6. DynamoDB State

| Table | Items | Purpose |
|-------|-------|---------|
| lcmgo-cagenai-prod-cv-processing-state | ~50 | CV processing status |
| lcmgo-cagenai-prod-query-cache | ~10 | Query cache |
| lcmgo-cagenai-prod-user-sessions | 0 | User sessions |
| lcmgo-cagenai-prod-prompt-versions | 0 | Prompt versioning |

---

## 7. API Gateway State

| Property | Value |
|----------|-------|
| API ID | iw9oxe3w4b |
| Stage | v1 |
| Endpoint | https://iw9oxe3w4b.execute-api.eu-north-1.amazonaws.com/v1 |

### 7.1 Routes

| Method | Path | Lambda | Auth |
|--------|------|--------|------|
| GET | /health | health | None |
| POST | /query | query | JWT |
| POST | /test/upload | upload | None |
| GET | /test/status/{id} | status | None |
| POST | /test/query | query | None |
| GET | /test/candidates | candidates | None |
| GET | /test/candidates/{id} | candidates | None |
| DELETE | /test/candidates/{id} | candidates | None |

---

## 8. Terraform State

| Property | Value |
|----------|-------|
| Backend | S3 (lcmgo-cagenai-prod-tfstate-eun1) |
| State File | terraform.tfstate |
| Resources | 177 |
| Last Applied | 2026-01-20 (Session 36) |

### 8.1 Terraform Rollback

```bash
# View current state
cd D:\CA\repo\infra\terraform
terraform state list | wc -l

# Rollback via git (no infrastructure changes in Phases 1-4)
git checkout v1.1-pre-deploy -- infra/terraform/

# Re-apply if needed
terraform plan
terraform apply
```

---

## 9. Code Changes Summary

### 9.1 New Files (Phases 1-4)

```
src/lcmgo_cagenai/hr_intelligence/
├── __init__.py
├── schema.py
├── analyzer.py
├── prompt_builder.py
└── formatter.py

src/lcmgo_cagenai/parser/
└── job_parser.py (new)

src/lcmgo_cagenai/query/
└── dynamic_aliases.py (new)

prompts/hr_analysis/
└── v1.0.0.txt (new)

prompts/job_parsing/
└── v1.0.0.txt (new)

tests/
├── test_code_paths.py (new)
├── test_job_parser_paths.py (new)
├── test_integration_hr_job.py (new)
├── test_integration_query_hr.py (new)
└── unit/
    ├── test_hr_intelligence.py (new)
    ├── test_job_parser.py (new)
    └── test_dynamic_aliases.py (new)

docs/
├── IMPLEMENTATION-PHASES-1-4.md (new)
├── PHASE-1-2-IMPLEMENTATION.md (new)
└── SNAPSHOT-v1.1-pre-deployment.md (this file)
```

### 9.2 Modified Files

```
lambda/query/handler.py          # +150 lines (HR Intelligence integration)
src/lcmgo_cagenai/query/__init__.py  # +15 lines (dynamic_aliases exports)
src/lcmgo_cagenai/parser/__init__.py # +5 lines (job_parser exports)
```

### 9.3 No Changes

```
infra/terraform/*               # No infrastructure changes
scripts/sql/*                   # No schema changes
lambda/cv_processor/handler.py  # No changes
lambda/cv_parser/handler.py     # No changes
```

---

## 10. Rollback Procedures

### 10.1 Quick Rollback (Code Only)

```bash
# 1. Checkout previous version
git checkout v1.0-stable

# 2. Or checkout specific phase
git checkout 68b63b4  # Before Phase 4
git checkout 9da65fd  # Before Phase 3
git checkout ba0e38e  # Before Phase 2
git checkout 2d36f11  # Before Phase 1
```

### 10.2 Full Rollback (Code + Lambda)

```bash
# 1. Checkout stable code
git checkout v1.0-stable

# 2. Build and publish layer v41 (if needed)
cd D:\CA\repo
# ... build layer ...

# 3. Update Lambda functions to use v41
aws lambda update-function-configuration \
  --function-name lcmgo-cagenai-prod-query \
  --layers arn:aws:lambda:eu-north-1:132934401449:layer:lcmgo-cagenai-prod-lcmgo-package:41 \
  --region eu-north-1

# 4. Verify
aws lambda invoke --function-name lcmgo-cagenai-prod-health /dev/stdout
```

### 10.3 Emergency Rollback Script

```bash
#!/bin/bash
# emergency-rollback.sh

REGION="eu-north-1"
LAYER_VERSION="41"

FUNCTIONS=(
  "lcmgo-cagenai-prod-query"
  "lcmgo-cagenai-prod-cv-parser"
  "lcmgo-cagenai-prod-cv-processor"
  "lcmgo-cagenai-prod-upload"
  "lcmgo-cagenai-prod-status"
  "lcmgo-cagenai-prod-candidates"
)

for fn in "${FUNCTIONS[@]}"; do
  echo "Rolling back $fn to layer v$LAYER_VERSION..."
  aws lambda update-function-configuration \
    --function-name "$fn" \
    --layers "arn:aws:lambda:$REGION:132934401449:layer:lcmgo-cagenai-prod-lcmgo-package:$LAYER_VERSION" \
    --region "$REGION"
done

echo "Rollback complete!"
```

---

## 11. Verification Checklist

### 11.1 Pre-Deployment Verification

- [ ] All tests passing (104+ tests)
- [ ] Git tag created (v1.1-pre-deploy)
- [ ] Documentation complete
- [ ] Snapshot document saved
- [ ] Lambda layer v51 is current stable

### 11.2 Post-Deployment Verification

- [ ] Health endpoint responds
- [ ] Query endpoint works (without HR analysis)
- [ ] Query endpoint works (with HR analysis)
- [ ] CV upload still works
- [ ] No errors in CloudWatch logs

### 11.3 Rollback Triggers

Rollback if any of these occur:
- [ ] Query Lambda timeout increases >2x
- [ ] Query Lambda errors >5%
- [ ] HR analysis fails >50% of requests
- [ ] CV processing breaks
- [ ] Database connection issues

---

## 12. Contacts

| Role | Contact |
|------|---------|
| Project Owner | yiannis@lcmgocloud.com |
| AWS Account | 132934401449 |
| GitLab Repo | https://gitlab.com/lcm-team/lcmgocloud_ca_genai_2026 |
| GitHub Repo | https://github.com/necropolis0079/CosmosAluminium |

---

*Snapshot created: 2026-01-20*
*Author: Claude Code (Session 39)*
