"""
OpenSearch index mappings for k-NN vector search and Greek text search.

Indices:
- cosmos-hr-candidates: CV embeddings and candidate data
- cosmos-hr-jobs: Job postings with requirements

Based on docs/04-VECTORDB-OPENSEARCH.md specification.
"""

# Index names (without version suffix for aliasing)
CANDIDATES_INDEX = "cosmos-hr-candidates"
JOBS_INDEX = "cosmos-hr-jobs"

# Version suffix for zero-downtime reindexing
INDEX_VERSION = "v1"

# Full index names with version
CANDIDATES_INDEX_VERSIONED = f"{CANDIDATES_INDEX}-{INDEX_VERSION}"
JOBS_INDEX_VERSIONED = f"{JOBS_INDEX}-{INDEX_VERSION}"

# Index settings with Greek analyzers and k-NN configuration
INDEX_SETTINGS = {
    "settings": {
        "index": {
            "number_of_shards": 3,
            "number_of_replicas": 1,
            "refresh_interval": "30s",
            "max_result_window": 10000,
            "knn": True,
            "knn.algo_param.ef_search": 512,
        },
        "analysis": {
            "char_filter": {
                "greek_char_filter": {
                    "type": "mapping",
                    "mappings": [
                        # Lowercase accented vowels
                        "\u03ac => \u03b1",  # ά => α
                        "\u03ad => \u03b5",  # έ => ε
                        "\u03ae => \u03b7",  # ή => η
                        "\u03af => \u03b9",  # ί => ι
                        "\u03cc => \u03bf",  # ό => ο
                        "\u03cd => \u03c5",  # ύ => υ
                        "\u03ce => \u03c9",  # ώ => ω
                        # Uppercase accented vowels
                        "\u0386 => \u0391",  # Ά => Α
                        "\u0388 => \u0395",  # Έ => Ε
                        "\u0389 => \u0397",  # Ή => Η
                        "\u038a => \u0399",  # Ί => Ι
                        "\u038c => \u039f",  # Ό => Ο
                        "\u038e => \u03a5",  # Ύ => Υ
                        "\u038f => \u03a9",  # Ώ => Ω
                        # Dialytika
                        "\u03ca => \u03b9",  # ϊ => ι
                        "\u03cb => \u03c5",  # ϋ => υ
                        "\u0390 => \u03b9",  # ΐ => ι
                        "\u03b0 => \u03c5",  # ΰ => υ
                    ],
                }
            },
            "filter": {
                "greek_lowercase": {"type": "lowercase", "language": "greek"},
                "greek_stop": {"type": "stop", "stopwords": "_greek_"},
                "greek_stemmer": {"type": "stemmer", "language": "greek"},
                "english_stop": {"type": "stop", "stopwords": "_english_"},
                "english_stemmer": {"type": "stemmer", "language": "english"},
                "word_delimiter_filter": {
                    "type": "word_delimiter_graph",
                    "generate_word_parts": True,
                    "generate_number_parts": True,
                    "split_on_case_change": True,
                    "split_on_numerics": True,
                    "preserve_original": True,
                },
            },
            "analyzer": {
                "greek_analyzer": {
                    "type": "custom",
                    "char_filter": ["greek_char_filter"],
                    "tokenizer": "standard",
                    "filter": ["greek_lowercase", "greek_stop", "greek_stemmer"],
                },
                "greek_search_analyzer": {
                    "type": "custom",
                    "char_filter": ["greek_char_filter"],
                    "tokenizer": "standard",
                    "filter": ["greek_lowercase"],
                },
                "multilingual_analyzer": {
                    "type": "custom",
                    "char_filter": ["greek_char_filter"],
                    "tokenizer": "standard",
                    "filter": ["lowercase", "word_delimiter_filter"],
                },
            },
            "normalizer": {
                "lowercase_normalizer": {
                    "type": "custom",
                    "char_filter": ["greek_char_filter"],
                    "filter": ["lowercase", "trim"],
                }
            },
        },
    }
}

# Candidates index mapping
CANDIDATES_MAPPING = {
    "mappings": {
        "properties": {
            "candidate_id": {"type": "keyword"},
            "external_id": {"type": "keyword"},
            "full_name": {
                "type": "text",
                "analyzer": "greek_analyzer",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "normalizer": "lowercase_normalizer",
                    },
                    "standard": {"type": "text", "analyzer": "standard"},
                },
            },
            "email": {"type": "keyword"},
            "phone": {"type": "keyword"},
            "location": {
                "properties": {
                    "city": {
                        "type": "text",
                        "analyzer": "greek_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "region": {"type": "keyword"},
                    "country": {"type": "keyword"},
                    "coordinates": {"type": "geo_point"},
                }
            },
            "employment_status": {"type": "keyword"},
            "availability_status": {"type": "keyword"},
            # Full CV text for BM25 search
            "cv_text": {
                "type": "text",
                "analyzer": "greek_analyzer",
                "term_vector": "with_positions_offsets",
                "store": True,
            },
            # Main CV embedding (1024-dim Cohere Embed v4)
            "cv_embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {"ef_construction": 512, "m": 16},
                },
            },
            # Skills (nested with embeddings)
            "skills": {
                "type": "nested",
                "properties": {
                    "skill_id": {"type": "keyword"},
                    "canonical_id": {"type": "keyword"},
                    "name_en": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "name_el": {
                        "type": "text",
                        "analyzer": "greek_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "category": {"type": "keyword"},
                    "level": {"type": "keyword"},
                    "years_experience": {"type": "float"},
                    "skill_embedding": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                        },
                    },
                },
            },
            # Experience (nested with embeddings)
            "experience": {
                "type": "nested",
                "properties": {
                    "company_name": {
                        "type": "text",
                        "analyzer": "greek_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "job_title": {
                        "type": "text",
                        "analyzer": "greek_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "role_id": {"type": "keyword"},
                    "start_date": {"type": "date"},
                    "end_date": {"type": "date"},
                    "is_current": {"type": "boolean"},
                    "duration_months": {"type": "integer"},
                    "description": {"type": "text", "analyzer": "greek_analyzer"},
                    "description_embedding": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                        },
                    },
                },
            },
            # Education (nested)
            "education": {
                "type": "nested",
                "properties": {
                    "institution_name": {
                        "type": "text",
                        "analyzer": "greek_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "degree_level": {"type": "keyword"},
                    "degree_title": {"type": "text", "analyzer": "greek_analyzer"},
                    "field_of_study": {"type": "keyword"},
                    "graduation_year": {"type": "integer"},
                },
            },
            # Certifications (nested)
            "certifications": {
                "type": "nested",
                "properties": {
                    "certification_id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "issuer": {"type": "keyword"},
                    "issue_date": {"type": "date"},
                    "expiry_date": {"type": "date"},
                    "is_current": {"type": "boolean"},
                },
            },
            # Training/Seminars (nested)
            "training": {
                "type": "nested",
                "properties": {
                    "name": {
                        "type": "text",
                        "analyzer": "greek_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "provider": {
                        "type": "text",
                        "analyzer": "greek_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "type": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "duration_hours": {"type": "integer"},
                },
            },
            # Training names for simple keyword search
            "training_names": {"type": "keyword"},
            # Languages (nested)
            "languages": {
                "type": "nested",
                "properties": {
                    "language_code": {"type": "keyword"},
                    "language_name": {"type": "keyword"},
                    "proficiency_level": {"type": "keyword"},
                    "is_native": {"type": "boolean"},
                },
            },
            # Metadata
            "salary_expectation": {
                "properties": {
                    "min": {"type": "float"},
                    "max": {"type": "float"},
                    "currency": {"type": "keyword"},
                }
            },
            "willing_to_relocate": {"type": "boolean"},
            "quality_score": {"type": "float"},
            "total_experience_months": {"type": "integer"},
            "tags": {"type": "keyword"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "indexed_at": {"type": "date"},
        }
    }
}

# Jobs index mapping
JOBS_MAPPING = {
    "mappings": {
        "properties": {
            "job_id": {"type": "keyword"},
            "title": {
                "type": "text",
                "analyzer": "greek_analyzer",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "description": {"type": "text", "analyzer": "greek_analyzer"},
            # Job description embedding for semantic matching
            "description_embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {"ef_construction": 512, "m": 16},
                },
            },
            # Requirements embedding for matching against CV skills
            "requirements_embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {"ef_construction": 512, "m": 16},
                },
            },
            "department": {"type": "keyword"},
            "location": {
                "properties": {
                    "city": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "country": {"type": "keyword"},
                }
            },
            "status": {"type": "keyword"},
            "employment_type": {"type": "keyword"},
            "experience_level": {"type": "keyword"},
            "experience_years_min": {"type": "integer"},
            "experience_years_max": {"type": "integer"},
            # Required skills (nested)
            "required_skills": {
                "type": "nested",
                "properties": {
                    "skill_id": {"type": "keyword"},
                    "canonical_id": {"type": "keyword"},
                    "name_en": {"type": "text"},
                    "name_el": {"type": "text", "analyzer": "greek_analyzer"},
                    "minimum_level": {"type": "keyword"},
                    "is_required": {"type": "boolean"},
                    "weight": {"type": "float"},
                },
            },
            "required_certifications": {"type": "keyword"},
            # Required languages (nested)
            "required_languages": {
                "type": "nested",
                "properties": {
                    "language_code": {"type": "keyword"},
                    "minimum_level": {"type": "keyword"},
                    "is_required": {"type": "boolean"},
                },
            },
            "salary_range": {
                "properties": {
                    "min": {"type": "float"},
                    "max": {"type": "float"},
                    "currency": {"type": "keyword"},
                }
            },
            "posted_at": {"type": "date"},
            "closes_at": {"type": "date"},
        }
    }
}


def get_full_mapping(base_mapping: dict) -> dict:
    """
    Combine index settings with mappings for index creation.

    Args:
        base_mapping: The mapping dict (CANDIDATES_MAPPING or JOBS_MAPPING)

    Returns:
        Complete index configuration with settings and mappings
    """
    return {**INDEX_SETTINGS, **base_mapping}
