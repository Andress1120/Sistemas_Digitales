"""Pruebas unitarias (pytest) del decodificador de 7 segmentos.
Ejecutar:  pytest -v
"""
import os
import pytest

from sevensegdec import read_table, simulate, check_table

TABLE_FILE = os.path.join(os.path.dirname(__file__), "tabla_7seg.txt")
MASK = 0x7F


@pytest.fixture(scope="module")
def table():
    return read_table(TABLE_FILE)


@pytest.fixture(scope="module")
def readings(table):
    """Simulates once and returns {bcd: sseg}."""
    return dict(simulate(table))


@pytest.fixture(scope="module")
def readings_inv(table):
    return dict(simulate(table, invert=True))


# --- the table file itself ---------------------------------------------------

def test_table_has_16_lines_of_7_bits():
    lines = [l.strip() for l in open(TABLE_FILE) if l.strip()]
    assert len(lines) == 16
    assert all(len(l) == 7 and set(l) <= {"0", "1"} for l in lines)


def test_table_patterns_are_unique(table):
    assert len(set(table)) == 16, "two inputs share the same pattern"


def test_read_table_rejects_bad_file(tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("1111110\n0110000\n")           # only 2 lines
    assert read_table(str(bad)) == tuple([0] * 16)  # falls back to the zero table


# --- the decoder: one test per input value (16 parametrized cases) -----------

# reference values (expected independent of the table file)
EXPECTED = [
    "1111110", "0110000", "1101101", "1111001", "0110011",   # 0-4
    "1011011", "1011111", "1110000", "1111111", "1111011",   # 5-9 (6 and 9 closed, 1 on the right)
    "0000001", "0001000", "1000000", "1100011", "0001001", "1001001",  # 10-15 custom
]


@pytest.mark.parametrize("bcd", range(16))
def test_decoder_matches_table(bcd, table, readings):
    assert readings[bcd] == table[bcd]


@pytest.mark.parametrize("bcd", range(16))
def test_decoder_matches_reference(bcd, readings):
    assert f"{readings[bcd]:07b}" == EXPECTED[bcd]


@pytest.mark.parametrize("bcd", range(16))
def test_inverted_output(bcd, table, readings_inv):
    assert readings_inv[bcd] == (~table[bcd]) & MASK


# --- the checker itself must be able to fail ---------------------------------

def test_check_table_ok(table):
    assert check_table(table) == []


def test_check_table_with_invert_ok(table):
    assert check_table(table, invert=True) == []


def test_simulation_covers_all_16_inputs(table):
    assert [b for b, _ in simulate(table)] == list(range(16))
