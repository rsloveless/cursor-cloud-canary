from pricing import discount_percent, total_cents


def test_no_discount_below_ten():
    assert discount_percent(9) == 0


def test_discount_starts_at_ten():
    assert discount_percent(10) == 10


def test_simple_total():
    assert total_cents(200, 5) == 1000
