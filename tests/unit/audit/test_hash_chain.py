import pytest

from rci.audit.hash_chain import AuditIntegrityError, verify_chain
from rci.audit.logger import AuditLogger


@pytest.mark.asyncio
async def test_hash_chain_verifies_after_multiple_entries() -> None:
    logger = AuditLogger()
    await logger.append(event_type="one", source="test")
    await logger.append(event_type="two", source="test", payload={"value": 3})

    verify_chain(logger.entries)
    assert logger.entries[1].previous_hash == logger.entries[0].entry_hash


@pytest.mark.asyncio
async def test_tampered_entry_is_detected() -> None:
    logger = AuditLogger()
    entry = await logger.append(event_type="one", source="test", payload={"safe": True})
    tampered = entry.model_copy(update={"payload": {"safe": False}})

    with pytest.raises(AuditIntegrityError, match="entry hash mismatch"):
        verify_chain([tampered])
