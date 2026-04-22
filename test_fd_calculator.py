"""Tests for FD Investment Calculator"""

import pytest
from fd_calculator import (
    CompoundingFrequency,
    FDResult,
    YearResult,
    calculate_fd,
    format_inr,
)


class TestCalculateFD:
    def test_single_year_quarterly(self):
        result = calculate_fd(100_000, 7.0, 1, CompoundingFrequency.QUARTERLY)
        assert isinstance(result, FDResult)
        assert len(result.year_wise) == 1
        # A = 100000 * (1 + 0.07/4)^4
        expected = 100_000 * (1 + 0.07 / 4) ** 4
        assert abs(result.maturity_amount - expected) < 0.01

    def test_single_year_monthly(self):
        result = calculate_fd(50_000, 6.5, 1, CompoundingFrequency.MONTHLY)
        expected = 50_000 * (1 + 0.065 / 12) ** 12
        assert abs(result.maturity_amount - expected) < 0.01

    def test_single_year_yearly(self):
        result = calculate_fd(100_000, 8.0, 1, CompoundingFrequency.YEARLY)
        expected = 100_000 * 1.08
        assert abs(result.maturity_amount - expected) < 0.01

    def test_multi_year_quarterly(self):
        result = calculate_fd(100_000, 7.0, 5, CompoundingFrequency.QUARTERLY)
        assert len(result.year_wise) == 5
        expected = 100_000 * (1 + 0.07 / 4) ** (4 * 5)
        assert abs(result.maturity_amount - expected) < 0.01

    def test_multi_year_yearly(self):
        result = calculate_fd(200_000, 6.0, 3, CompoundingFrequency.YEARLY)
        expected = 200_000 * (1.06 ** 3)
        assert abs(result.maturity_amount - expected) < 0.01

    def test_year_wise_continuity(self):
        result = calculate_fd(100_000, 8.0, 4, CompoundingFrequency.QUARTERLY)
        for i in range(1, len(result.year_wise)):
            prev_close = result.year_wise[i - 1].closing_balance
            curr_open = result.year_wise[i].opening_balance
            assert abs(prev_close - curr_open) < 0.001

    def test_year_wise_interest_matches_diff(self):
        result = calculate_fd(100_000, 7.0, 3, CompoundingFrequency.QUARTERLY)
        for yr in result.year_wise:
            assert abs(yr.closing_balance - yr.opening_balance - yr.interest_earned) < 0.001

    def test_total_interest(self):
        result = calculate_fd(100_000, 7.0, 3, CompoundingFrequency.QUARTERLY)
        assert abs(result.total_interest - (result.maturity_amount - result.principal)) < 0.001

    def test_first_year_opening_equals_principal(self):
        result = calculate_fd(75_000, 7.5, 2, CompoundingFrequency.HALF_YEARLY)
        assert result.year_wise[0].opening_balance == 75_000

    def test_default_compounding_is_quarterly(self):
        r1 = calculate_fd(100_000, 7.0, 2)
        r2 = calculate_fd(100_000, 7.0, 2, CompoundingFrequency.QUARTERLY)
        assert abs(r1.maturity_amount - r2.maturity_amount) < 0.001

    def test_result_fields(self):
        result = calculate_fd(100_000, 7.0, 1)
        assert result.principal == 100_000
        assert result.annual_rate == 7.0
        assert result.tenure_years == 1
        assert result.compounding == CompoundingFrequency.QUARTERLY

    def test_invalid_principal_raises(self):
        with pytest.raises(ValueError):
            calculate_fd(0, 7.0, 1)
        with pytest.raises(ValueError):
            calculate_fd(-1000, 7.0, 1)

    def test_invalid_rate_raises(self):
        with pytest.raises(ValueError):
            calculate_fd(100_000, 0, 1)
        with pytest.raises(ValueError):
            calculate_fd(100_000, -5, 1)

    def test_invalid_tenure_raises(self):
        with pytest.raises(ValueError):
            calculate_fd(100_000, 7.0, 0)

    def test_large_tenure(self):
        result = calculate_fd(100_000, 7.0, 20, CompoundingFrequency.QUARTERLY)
        assert len(result.year_wise) == 20
        expected = 100_000 * (1 + 0.07 / 4) ** (4 * 20)
        assert abs(result.maturity_amount - expected) < 0.01


class TestFormatInr:
    def test_basic(self):
        assert format_inr(100_000) == "₹100,000.00"

    def test_decimal(self):
        assert format_inr(1234.56) == "₹1,234.56"

    def test_large_amount(self):
        assert format_inr(10_000_000) == "₹10,000,000.00"
