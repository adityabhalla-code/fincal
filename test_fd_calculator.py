"""Tests for FD Investment Calculator"""

import pytest
from fd_calculator import (
    CompoundingFrequency,
    FDResult,
    YearResult,
    calculate_fd,
    calculate_fd_with_topups,
    format_inr,
)


class TestCalculateFD:
    def test_single_year_quarterly(self):
        result = calculate_fd(100_000, 7.0, 1, CompoundingFrequency.QUARTERLY)
        assert isinstance(result, FDResult)
        assert len(result.year_wise) == 1
        expected = 100_000 * (1 + 0.07 / 4) ** 4
        assert abs(result.maturity_amount - expected) < 0.01

    def test_single_year_monthly(self):
        result = calculate_fd(50_000, 6.5, 1, CompoundingFrequency.MONTHLY)
        expected = 50_000 * (1 + 0.065 / 12) ** 12
        assert abs(result.maturity_amount - expected) < 0.01

    def test_single_year_yearly(self):
        result = calculate_fd(100_000, 8.0, 1, CompoundingFrequency.YEARLY)
        assert abs(result.maturity_amount - 108_000) < 0.01

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
            curr_open  = result.year_wise[i].opening_balance
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
        assert result.total_topups == 0.0

    def test_all_topups_zero_in_standard_fd(self):
        result = calculate_fd(100_000, 7.0, 3)
        assert all(yr.topup == 0.0 for yr in result.year_wise)

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


class TestCalculateFDWithTopups:
    def test_zero_topups_matches_standard(self):
        r1 = calculate_fd(100_000, 7.0, 3, CompoundingFrequency.QUARTERLY)
        r2 = calculate_fd_with_topups(100_000, 7.0, 3, [0, 0, 0], CompoundingFrequency.QUARTERLY)
        assert abs(r1.maturity_amount - r2.maturity_amount) < 0.001

    def test_topup_increases_maturity(self):
        base   = calculate_fd(100_000, 7.0, 3)
        topped = calculate_fd_with_topups(100_000, 7.0, 3, [10_000, 0, 0])
        assert topped.maturity_amount > base.maturity_amount

    def test_topup_added_at_start_of_year(self):
        # Year 1 opening = principal + topup[0]
        result = calculate_fd_with_topups(100_000, 8.0, 2, [20_000, 0])
        assert abs(result.year_wise[0].opening_balance - 120_000) < 0.001

    def test_topup_year2_opening(self):
        result = calculate_fd_with_topups(100_000, 8.0, 2, [0, 15_000])
        yr1_close = result.year_wise[0].closing_balance
        assert abs(result.year_wise[1].opening_balance - (yr1_close + 15_000)) < 0.001

    def test_total_topups_sum(self):
        topups = [10_000, 5_000, 20_000]
        result = calculate_fd_with_topups(100_000, 7.0, 3, topups)
        assert abs(result.total_topups - 35_000) < 0.001

    def test_total_interest_excludes_topups(self):
        topups = [10_000, 10_000]
        result = calculate_fd_with_topups(100_000, 7.0, 2, topups)
        expected_interest = result.maturity_amount - result.principal - result.total_topups
        assert abs(result.total_interest - expected_interest) < 0.001

    def test_topup_stored_in_year_result(self):
        topups = [5_000, 0, 8_000]
        result = calculate_fd_with_topups(100_000, 7.0, 3, topups)
        assert result.year_wise[0].topup == 5_000
        assert result.year_wise[1].topup == 0
        assert result.year_wise[2].topup == 8_000

    def test_year_wise_continuity_with_topups(self):
        topups = [10_000, 5_000, 0, 20_000]
        result = calculate_fd_with_topups(100_000, 7.0, 4, topups)
        for i in range(1, len(result.year_wise)):
            prev_close = result.year_wise[i - 1].closing_balance
            curr_topup = result.year_wise[i].topup
            curr_open  = result.year_wise[i].opening_balance
            assert abs(prev_close + curr_topup - curr_open) < 0.001

    def test_maturity_equals_last_year_closing(self):
        topups = [5_000, 10_000, 0]
        result = calculate_fd_with_topups(100_000, 7.5, 3, topups)
        assert abs(result.maturity_amount - result.year_wise[-1].closing_balance) < 0.001

    def test_wrong_topups_length_raises(self):
        with pytest.raises(ValueError):
            calculate_fd_with_topups(100_000, 7.0, 3, [1000, 2000])

    def test_negative_topup_raises(self):
        with pytest.raises(ValueError):
            calculate_fd_with_topups(100_000, 7.0, 2, [1000, -500])

    def test_single_year_with_topup(self):
        # P=100k, topup=50k at start → 150k compounds for 1 year at 8% quarterly
        result = calculate_fd_with_topups(100_000, 8.0, 1, [50_000])
        expected = 150_000 * (1 + 0.08 / 4) ** 4
        assert abs(result.maturity_amount - expected) < 0.01

    def test_compounding_respected_with_topups(self):
        r_q = calculate_fd_with_topups(100_000, 7.0, 2, [10_000, 0], CompoundingFrequency.QUARTERLY)
        r_y = calculate_fd_with_topups(100_000, 7.0, 2, [10_000, 0], CompoundingFrequency.YEARLY)
        assert r_q.maturity_amount > r_y.maturity_amount


class TestMonthsTenure:
    def test_months_only_no_years(self):
        # 0 years 6 months, quarterly: A = P * (1 + r/4)^(6*4/12) = P * (1+r/4)^2
        result = calculate_fd(100_000, 8.0, 0, CompoundingFrequency.QUARTERLY, tenure_months=6)
        expected = 100_000 * (1 + 0.08 / 4) ** 2
        assert abs(result.maturity_amount - expected) < 0.01

    def test_years_and_months(self):
        # 2 years 3 months quarterly
        result = calculate_fd(100_000, 8.0, 2, CompoundingFrequency.QUARTERLY, tenure_months=3)
        after_years = 100_000 * (1 + 0.08 / 4) ** 8
        expected    = after_years * (1 + 0.08 / 4) ** 1   # 3 months = 1 quarter
        assert abs(result.maturity_amount - expected) < 0.01

    def test_partial_row_appended(self):
        result = calculate_fd(100_000, 8.0, 2, tenure_months=6)
        assert len(result.year_wise) == 3   # 2 full years + 1 partial row

    def test_partial_row_period_months(self):
        result = calculate_fd(100_000, 8.0, 1, tenure_months=9)
        assert result.year_wise[-1].period_months == 9

    def test_full_year_rows_have_period_months_12(self):
        result = calculate_fd(100_000, 7.0, 3, tenure_months=6)
        for yr in result.year_wise[:3]:
            assert yr.period_months == 12

    def test_no_months_no_partial_row(self):
        result = calculate_fd(100_000, 7.0, 3)
        assert len(result.year_wise) == 3
        assert all(yr.period_months == 12 for yr in result.year_wise)

    def test_tenure_months_stored_in_result(self):
        result = calculate_fd(100_000, 7.0, 2, tenure_months=5)
        assert result.tenure_months == 5

    def test_zero_years_zero_months_raises(self):
        with pytest.raises(ValueError):
            calculate_fd(100_000, 7.0, 0, tenure_months=0)

    def test_invalid_tenure_months_raises(self):
        with pytest.raises(ValueError):
            calculate_fd(100_000, 7.0, 1, tenure_months=12)
        with pytest.raises(ValueError):
            calculate_fd(100_000, 7.0, 1, tenure_months=-1)

    def test_months_maturity_greater_than_years_only(self):
        base  = calculate_fd(100_000, 7.0, 2)
        extra = calculate_fd(100_000, 7.0, 2, tenure_months=6)
        assert extra.maturity_amount > base.maturity_amount

    def test_partial_continuity(self):
        result = calculate_fd(100_000, 8.0, 2, tenure_months=3)
        yr2_close    = result.year_wise[1].closing_balance
        partial_open = result.year_wise[2].opening_balance
        assert abs(yr2_close - partial_open) < 0.001


class TestFormatInr:
    def test_basic(self):
        assert format_inr(100_000) == "₹100,000.00"

    def test_decimal(self):
        assert format_inr(1234.56) == "₹1,234.56"

    def test_large_amount(self):
        assert format_inr(10_000_000) == "₹10,000,000.00"
