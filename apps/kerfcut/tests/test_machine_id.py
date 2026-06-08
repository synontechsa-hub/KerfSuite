"""
KerfCut — Machine ID Tests
Verify that the composite hardware fingerprint is deterministic, stable,
and produces correctly formatted output.
"""
import re
import pytest


def test_machine_id_deterministic():
    """Calling _get_machine_id() twice must return the same value."""
    from core.auth import _get_machine_id

    id1 = _get_machine_id()
    id2 = _get_machine_id()
    assert id1 == id2, f"Machine ID is not deterministic: {id1!r} != {id2!r}"


def test_machine_id_length():
    """The raw machine ID must be exactly 16 uppercase hex characters."""
    from core.auth import _get_machine_id

    mid = _get_machine_id()
    assert len(mid) == 16, f"Expected 16 chars, got {len(mid)}: {mid!r}"


def test_machine_id_hex():
    """The raw machine ID must be valid uppercase hexadecimal."""
    from core.auth import _get_machine_id

    mid = _get_machine_id()
    assert re.fullmatch(r"[0-9A-F]{16}", mid), (
        f"Machine ID is not valid uppercase hex: {mid!r}"
    )


def test_machine_id_display_format():
    """get_machine_id_display() must return XXXX-XXXX-XXXX-XXXX format."""
    from core.auth import get_machine_id_display

    display = get_machine_id_display()
    assert re.fullmatch(r"[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}", display), (
        f"Display format is wrong: {display!r}"
    )


def test_machine_id_display_matches_raw():
    """The display format must be the raw ID with dashes inserted."""
    from core.auth import _get_machine_id, get_machine_id_display

    raw = _get_machine_id()
    display = get_machine_id_display()
    assert display.replace("-", "") == raw, (
        f"Display {display!r} does not match raw {raw!r}"
    )
