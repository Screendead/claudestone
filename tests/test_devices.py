"""Geometry checks that need no server: the display must read correctly from the front."""

from redstone.devices import DIGITS, SEGMENTS, front_view

TWO = """\
.###.
....#
....#
....#
.###.
#....
#....
#....
.###."""

FOUR = """\
.....
#...#
#...#
#...#
.###.
....#
....#
....#
....."""


def lit(digit: int) -> set:
    return {pos for s in DIGITS[digit] for pos in SEGMENTS[s]}


def test_two_reads_as_two_from_the_front():
    assert front_view(lit(2)) == TWO


def test_four_reads_as_four_from_the_front():
    assert front_view(lit(4)) == FOUR
