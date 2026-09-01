from rci.domain.identifiers import new_command_id, new_event_id, new_interaction_id


def test_generated_identifiers_are_unique() -> None:
    assert new_event_id() != new_event_id()
    assert new_interaction_id() != new_interaction_id()
    assert new_command_id() != new_command_id()
