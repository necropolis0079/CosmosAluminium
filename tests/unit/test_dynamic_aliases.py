"""
Unit tests for Dynamic Taxonomy Alias Loader.

Tests the DynamicAliasLoader class that loads aliases from
PostgreSQL taxonomy tables.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Configure encoding for Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from lcmgo_cagenai.query.dynamic_aliases import (
    AliasCache,
    AliasEntry,
    DynamicAliasLoader,
    normalize_text,
    load_aliases_sync,
    get_global_loader,
)


# =============================================================================
# TEST DATA
# =============================================================================

MOCK_SKILLS = [
    ("ACCOUNTING", "Accounting", "Λογιστική", ["bookkeeping"], ["λογιστεία"], "Finance"),
    ("DATA_ANALYSIS", "Data Analysis", "Ανάλυση Δεδομένων", ["analytics"], ["αναλυτική"], "IT"),
]

MOCK_ROLES = [
    ("ACCOUNTANT", "Accountant", "Λογιστής", ["bookkeeper"], ["λογιστρια"], "Accounting"),
    ("DEVELOPER", "Software Developer", "Προγραμματιστής", ["programmer", "coder"], ["developer"], "IT"),
]

MOCK_SOFTWARE = [
    ("SAP_ERP", "SAP ERP", ["SAP", "SAP R/3"], "SAP", "ERP"),
    ("EXCEL", "Microsoft Excel", ["Excel", "MS Excel"], "Microsoft", "Office"),
]

MOCK_CERTIFICATIONS = [
    ("CPA", "Certified Public Accountant", "Ορκωτός Λογιστής", ["CPA Certification"], ["CPA", "Ο.Λ."], "ACCA"),
    ("PMP", "Project Management Professional", None, [], ["PMP", "PM Professional"], "PMI"),
]


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_connection():
    """Create a mock database connection."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


@pytest.fixture
def mock_secrets_client():
    """Create a mock Secrets Manager client."""
    client = MagicMock()
    client.get_secret_value.return_value = {
        "SecretString": json.dumps({
            "host": "localhost",
            "port": 5432,
            "dbname": "test",
            "username": "test",
            "password": "test"
        })
    }
    return client


# =============================================================================
# TESTS: normalize_text
# =============================================================================

class TestNormalizeText:
    """Test the normalize_text function."""

    def test_lowercase(self):
        """Test that text is lowercased."""
        assert normalize_text("HELLO") == "hello"
        assert normalize_text("Hello World") == "hello world"

    def test_removes_greek_accents(self):
        """Test that Greek accents are removed."""
        assert normalize_text("Λογιστής") == "λογιστης"
        assert normalize_text("Αθήνα") == "αθηνα"
        assert normalize_text("Θεσσαλονίκη") == "θεσσαλονικη"

    def test_removes_latin_accents(self):
        """Test that Latin accents are removed."""
        assert normalize_text("café") == "cafe"
        assert normalize_text("naïve") == "naive"

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        assert normalize_text("  hello  ") == "hello"
        assert normalize_text("\thello\n") == "hello"

    def test_preserves_spaces_between_words(self):
        """Test that spaces between words are preserved."""
        assert normalize_text("hello world") == "hello world"

    def test_empty_string(self):
        """Test handling of empty string."""
        assert normalize_text("") == ""

    def test_none_returns_empty(self):
        """Test handling of None."""
        assert normalize_text(None) == ""


# =============================================================================
# TESTS: AliasEntry
# =============================================================================

class TestAliasEntry:
    """Test the AliasEntry dataclass."""

    def test_creation(self):
        """Test creating an AliasEntry."""
        entry = AliasEntry(
            canonical_id="ACCOUNTANT",
            source_table="role_taxonomy",
            source_language="el",
            match_type="name_el",
            primary_name="Accountant",
        )

        assert entry.canonical_id == "ACCOUNTANT"
        assert entry.source_table == "role_taxonomy"
        assert entry.source_language == "el"
        assert entry.match_type == "name_el"
        assert entry.primary_name == "Accountant"
        assert entry.confidence == 1.0  # Default
        assert entry.category is None  # Default

    def test_with_category(self):
        """Test creating AliasEntry with category."""
        entry = AliasEntry(
            canonical_id="SAP_ERP",
            source_table="software_taxonomy",
            source_language="both",
            match_type="name",
            primary_name="SAP ERP",
            category="ERP",
        )

        assert entry.category == "ERP"

    def test_with_custom_confidence(self):
        """Test creating AliasEntry with custom confidence."""
        entry = AliasEntry(
            canonical_id="CPA",
            source_table="certification_taxonomy",
            source_language="both",
            match_type="abbreviation",
            primary_name="Certified Public Accountant",
            confidence=0.98,
        )

        assert entry.confidence == 0.98


# =============================================================================
# TESTS: AliasCache
# =============================================================================

class TestAliasCache:
    """Test the AliasCache class."""

    def test_empty_cache_is_stale(self):
        """Test that empty cache is considered stale."""
        cache = AliasCache()
        assert cache.is_stale(60) is True

    def test_fresh_cache_not_stale(self):
        """Test that fresh cache is not stale."""
        cache = AliasCache(
            aliases={"test": AliasEntry("TEST", "test", "en", "name", "Test")},
            loaded_at=datetime.now(timezone.utc),
            entry_count=1,
        )
        assert cache.is_stale(60) is False

    def test_old_cache_is_stale(self):
        """Test that old cache is stale."""
        old_time = datetime.now(timezone.utc) - timedelta(minutes=120)
        cache = AliasCache(
            aliases={"test": AliasEntry("TEST", "test", "en", "name", "Test")},
            loaded_at=old_time,
            entry_count=1,
        )
        assert cache.is_stale(60) is True

    def test_cache_on_ttl_boundary(self):
        """Test cache at exactly TTL boundary."""
        boundary_time = datetime.now(timezone.utc) - timedelta(minutes=60)
        cache = AliasCache(
            aliases={},
            loaded_at=boundary_time,
            entry_count=0,
        )
        # At 60 minutes, should be stale (> not >=)
        assert cache.is_stale(60) is True


# =============================================================================
# TESTS: DynamicAliasLoader
# =============================================================================

class TestDynamicAliasLoader:
    """Test the DynamicAliasLoader class."""

    def test_init(self):
        """Test loader initialization."""
        loader = DynamicAliasLoader(
            db_secret_arn="arn:aws:secretsmanager:eu-north-1:123:secret:test",
            cache_ttl_minutes=30,
            region="eu-north-1",
        )

        assert loader.db_secret_arn == "arn:aws:secretsmanager:eu-north-1:123:secret:test"
        assert loader.cache_ttl_minutes == 30
        assert loader.region == "eu-north-1"

    def test_default_ttl(self):
        """Test default TTL is 60 minutes."""
        loader = DynamicAliasLoader(db_secret_arn="test")
        assert loader.cache_ttl_minutes == 60

    @pytest.mark.asyncio
    async def test_load_skills(self):
        """Test loading skill aliases."""
        loader = DynamicAliasLoader(db_secret_arn="test")

        # Mock connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = MOCK_SKILLS

        with patch.object(loader, '_get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            aliases = await loader._load_skills()

        # Check entries were created
        assert len(aliases) > 0

        # Check English name
        assert "accounting" in aliases
        assert aliases["accounting"].canonical_id == "ACCOUNTING"
        assert aliases["accounting"].match_type == "name_en"

        # Check Greek name (normalized)
        assert "λογιστικη" in aliases  # Accent removed
        assert aliases["λογιστικη"].canonical_id == "ACCOUNTING"
        assert aliases["λογιστικη"].match_type == "name_el"

        # Check aliases
        assert "bookkeeping" in aliases
        assert aliases["bookkeeping"].match_type == "alias_en"
        assert aliases["bookkeeping"].confidence == 0.95

    @pytest.mark.asyncio
    async def test_load_roles(self):
        """Test loading role aliases."""
        loader = DynamicAliasLoader(db_secret_arn="test")

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = MOCK_ROLES

        with patch.object(loader, '_get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            aliases = await loader._load_roles()

        # Check entries
        assert "accountant" in aliases
        assert aliases["accountant"].canonical_id == "ACCOUNTANT"
        assert aliases["accountant"].source_table == "role_taxonomy"

        # Check Greek (normalized)
        assert "λογιστης" in aliases  # Accent removed
        assert aliases["λογιστης"].canonical_id == "ACCOUNTANT"

    @pytest.mark.asyncio
    async def test_load_software(self):
        """Test loading software aliases."""
        loader = DynamicAliasLoader(db_secret_arn="test")

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = MOCK_SOFTWARE

        with patch.object(loader, '_get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            aliases = await loader._load_software()

        # Check entries
        assert "sap erp" in aliases
        assert aliases["sap erp"].canonical_id == "SAP_ERP"

        # Check alias
        assert "sap" in aliases
        assert aliases["sap"].canonical_id == "SAP_ERP"
        assert aliases["sap"].match_type == "alias"

    @pytest.mark.asyncio
    async def test_load_certifications(self):
        """Test loading certification aliases."""
        loader = DynamicAliasLoader(db_secret_arn="test")

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = MOCK_CERTIFICATIONS

        with patch.object(loader, '_get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            aliases = await loader._load_certifications()

        # Check abbreviation entry
        assert "cpa" in aliases
        assert aliases["cpa"].canonical_id == "CPA"
        assert aliases["cpa"].match_type == "abbreviation"
        assert aliases["cpa"].confidence == 0.98  # Higher for abbreviations

        # Check PMP
        assert "pmp" in aliases
        assert aliases["pmp"].canonical_id == "PMP"

    @pytest.mark.asyncio
    async def test_load_all_merges_tables(self):
        """Test load_all merges all taxonomy tables."""
        loader = DynamicAliasLoader(db_secret_arn="test")

        # Mock all load methods
        with patch.object(loader, '_load_skills', return_value={"skill1": AliasEntry("S1", "skill", "en", "name", "Skill1")}):
            with patch.object(loader, '_load_roles', return_value={"role1": AliasEntry("R1", "role", "en", "name", "Role1")}):
                with patch.object(loader, '_load_software', return_value={"soft1": AliasEntry("SW1", "software", "en", "name", "Soft1")}):
                    with patch.object(loader, '_load_certifications', return_value={"cert1": AliasEntry("C1", "cert", "en", "name", "Cert1")}):
                        aliases = await loader.load_all()

        # Should have entries from all tables
        assert "skill1" in aliases
        assert "role1" in aliases
        assert "soft1" in aliases
        assert "cert1" in aliases
        assert len(aliases) == 4

    @pytest.mark.asyncio
    async def test_caching_behavior(self):
        """Test that aliases are cached."""
        loader = DynamicAliasLoader(db_secret_arn="test", cache_ttl_minutes=60)

        # First load
        with patch.object(loader, '_load_skills', return_value={"test": AliasEntry("T", "t", "en", "n", "Test")}):
            with patch.object(loader, '_load_roles', return_value={}):
                with patch.object(loader, '_load_software', return_value={}):
                    with patch.object(loader, '_load_certifications', return_value={}):
                        aliases1 = await loader.load_all()

        # Second load should use cache
        with patch.object(loader, '_load_skills') as mock_skills:
            aliases2 = await loader.load_all()
            mock_skills.assert_not_called()

        # Results should be same
        assert aliases1 == aliases2

    @pytest.mark.asyncio
    async def test_reload_ignores_cache(self):
        """Test that reload() ignores cache."""
        loader = DynamicAliasLoader(db_secret_arn="test")

        # Pre-populate cache
        loader._cache = AliasCache(
            aliases={"old": AliasEntry("OLD", "t", "en", "n", "Old")},
            loaded_at=datetime.now(timezone.utc),
            entry_count=1,
        )

        # Reload should fetch fresh data
        with patch.object(loader, '_load_skills', return_value={"new": AliasEntry("NEW", "t", "en", "n", "New")}):
            with patch.object(loader, '_load_roles', return_value={}):
                with patch.object(loader, '_load_software', return_value={}):
                    with patch.object(loader, '_load_certifications', return_value={}):
                        aliases = await loader.reload()

        assert "new" in aliases
        assert "old" not in aliases

    def test_get_cached(self):
        """Test get_cached returns cache without loading."""
        loader = DynamicAliasLoader(db_secret_arn="test")

        # Empty cache
        assert loader.get_cached() == {}

        # Pre-populate
        loader._cache = AliasCache(
            aliases={"test": AliasEntry("T", "t", "en", "n", "Test")},
            loaded_at=datetime.now(timezone.utc),
            entry_count=1,
        )

        cached = loader.get_cached()
        assert "test" in cached

    @pytest.mark.asyncio
    async def test_handles_db_errors_gracefully(self):
        """Test that DB errors are handled gracefully."""
        loader = DynamicAliasLoader(db_secret_arn="test")

        # Make one load fail
        async def failing_load():
            raise Exception("DB Error")

        with patch.object(loader, '_load_skills', side_effect=failing_load):
            with patch.object(loader, '_load_roles', return_value={"role1": AliasEntry("R1", "r", "en", "n", "R1")}):
                with patch.object(loader, '_load_software', return_value={}):
                    with patch.object(loader, '_load_certifications', return_value={}):
                        # Should not raise, but return partial results
                        aliases = await loader.load_all()

        # Should still have roles
        assert "role1" in aliases


# =============================================================================
# TESTS: Sync Wrapper
# =============================================================================

class TestSyncWrapper:
    """Test synchronous wrapper functions."""

    def test_load_aliases_sync(self):
        """Test synchronous loading."""
        with patch('lcmgo_cagenai.query.dynamic_aliases.DynamicAliasLoader') as MockLoader:
            mock_instance = MagicMock()

            async def mock_load():
                return {"test": AliasEntry("T", "t", "en", "n", "Test")}

            mock_instance.load_all = mock_load
            mock_instance.close = MagicMock()
            MockLoader.return_value = mock_instance

            aliases = load_aliases_sync(db_secret_arn="test")

            assert "test" in aliases
            mock_instance.close.assert_called_once()


# =============================================================================
# TESTS: Global Loader
# =============================================================================

class TestGlobalLoader:
    """Test global loader singleton."""

    def test_get_global_loader_creates_singleton(self):
        """Test that global loader is created once."""
        import lcmgo_cagenai.query.dynamic_aliases as module

        # Reset global
        module._global_loader = None

        loader1 = get_global_loader(db_secret_arn="test1")
        loader2 = get_global_loader(db_secret_arn="test2")

        # Should be same instance
        assert loader1 is loader2

        # Cleanup
        module._global_loader = None


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run tests without pytest."""
    print("=" * 60)
    print("Dynamic Aliases Unit Tests")
    print("=" * 60)

    # Test normalize_text
    print("\n1. Testing normalize_text...")
    assert normalize_text("HELLO") == "hello"
    assert normalize_text("Λογιστής") == "λογιστης"
    assert normalize_text("  test  ") == "test"
    assert normalize_text("") == ""
    print("   PASSED: normalize_text works correctly")

    # Test AliasEntry
    print("\n2. Testing AliasEntry...")
    entry = AliasEntry("TEST", "skill", "en", "name", "Test")
    assert entry.canonical_id == "TEST"
    assert entry.confidence == 1.0
    print("   PASSED: AliasEntry works correctly")

    # Test AliasCache
    print("\n3. Testing AliasCache...")
    cache = AliasCache()
    assert cache.is_stale(60) is True
    cache = AliasCache(loaded_at=datetime.now(timezone.utc))
    assert cache.is_stale(60) is False
    print("   PASSED: AliasCache works correctly")

    # Test DynamicAliasLoader init
    print("\n4. Testing DynamicAliasLoader init...")
    loader = DynamicAliasLoader(db_secret_arn="test", cache_ttl_minutes=30)
    assert loader.cache_ttl_minutes == 30
    print("   PASSED: DynamicAliasLoader init works correctly")

    print("\n" + "=" * 60)
    print("All basic tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
