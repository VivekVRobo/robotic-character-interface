import pytest

from rci.audit.logger import AuditLogger
from rci.audit.query import AuditQuery, query_entries


@pytest.mark.asyncio
async def test_query_filters_event_type_and_source() -> None:
    logger = AuditLogger()
    await logger.append(event_type="one", source="alpha")
    await logger.append(event_type="two", source="beta")
    await logger.append(event_type="one", source="beta")

    result = query_entries(logger.entries, AuditQuery(event_type="one", source="beta"))

    assert len(result) == 1
    assert result[0].sequence == 2
