"""Tests for the shared ``wg show <iface> dump`` parser."""

from __future__ import annotations

from kosatka_agent.providers._wgcore import PeerStats, parse_wg_dump


def test_parse_skips_interface_header_row():
    """First dump line describes the interface; only 4 fields, no peers."""
    dump = "PRIVKEY\tPUBKEY\t51820\toff"
    assert parse_wg_dump(dump) == []


def test_parse_extracts_full_peer_row():
    dump = "\t".join(
        [
            "Pub1=",
            "Psk1=",
            "1.2.3.4:51820",
            "10.8.0.5/32",
            "1735000000",
            "1024",
            "2048",
            "25",
        ]
    )
    rows = parse_wg_dump(dump)
    assert rows == [
        PeerStats(
            public_key="Pub1=",
            endpoint="1.2.3.4:51820",
            latest_handshake=1735000000,
            transfer_rx=1024,
            transfer_tx=2048,
        )
    ]
    assert rows[0].endpoint_ip == "1.2.3.4"


def test_parse_handles_ipv6_bracketed_endpoint():
    dump = "\t".join(["Pub2=", "Psk2=", "[2001:db8::1]:51820", "10.8.0.6/32", "0", "0", "0", "off"])
    rows = parse_wg_dump(dump)
    assert rows[0].endpoint == "[2001:db8::1]:51820"
    assert rows[0].endpoint_ip == "2001:db8::1"


def test_parse_handles_no_endpoint_yet():
    """Before first handshake ``wg`` prints ``"(none)"`` for the endpoint."""
    dump = "\t".join(["Pub3=", "Psk3=", "(none)", "10.8.0.7/32", "0", "0", "0", "off"])
    rows = parse_wg_dump(dump)
    assert rows[0].endpoint == "(none)"
    assert rows[0].endpoint_ip is None


def test_parse_skips_garbled_rows():
    """A line with non-numeric handshake field shouldn't crash the parser."""
    dump = "\t".join(["Pub4=", "Psk4=", "1.2.3.4:51820", "10.8.0.8/32", "abc", "1", "2", "off"])
    assert parse_wg_dump(dump) == []


def test_parse_multiple_peers():
    dump = (
        "PRIVKEY\tPUBKEY\t51820\toff\n"
        + "\t".join(["A=", "Pa=", "1.1.1.1:1", "10.8.0.1/32", "1", "10", "20", "0"])
        + "\n"
        + "\t".join(["B=", "Pb=", "(none)", "10.8.0.2/32", "0", "0", "0", "0"])
    )
    rows = parse_wg_dump(dump)
    assert [r.public_key for r in rows] == ["A=", "B="]
    assert rows[0].endpoint_ip == "1.1.1.1"
    assert rows[1].endpoint_ip is None
