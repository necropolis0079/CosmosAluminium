# Architecture Decisions - LCMGoCloud-CAGenAI

Αρχιτεκτονικές αποφάσεις για το project.

**Format**:
- **Απόφαση**: Τι αποφασίστηκε
- **Alternatives**: Τι άλλο εξετάστηκε
- **Γιατί**: Reasoning
- **Επίπτωση**: Τι επηρεάζει
- **AWS Resources**: Αν επηρεάζει AWS resources

---

## 2025-01-17 - Implementation Configuration Decisions

**Αποφάσεις** για MVP implementation:

| Area | Decision |
|------|----------|
| **Authentication** | AWS Cognito (5-20 users) |
| **Frontend Hosting** | AWS Amplify Hosting |
| **CI/CD** | AWS CodePipeline |
| **Tesseract OCR** | Lambda Layer |
| **Custom Domain** | Όχι, AWS defaults |
| **Data Migration** | Fresh start, no migration |
| **Budget Alerts** | Email notifications |
| **GDPR** | Standard (EU residency, encryption, logs) |
| **Timeline** | MVP σε 1-2 μήνες |

---

## 2026-01-17 - Bedrock Model Availability in eu-north-1

**Decision**: Use EU cross-region inference profiles for all Bedrock models instead of direct regional endpoints.

**Research Findings** (verified 2026-01-17):
- **eu-north-1 (Stockholm) direct availability**: Very limited - only Amazon Titan Embeddings V2 and Titan Text G1
- **EU Inference Profile availability**: Full Claude and Cohere model access via cross-region routing

**Available via EU Inference Profile** (`eu.*` model IDs):
| Model | Inference Profile ID |
|-------|---------------------|
| Claude 3 Haiku | `eu.anthropic.claude-3-haiku-20240307-v1:0` |
| Claude 3.5 Sonnet | `eu.anthropic.claude-3-5-sonnet-20240620-v1:0` |
| Claude 3.7 Sonnet | `eu.anthropic.claude-3-7-sonnet-20250219-v1:0` |
| Claude Haiku 4.5 | `eu.anthropic.claude-haiku-4-5-20251001-v1:0` |
| Claude Sonnet 4.5 | `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Claude Opus 4.5 | `eu.anthropic.claude-opus-4-5-20251101-v1:0` |
| Cohere Embed v4 | `eu.cohere.embed-v4:0` |

**EU Inference Profile Destination Regions**:
- eu-central-1 (Frankfurt), eu-north-1 (Stockholm), eu-south-1 (Milan)
- eu-south-2 (Spain), eu-west-1 (Ireland), eu-west-2 (London), eu-west-3 (Paris)

**Rationale**:
- ✅ **Chosen**: EU cross-region inference
  - Access to all Claude 4.5 models
  - Data stays within EU (GDPR compliant)
  - No additional charge for cross-region routing
  - Automatic load balancing across EU regions
- ❌ **Rejected**: Direct eu-north-1 endpoints
  - Claude and Cohere models not available directly
  - Would require application changes if models become available later
- ❌ **Rejected**: Single non-Stockholm EU region (e.g., eu-central-1)
  - No benefit over cross-region inference
  - Less resilient

**Impact**:
- Update all Bedrock model IDs in IAM policies to use `eu.*` inference profiles
- Code must use inference profile ARNs, not regional model ARNs
- Pricing calculated based on source region (eu-north-1)

**Sources**:
- [AWS Bedrock Model Regions](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html)
- [AWS Bedrock Inference Profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html)

---

## 2026-01-18 - Cohere Embed v4 API Format Changes (ISSUE-007)

**Decision**: Update embedding code to handle Cohere Embed v4 API format differences.

**Discovery** (ISSUE-007 Investigation):
Cohere Embed v4 has significant API changes from v3 that caused embedding failures:

| Aspect | v3 Format | v4 Format |
|--------|-----------|-----------|
| Response | `{"embeddings": [[...]]}` | `{"embeddings": {"float": [[...]]}}` |
| embedding_types | Optional | Required (`["float"]` or `["int8"]`) |
| truncate | `END`, `START`, `NONE` | `NONE`, `LEFT`, `RIGHT` |
| max batch | 96+ | 96 (strict) |

**Code Changes**:
1. **Response parsing**: Check if `embeddings` is dict, extract `["float"]` or `["int8"]` key
2. **Request body**: Add `embedding_types: ["float"]`, remove `truncate`
3. **Batch limit**: Enforce 96 items max per request

**Files Changed**:
- `src/lcmgo_cagenai/llm/provider.py` (embed, embed_query methods)
- `src/lcmgo_cagenai/parser/taxonomy_mapper.py` (batch limit)

**Documentation**: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-embed-v4.html

---

## 2026-01-18 - Proper Batch Processing + Terraform Triggers (ISSUE-008)

**Decision**: Implement proper batching for Cohere API and expand Terraform triggers.

**Discovery** (ISSUE-008 Investigation):
Two related issues discovered during code review:

### Part A: Data Accuracy Bug
**Problem**: Code used `candidates[:96]` which TRUNCATED data instead of batching.
- skill_taxonomy has 124 entries
- Only first 96 were processed (77%)
- 28 entries (23%) were NEVER compared semantically

**Fix**: Proper batching loop:
```python
for i in range(0, len(candidates), COHERE_BATCH_SIZE):
    batch = candidates[i:i + COHERE_BATCH_SIZE]
    batch_response = await self.provider.embed(batch)
    all_candidate_embeddings.extend(batch_response.embeddings)
```

### Part B: Terraform Trigger Detection
**Problem**: Only 5 `__init__.py` files were tracked in null_resource triggers.
- Changes to most source files didn't trigger layer rebuild
- Manual `terraform taint` was required

**Fix**: Expanded to 23 file triggers covering all modules:
- OCR: 5 files
- LLM: 2 files
- Search: 3 files
- Parser: 6 files
- Query: 5 files

**Files Changed**:
- `src/lcmgo_cagenai/parser/taxonomy_mapper.py` (batching)
- `infra/terraform/lambda_cv_processor.tf` (23 triggers)

**Verification**: 124 skill entries now processed in 2 batches (96 + 28).

---

## 2026-01-17 - Cohere Embed v4 (Update from v3)

**Decision**: Use Cohere Embed v4 instead of v3 for vector embeddings.

**Rationale**:
- ✅ **Chosen**: Cohere Embed v4
  - Available via EU inference profile (`eu.cohere.embed-v4:0`)
  - Multimodal support (text + images)
  - 100+ languages including Greek
  - Improved performance over v3
- ❌ **Rejected**: Cohere Embed v3
  - Not available in EU inference profile
  - Would require direct regional endpoint (not available in eu-north-1)

**Impact**:
- Update model ID: `cohere.embed-multilingual-v3` → `eu.cohere.embed-v4:0`
- Code changes minimal (same embedding dimensions)
- Multimodal capability available for future CV image analysis
- **UPDATE (2026-01-18)**: See above for API format changes required

---

## 2026-01-17 - Cognito Authentication with Role-Based Access

**Decision**: Use AWS Cognito User Pool with 3 user groups for authentication and authorization.

**User Groups**:
| Group | Description | Permissions |
|-------|-------------|-------------|
| **SuperAdmin** | System administrators | Full access, user management, system config |
| **Admins** | HR managers | CV management, query access, reports, prompt management |
| **HRUsers** | HR staff | CV upload, basic queries, view results |

**Rationale**:
- ✅ **Chosen**: Cognito with groups
  - Native AWS integration
  - No separate auth server needed
  - JWT tokens with group claims
  - MFA support built-in
  - Cost-effective for 5-20 users (free tier)
- ❌ **Rejected**: Custom auth with RDS
  - More development effort
  - Security burden
  - No MFA out of box
- ❌ **Rejected**: Third-party (Auth0, Okta)
  - Additional cost
  - External dependency
  - Overkill for user count

**Features**:
- Email/password authentication
- Optional MFA (TOTP)
- Password policy: 12+ chars, mixed case, numbers, symbols
- Account lockout after 5 failed attempts
- JWT token expiry: 1 hour access, 30 days refresh

**Impact**:
- New Terraform: `cognito.tf` with User Pool, App Client, Groups
- Lambda authorizer uses Cognito JWT validation
- Frontend uses AWS Amplify Auth library
- API Gateway validates group membership for protected endpoints

---

## 2025-01-17 - AWS Naming Convention & Region

**Απόφαση**: Use standardized naming convention `lcmgo-cagenai-prod-{service}-{component}-eun1` for all AWS resources.

**Alternatives**:
- ❌ Short names (ca-genai-*) - Less descriptive
- ❌ Long names with company (cosmosaluminium-*) - Too long for AWS limits

**Γιατί**:
- Consistent identification across services
- Region-aware (eun1 = eu-north-1)
- Environment-aware (prod)
- Easy to filter/search

**Επίπτωση**: All AWS resources must follow this convention.

**AWS Resources**:
- Region: eu-north-1 (Stockholm)
- VPC CIDR: 10.10.0.0/20
- Resource Group: rg-lcmgo-cagenai-prod

---

## 2025-01-17 - Text-to-SQL over RAG for Structured Queries

**Decision**: Use Text-to-SQL approach instead of pure RAG for structured HR queries.

**Rationale**:
- ✅ **Chosen**: Text-to-SQL with Claude Haiku
  - Deterministic results (same query = same results)
  - 54% cost savings (~€0.0043/query vs €0.0093/query)
  - Faster execution (~2s vs ~3s)
  - Explainable results (can show SQL and explain matches)
- ❌ **Rejected**: Pure RAG
  - Non-deterministic results
  - Higher cost per query
  - False positives in semantic matching
- ❌ **Rejected**: Hybrid only
  - Added complexity without significant benefit for structured queries

**Impact**:
- Requires PostgreSQL schema optimized for SQL generation
- Need taxonomy mapping for canonical IDs (SKILL_*, ROLE_*, etc.)
- Claude Haiku for query translation, Sonnet for evaluation

---

### 2025-01-17: PostgreSQL + OpenSearch Hybrid Architecture

**Decision**: Use both PostgreSQL (structured data) and OpenSearch (vector search) rather than single database.

**Rationale**:
- ✅ **Chosen**: Dual database
  - PostgreSQL for structured queries, ACID compliance, complex joins
  - OpenSearch for semantic search, k-NN vectors, full-text with Greek analyzer
  - Best tool for each job
- ❌ **Rejected**: PostgreSQL only with pgvector
  - Less mature vector search capabilities
  - No native Greek text analyzer
- ❌ **Rejected**: OpenSearch only
  - Poor for complex relational queries
  - No ACID guarantees

**Impact**:
- Dual-write required during CV processing
- Result merging with RRF (Reciprocal Rank Fusion)
- Higher infrastructure cost but better performance

---

### 2025-01-17: Documentation Repository Separate from Code

**Decision**: Maintain documentation in separate repository (D:\CA) from implementation code (GitLab).

**Rationale**:
- ✅ **Chosen**: Separate repos
  - Documentation can evolve independently
  - Easier access for non-developers
  - Contains sensitive sample data (CVs)
- ❌ **Rejected**: Docs in code repo
  - Mixing concerns
  - Larger repo size with CV samples

**Impact**:
- Need to keep docs in sync with implementation
- Cross-reference to GitLab for actual code

---

### 2025-01-17: Cohere Embed v3 for Vector Embeddings

**Decision**: Use Cohere Embed v3 (via Bedrock) for all vector embeddings instead of Amazon Titan.

**Rationale**:
- ✅ **Chosen**: Cohere Embed v3
  - Explicit multilingual support including Greek
  - Better semantic matching for Greek terms (συγκολλητής ↔ welder)
  - Same dimensions (1024) - no schema changes needed
  - Superior cross-lingual retrieval
- ❌ **Rejected**: Amazon Titan Embeddings v2
  - English-optimized, weaker Greek support
  - Cheaper ($0.02 vs $0.10 per 1M tokens) but quality matters more
- ❌ **Rejected**: Titan Multimodal
  - Overkill for text-only embeddings
  - Still English-optimized

**Impact**:
- Update OpenSearch index to use Cohere embeddings
- Embedding cost increases 5x but volume is low (once per CV)
- Better search quality for Greek CVs

---

### 2025-01-17: Triple OCR with Parallel Execution

**Decision**: Run Claude Vision, Tesseract, and AWS Textract in parallel for all CV documents, with scoring and validation.

**Rationale**:
- ✅ **Chosen**: Triple OCR with voting
  - Redundancy improves accuracy
  - Different engines excel at different document types
  - Voting system (2/3 agreement) increases confidence
  - Claude arbitration for conflicts
- ❌ **Rejected**: Single OCR (Tesseract only)
  - Greek OCR quality inconsistent
  - No fallback on failure
- ❌ **Rejected**: Sequential fallback
  - Slower processing
  - No cross-validation

**Impact**:
- Higher processing cost per CV (3x OCR calls)
- Better accuracy especially for scanned/image CVs
- Need OCR Fusion Engine component
- Confidence scoring: 3/3 agreement = 0.95+, 2/3 = 0.80, 0/3 = manual review

---

### 2025-01-17: DynamoDB for CV Processing State Machine

**Decision**: Use DynamoDB to track CV processing state with full audit trail and retry logic.

**Rationale**:
- ✅ **Chosen**: DynamoDB state tracking
  - Serverless, scales automatically
  - Fast point lookups by cv_id
  - TTL for automatic cleanup
  - Supports correlation IDs for tracing
- ❌ **Rejected**: PostgreSQL for state
  - Mixing operational and business data
  - Connection pool pressure
- ❌ **Rejected**: SQS only (stateless)
  - No visibility into processing state
  - Hard to debug failures

**Impact**:
- New DynamoDB table: cv_processing_state
- States: UPLOADED → OCR_PROCESSING → OCR_COMPLETE → PARSING → POSTGRES_WRITING → POSTGRES_DONE → VECTOR_WRITING → VECTOR_DONE → COMPLETED | FAILED
- Retry logic: 3x with exponential backoff per stage
- Validation report stored per CV

---

### 2025-01-17: PostgreSQL as Primary Database with Retry Strategy

**Decision**: PostgreSQL is the authoritative data store. Vector DB (OpenSearch) is secondary and can be rebuilt.

**Rationale**:
- ✅ **Chosen**: PostgreSQL primary, OpenSearch secondary
  - ACID guarantees for candidate data
  - OpenSearch can be reindexed from PostgreSQL
  - Partial success allowed (SQL works even if vector fails)
- ❌ **Rejected**: Dual-primary
  - Complexity of distributed transactions
  - No clear source of truth

**Impact**:
- If PostgreSQL write fails: retry entire CV processing
- If OpenSearch write fails: mark as POSTGRES_DONE, queue for vector retry
- CV is searchable via SQL immediately, semantic search follows
- Nightly job to sync any PostgreSQL records missing from OpenSearch

---

### 2025-01-17: Claude 4.5 Models for All AI Tasks

**Decision**: Use Claude 4.5 (Sonnet and Opus) via Bedrock for all LLM tasks.

**Rationale**:
- ✅ **Chosen**: Claude 4.5 exclusively
  - Latest model with best performance
  - Consistent behavior across tasks
  - Greek language understanding improved
  - Claude 4.5 Sonnet for: query translation, CV parsing, evaluations
  - Claude 4.5 Opus for: complex analysis, OCR arbitration
- ❌ **Rejected**: Claude 3.5 Haiku
  - Older model, less capable
  - Cost savings not worth quality loss for this use case
- ❌ **Rejected**: Mixed models (GPT + Claude)
  - Inconsistent outputs
  - Multiple vendor dependencies

**Impact**:
- Update all Bedrock model IDs to Claude 4.5 versions
- Higher cost per token but better accuracy
- Simplified prompt management (one model family)

---

### 2025-01-17: Abstract LLM Layer with Provider Swapping

**Decision**: Implement abstraction layer for LLM calls to enable provider switching and fallbacks.

**Rationale**:
- ✅ **Chosen**: Abstract LLMProvider interface
  - Easy swap between Bedrock/OpenAI/local models
  - Automatic fallback on provider failure
  - Centralized retry and caching logic
  - Prompt versioning support
- ❌ **Rejected**: Direct Bedrock SDK calls
  - Vendor lock-in
  - No fallback capability
  - Scattered LLM logic

**Impact**:
- New module: llm_provider.py with BedrockProvider, OpenAIProvider
- All LLM calls go through abstraction
- Enables A/B testing of models
- Caching layer for repeated queries

---

### 2025-01-17: Prompt Versioning with Regression Tests

**Decision**: Version all prompts with metadata and maintain regression test suites.

**Rationale**:
- ✅ **Chosen**: Versioned prompts with tests
  - Track prompt changes over time
  - Measure accuracy per version
  - Prevent regressions on updates
  - Rollback capability
- ❌ **Rejected**: Prompts in code
  - Hard to track changes
  - No performance metrics
  - Risky updates

**Impact**:
- Prompts stored in prompts/ directory with version numbers
- metadata.json tracks version history and accuracy metrics
- Regression tests run before deploying new prompt versions
- CI/CD gate on prompt accuracy threshold

---

### 2025-01-17: Query Router with Confidence Threshold

**Decision**: Query router must ask for clarification when confidence < 0.7.

**Rationale**:
- ✅ **Chosen**: Confidence-based routing with clarification
  - Prevents wrong query interpretation
  - Better UX than wrong results
  - User can guide the system
  - Threshold 0.7 balances accuracy vs friction
- ❌ **Rejected**: Always route without asking
  - Risk of completely wrong results
  - User frustration
- ❌ **Rejected**: Higher threshold (0.9)
  - Too many clarification requests
  - Annoying UX

**Impact**:
- QueryRouter returns CLARIFY action when confidence < 0.7
- UI must handle ClarificationModal component
- Fallback to RAG for semantic queries when structured fails

---

### 2025-01-17: Correlation IDs Across Pipeline

**Decision**: Generate correlation ID at CV upload, propagate through all processing stages.

**Rationale**:
- ✅ **Chosen**: Correlation ID pattern
  - End-to-end tracing of CV processing
  - Easy debugging across Lambda invocations
  - CloudWatch Logs Insights queries by correlation_id
  - Audit trail for compliance
- ❌ **Rejected**: Request ID only
  - Lost across async boundaries
  - No cross-service correlation

**Impact**:
- correlation_id generated at API Gateway
- Passed through SQS message attributes
- Stored in DynamoDB state record
- Included in all CloudWatch logs
- Searchable in UI for debugging

---

### 2025-01-17: React UI for CV Processing Management

**Decision**: Build React frontend for managing CV uploads, monitoring processing, and validation review.

**Rationale**:
- ✅ **Chosen**: React SPA
  - Modern, maintainable frontend
  - Real-time updates via WebSocket
  - Component reuse across features
  - Team familiarity
- ❌ **Rejected**: Server-rendered pages
  - Poor interactivity
  - More backend complexity
- ❌ **Rejected**: Vue/Angular
  - Team preference for React

**Impact**:
- Components needed: CVUpload, ProcessingStatus, ValidationReport, Dashboard, PromptManager, BudgetAlerts
- WebSocket connection for real-time state updates
- Integration with DynamoDB state and CloudWatch metrics

---

### 2025-01-17: Greek Text Normalization Strategy

**Decision**: Aggressive normalization with unaccent + lowercase for all Greek text matching.

**Rationale**:
- ✅ **Chosen**: Aggressive normalization
  - Handles accent variations (τόνοι, διαλυτικά)
  - Case-insensitive matching
  - Greeklish detection and conversion
  - Training data from 200 sample CVs
- ❌ **Rejected**: Preserve original text
  - Matching failures on accent differences
  - "Γιώργος" ≠ "ΓΙΩΡΓΟΣ" without normalization

**Impact**:
- PostgreSQL: unaccent extension + lower() on all Greek text columns
- OpenSearch: Greek analyzer with lowercase filter
- Normalization applied at ingestion AND query time
- Build edge case dictionary from sample CVs

---

### 2025-01-17: AWS Budget Alerts

**Decision**: Implement multi-tier budget alerts for AWS spending, especially Bedrock/AI costs.

**Rationale**:
- ✅ **Chosen**: Proactive budget monitoring
  - Prevent bill shock from AI costs
  - Early warning at 50%, 80%, 100% thresholds
  - Separate alerts for Bedrock vs other services
  - Automatic notifications to Slack/email
- ❌ **Rejected**: Monthly review only
  - Too late to react
  - Potential for large overruns

**Impact**:
- AWS Budgets configured with SNS alerts
- BudgetAlerts component in React UI
- Daily cost tracking in CloudWatch dashboard
- Automatic throttling option at 100% budget

---

## 2026-01-17 - Data Validation & Integrity Architecture

### Unmatched Taxonomy Capture Strategy

**Decision**: Capture all CV items that cannot be mapped to existing taxonomy instead of silently discarding them.

**Rationale**:
- ✅ **Chosen**: Unmatched items table with review workflow
  - No data loss during CV processing
  - Enables taxonomy expansion based on real data
  - Manual review queue for HR admins
  - Suggested mappings with semantic similarity scores
- ❌ **Rejected**: Silent discard (current behavior)
  - Data loss - skills/software/certs permanently lost
  - No visibility into taxonomy gaps
  - Users unaware of incomplete profiles
- ❌ **Rejected**: Automatic taxonomy expansion
  - Risk of polluting taxonomy with noise
  - No human validation of new entries
  - Quality control issues

**Impact**:
- New table: `unmatched_taxonomy_items`
- Modified: `db_writer.py` to capture unmatched items
- Modified: `taxonomy_mapper.py` to return suggested matches
- New admin view for reviewing unmatched items
- Taxonomy coverage metrics dashboard

---

### Post-Write Verification Strategy

**Decision**: Verify all database writes after CV processing with count validation.

**Rationale**:
- ✅ **Chosen**: Post-write verification with counts
  - Catches silent write failures
  - Provides completeness metrics
  - Non-blocking (soft failure)
  - Stored in DynamoDB for tracking
- ❌ **Rejected**: Assume success after commit
  - Silent data loss possible
  - No way to detect partial writes
  - No audit trail
- ❌ **Rejected**: Transaction rollback on any mismatch
  - Too strict for partial data
  - Unmatched skills would fail entire CV
  - User gets nothing instead of partial data

**Impact**:
- New: `WriteVerification` dataclass
- Modified: `write_candidate()` returns verification result
- DynamoDB stores verification results per correlation_id
- CloudWatch metrics for verification success rate

---

### Dynamic Query Aliases Strategy

**Decision**: Load query aliases from database taxonomy tables instead of static dictionary.

**Rationale**:
- ✅ **Chosen**: Database-loaded aliases with caching
  - Aliases automatically reflect taxonomy updates
  - No code deployment needed for new terms
  - Cache with 5-minute TTL for performance
  - Fallback to static dict on DB failure
- ❌ **Rejected**: Static GREEK_ALIASES dict (current)
  - Requires code changes for new aliases
  - Out of sync with taxonomy tables
  - ~350 hardcoded entries insufficient
- ❌ **Rejected**: Real-time DB lookup per query
  - Too slow for query translation
  - Database connection overhead
  - No caching

**Impact**:
- New module: `dynamic_aliases.py`
- Modified: `query_translator.py` to use dynamic loader
- New Lambda environment variable: `DB_SECRET_ARN`
- Cache refresh every 5 minutes

---

### Job Posting Matching Strategy

**Decision**: Enable job postings to be parsed into candidate search filters.

**Rationale**:
- ✅ **Chosen**: Claude-based job posting parser
  - Same LLM infrastructure as CV parsing
  - Consistent taxonomy mapping
  - Natural language requirement extraction
  - Bidirectional matching (candidate→jobs, job→candidates)
- ❌ **Rejected**: Manual requirement entry only
  - Time-consuming for HR staff
  - Error-prone manual mapping
  - Inconsistent filter generation
- ❌ **Rejected**: Keyword extraction only
  - Misses semantic requirements
  - Cannot handle Greek variations
  - No structure validation

**Impact**:
- New module: `job_parser.py`
- New endpoint: `POST /jobs/parse`
- New dataclasses: `JobRequirements`, `LanguageRequirement`
- Integration with existing query infrastructure

---

### Query Result Validation Strategy

**Decision**: Validate query results before returning to users.

**Rationale**:
- ✅ **Chosen**: Multi-layer validation
  - SQL sanity checks (valid query, no cartesian products)
  - Result count validation (0 results → suggest alternatives)
  - Relevance scoring (at least 1 filter match per result)
  - User feedback loop for continuous improvement
- ❌ **Rejected**: Return raw SQL results
  - No quality control
  - Bad queries return wrong data silently
  - No learning from user feedback
- ❌ **Rejected**: Manual result review
  - Doesn't scale
  - Delays results to users
  - Not practical for real-time queries

**Impact**:
- Modified: `query/handler.py` with validation layer
- New: `QueryResultValidation` dataclass
- CloudWatch metrics for result quality
- User feedback stored in `query_feedback` table

---

### EU Inference Profile Cross-Region Routing (Session 24)

**Decision**: Use region wildcards (`*`) in IAM policies for EU inference profiles because they route requests to any EU region, not just the source region.

**Rationale**:
- ✅ **Chosen**: Region wildcards in IAM policies
  - EU inference profiles (e.g., `eu.anthropic.claude-*`) route to eu-west-3, eu-central-1, etc.
  - Cannot predict which destination region will handle the request
  - Using `*` allows cross-region routing without IAM failures
  - Example: `arn:aws:bedrock:*::foundation-model/anthropic.claude-*`
- ❌ **Rejected**: Hardcoded source region (eu-north-1)
  - Causes AccessDeniedException when AWS routes to different EU region
  - Discovered during ISSUE-005 testing

**Impact**:
- Updated `lambda_cv_parser.tf` and `lambda_cv_processor.tf`
- Both inference-profile and foundation-model ARNs need wildcards
- Same pattern needed for all EU cross-region inference profiles

**Lesson Learned**:
- EU inference profiles are not region-bound to source region
- AWS automatically load-balances to available EU regions
- IAM policies must account for this routing behavior

---

### pg8000 PostgreSQL Driver Transaction Handling (Session 24)

**Decision**: Use pg8000's implicit transaction model without explicit `begin()` calls.

**Rationale**:
- ✅ **Chosen**: Implicit transactions (autocommit=False)
  - pg8000 uses autocommit=False by default
  - Transactions are implicit - no `begin()` needed
  - `commit()` finalizes, `rollback()` reverts
  - Simple and clean API
- ❌ **Rejected**: Explicit begin() (psycopg2 style)
  - pg8000 doesn't have `Connection.begin()` method
  - Causes AttributeError at runtime
  - Discovered during ISSUE-006 testing

**Impact**:
- Fixed `db_writer.py` to remove `conn.begin()` call
- Pattern: `conn = connect(...) → execute → conn.commit()`
- Error handling: use `conn.rollback()` on exception

**Lesson Learned**:
- pg8000 API differs from psycopg2 despite both being PostgreSQL drivers
- Always check driver-specific documentation for transaction handling
- Pure Python drivers may have different API conventions

---

### CV Data Cleanup Strategy (Session 22)

**Decision**: Create comprehensive cleanup utility supporting all CV data storage locations with orphan detection.

**Rationale**:
- ✅ **Chosen**: Multi-storage cleanup script with CLI
  - Covers all 5 storage locations (S3 uploads, S3 processed, DynamoDB, PostgreSQL, OpenSearch)
  - Dry-run mode prevents accidental deletion
  - Orphan detection finds inconsistent data
  - CLI interface for easy scripting
  - JSON output for automation
- ❌ **Rejected**: Manual AWS Console cleanup
  - Time-consuming across 5 services
  - Error-prone without correlation tracking
  - No orphan detection capability
  - Not repeatable
- ❌ **Rejected**: AWS Athena + Step Functions
  - Over-engineered for cleanup use case
  - Additional infrastructure costs
  - Slower iteration during development

**Impact**:
- New script: `scripts/cleanup/cleanup_cv_data.py`
- Documentation: `docs/CLEANUP-PROCESS.md`
- Pre-testing: Run `--find-orphans` to establish baseline
- Post-testing: Run `--all --confirm` for full cleanup
- Ongoing: Can clean individual CVs by correlation_id or candidate_id

**Key IDs**:
| ID | Generated By | Links |
|----|--------------|-------|
| `correlation_id` | cv_processor Lambda | S3 ↔ DynamoDB ↔ S3 parsed |
| `candidate_id` | PostgreSQL INSERT | PostgreSQL ↔ OpenSearch |

---

## 2026-01-20 - Partial/Fuzzy Matching for Software Search (Session 37)

**Decision**: Use partial ILIKE matching instead of exact array overlap for software and taxonomy searches.

**Problem Discovered**:
User reported "Candidates with Excel experience" returning 0 results despite 15+ candidates having Microsoft Excel in their profile.

**Root Cause Analysis**:
1. Software taxonomy stores full names: "Microsoft Excel", "SAP ERP"
2. User queries use partial terms: "Excel", "SAP"
3. SQL function used exact array overlap: `["Excel"] && ["Microsoft Excel"]` = FALSE
4. SQL generator searched only `name` column, but canonical_id was being passed

**Rationale**:
- ✅ **Chosen**: Partial ILIKE matching with bidirectional check
  - Matches "Excel" → "Microsoft Excel" (search term in full name)
  - Matches "Microsoft Excel" → "Excel" (full name contains search)
  - Case-insensitive with LOWER()
  - Works with both short terms and full names
  - Minimal performance impact (EXISTS with early termination)
- ❌ **Rejected**: Trigram similarity (pg_trgm)
  - Already available but overkill for exact substring matching
  - Higher computational cost for simple partial matches
- ❌ **Rejected**: Expand aliases in query preprocessing
  - Would require maintaining alias mappings in application code
  - Adds complexity and potential for stale mappings
- ❌ **Rejected**: Full-text search (tsvector)
  - Heavyweight for simple substring matching
  - Would require schema changes

**Implementation**:
```sql
-- SQL Function (match_candidates_relaxed)
WHEN EXISTS (
    SELECT 1 FROM unnest(v.software) sw, unnest(p_software) ps
    WHERE LOWER(sw) LIKE '%' || LOWER(ps) || '%'
       OR LOWER(ps) LIKE '%' || LOWER(sw) || '%'
) THEN 0.20
```

```python
# SQL Generator (sql_generator.py)
name_condition_template = f"({taxonomy_alias}.name ILIKE {{placeholder}} OR {taxonomy_alias}.canonical_id ILIKE {{placeholder}})"
```

**Impact**:
- Query searches now return expected results for partial software terms
- Both SQL function (job matching) and SQL generator (structured queries) fixed
- No schema changes required
- Deployed via Lambda layer v51

**Files Changed**:
- `scripts/sql/019_job_matching.sql`
- `src/lcmgo_cagenai/query/sql_generator.py`

---

## Pending Decisions

*None currently*

---

## Decision Template

```markdown
### YYYY-MM-DD: [Title]

**Decision**: [What was decided]

**Rationale**:
- ✅ **Chosen**: [Option]
  - [Reason 1]
  - [Reason 2]
- ❌ **Rejected**: [Alternative 1]
  - [Why rejected]
- ❌ **Rejected**: [Alternative 2]
  - [Why rejected]

**Impact**: [How this affects the project]
```
