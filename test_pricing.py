import pytest

from pricing import discount_percent, total_cents


# Rule 3: Orders of fewer than 10 units get no discount.
def test_no_discount_below_ten():
    assert discount_percent(9) == 0
    assert discount_percent(1) == 0


def test_no_discount_at_zero_boundary_for_percent():
    # discount_percent itself has no ValueError contract; total_cents does.
    assert discount_percent(0) == 0


# Rule 1: An order of 10 or more units gets a 10% discount.
def test_ten_percent_at_ten():
    assert discount_percent(10) == 10


def test_ten_percent_between_ten_and_ninety_nine():
    assert discount_percent(11) == 10
    assert discount_percent(99) == 10


# Rule 2: An order of 100 or more units gets a 20% discount instead.
def test_twenty_percent_at_one_hundred():
    assert discount_percent(100) == 20


def test_twenty_percent_above_one_hundred():
    assert discount_percent(101) == 20
    assert discount_percent(1000) == 20


# Rule 4: whole cents, nearest; exact half rounds up.
def test_total_no_discount_exact():
    assert total_cents(200, 5) == 1000


def test_total_ten_percent_exact():
    # 100 * 10 * 0.9 = 900
    assert total_cents(100, 10) == 900


def test_total_twenty_percent_exact():
    # 100 * 100 * 0.8 = 8000
    assert total_cents(100, 100) == 8000


def test_total_rounds_half_up():
    # 1 * 25 * 0.9 = 22.5 -> 23
    assert total_cents(1, 25) == 23


def test_total_rounds_down_when_below_half():
    # 1 * 11 * 0.9 = 9.9 -> 10
    assert total_cents(1, 11) == 10


def test_total_rounds_up_when_above_half():
    # 3 * 11 * 0.9 = 29.7 -> 30
    assert total_cents(3, 11) == 30


# Rule 5: quantity below 1 or negative unit price raises ValueError.
def test_quantity_zero_raises():
    with pytest.raises(ValueError):
        total_cents(100, 0)


def test_quantity_negative_raises():
    with pytest.raises(ValueError):
        total_cents(100, -1)


def test_negative_unit_price_raises():
    with pytest.raises(ValueError):
        total_cents(-1, 5)


def test_zero_unit_price_allowed():
    assert total_cents(0, 5) == 0


def test_quantity_one_is_valid_minimum():
    assert total_cents(50, 1) == 50
