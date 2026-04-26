"""Tests for FD Investment Calculator"""

import pytest
from fd_calculator import (
    CompoundingFrequency,
    DCFResult,
    FDResult,
    FVResult,
    LoanResult,
    OptionsResult,
    TaxResult,
    YearResult,
    calculate_dcf,
    calculate_fd,
    calculate_fd_with_topups,
    calculate_future_value,
    calculate_home_loan,
    calculate_options_value,
    calculate_tax,
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


class TestFutureValue:
    def test_basic_no_inflation(self):
        result = calculate_future_value(100_000, 10.0, 5)
        expected = 100_000 * (1.10 ** 5)
        assert abs(result.nominal_fv - expected) < 0.01

    def test_single_year(self):
        result = calculate_future_value(100_000, 8.0, 1)
        assert abs(result.nominal_fv - 108_000) < 0.01

    def test_no_inflation_real_equals_nominal(self):
        result = calculate_future_value(100_000, 10.0, 5, inflation_percent=0)
        assert abs(result.real_fv - result.nominal_fv) < 0.001

    def test_inflation_reduces_real_value(self):
        result = calculate_future_value(100_000, 10.0, 10, inflation_percent=6.0)
        assert result.real_fv < result.nominal_fv

    def test_real_fv_formula(self):
        # real = nominal / (1 + inf)^years
        result = calculate_future_value(100_000, 10.0, 5, inflation_percent=6.0)
        nominal  = 100_000 * (1.10 ** 5)
        expected_real = nominal / (1.06 ** 5)
        assert abs(result.real_fv - expected_real) < 0.01

    def test_total_growth(self):
        result = calculate_future_value(100_000, 10.0, 5)
        assert abs(result.total_growth - (result.nominal_fv - 100_000)) < 0.001

    def test_inflation_loss(self):
        result = calculate_future_value(100_000, 10.0, 5, inflation_percent=6.0)
        assert abs(result.inflation_loss - (result.nominal_fv - result.real_fv)) < 0.001

    def test_year_wise_length_no_months(self):
        result = calculate_future_value(100_000, 10.0, 5)
        assert len(result.year_wise) == 5

    def test_year_wise_length_with_months(self):
        result = calculate_future_value(100_000, 10.0, 3, tenure_months=6)
        assert len(result.year_wise) == 4  # 3 full years + 1 partial row

    def test_year_wise_labels(self):
        result = calculate_future_value(100_000, 10.0, 2, tenure_months=3)
        assert result.year_wise[0].label == "Yr 1"
        assert result.year_wise[1].label == "Yr 2"
        assert result.year_wise[2].label == "+3m"

    def test_partial_months_nominal(self):
        # 0 years 6 months: nominal = pv * (1.10)^0.5
        result = calculate_future_value(100_000, 10.0, 0, tenure_months=6)
        expected = 100_000 * (1.10 ** 0.5)
        assert abs(result.nominal_fv - expected) < 0.01

    def test_nominal_increases_each_year(self):
        result = calculate_future_value(100_000, 10.0, 5)
        for i in range(1, len(result.year_wise)):
            assert result.year_wise[i].nominal_value > result.year_wise[i-1].nominal_value

    def test_result_fields_stored(self):
        result = calculate_future_value(100_000, 10.0, 5, inflation_percent=6.0, tenure_months=3)
        assert result.present_value == 100_000
        assert result.return_rate == 10.0
        assert result.inflation_rate == 6.0
        assert result.tenure_years == 5
        assert result.tenure_months == 3

    def test_invalid_pv_raises(self):
        with pytest.raises(ValueError):
            calculate_future_value(0, 10.0, 5)

    def test_invalid_return_raises(self):
        with pytest.raises(ValueError):
            calculate_future_value(100_000, -1, 5)

    def test_zero_return_zero_inflation_raises(self):
        with pytest.raises(ValueError):
            calculate_future_value(100_000, 0, 5, inflation_percent=0)

    def test_negative_inflation_raises(self):
        with pytest.raises(ValueError):
            calculate_future_value(100_000, 10.0, 5, inflation_percent=-1)

    def test_zero_tenure_raises(self):
        with pytest.raises(ValueError):
            calculate_future_value(100_000, 10.0, 0, tenure_months=0)

    def test_invalid_months_raises(self):
        with pytest.raises(ValueError):
            calculate_future_value(100_000, 10.0, 1, tenure_months=12)

    def test_amount_needed_stored_per_row(self):
        result = calculate_future_value(100_000, 10.0, 3, inflation_percent=6.0)
        for i, yr in enumerate(result.year_wise, 1):
            expected = 100_000 * (1.06 ** i)
            assert abs(yr.amount_needed - expected) < 0.01

    def test_amount_needed_zero_when_no_inflation(self):
        result = calculate_future_value(100_000, 10.0, 3)
        assert all(yr.amount_needed == 0.0 for yr in result.year_wise)


class TestFutureValueInflationOnly:
    def test_inflation_only_nominal_unchanged(self):
        # With no return, nominal stays at PV every year
        result = calculate_future_value(100_000, 0, 3, inflation_percent=6.0)
        for yr in result.year_wise:
            assert abs(yr.nominal_value - 100_000) < 0.001

    def test_inflation_only_amount_needed(self):
        # Amount needed after 5 years at 6% inflation = 100000 * 1.06^5
        result = calculate_future_value(100_000, 0, 5, inflation_percent=6.0)
        expected = 100_000 * (1.06 ** 5)
        assert abs(result.amount_needed_fv - expected) < 0.01

    def test_inflation_only_real_value(self):
        # Real value = PV / (1+inf)^t (purchasing power of original amount)
        result = calculate_future_value(100_000, 0, 5, inflation_percent=6.0)
        expected_real = 100_000 / (1.06 ** 5)
        assert abs(result.real_fv - expected_real) < 0.01

    def test_inflation_only_year_wise_real_decreases(self):
        result = calculate_future_value(100_000, 0, 5, inflation_percent=6.0)
        for i in range(1, len(result.year_wise)):
            assert result.year_wise[i].real_value < result.year_wise[i-1].real_value

    def test_inflation_only_with_months(self):
        result = calculate_future_value(100_000, 0, 1, inflation_percent=6.0, tenure_months=6)
        assert len(result.year_wise) == 2
        assert abs(result.year_wise[-1].nominal_value - 100_000) < 0.001

    def test_zero_return_is_valid_with_inflation(self):
        result = calculate_future_value(100_000, 0, 3, inflation_percent=6.0)
        assert isinstance(result, FVResult)

    def test_both_return_and_inflation(self):
        result = calculate_future_value(100_000, 12.0, 5, inflation_percent=6.0)
        assert result.nominal_fv > result.real_fv
        assert result.real_fv > 100_000   # still grew in real terms (12% > 6%)


class TestOptionsValue:
    def test_call_itm_intrinsic(self):
        r = calculate_options_value('call', 1500, 1400, 120)
        assert abs(r.intrinsic_value - 100) < 0.001

    def test_call_itm_extrinsic(self):
        r = calculate_options_value('call', 1500, 1400, 120)
        assert abs(r.extrinsic_value - 20) < 0.001

    def test_call_otm_intrinsic_zero(self):
        r = calculate_options_value('call', 1400, 1500, 40)
        assert r.intrinsic_value == 0.0

    def test_call_otm_extrinsic_equals_premium(self):
        r = calculate_options_value('call', 1400, 1500, 40)
        assert abs(r.extrinsic_value - 40) < 0.001

    def test_put_itm_intrinsic(self):
        r = calculate_options_value('put', 1400, 1500, 120)
        assert abs(r.intrinsic_value - 100) < 0.001

    def test_put_otm_intrinsic_zero(self):
        r = calculate_options_value('put', 1500, 1400, 40)
        assert r.intrinsic_value == 0.0

    def test_call_breakeven(self):
        r = calculate_options_value('call', 1500, 1400, 80)
        assert abs(r.breakeven - 1480) < 0.001

    def test_put_breakeven(self):
        r = calculate_options_value('put', 1400, 1500, 80)
        assert abs(r.breakeven - 1420) < 0.001

    def test_moneyness_itm_call(self):
        r = calculate_options_value('call', 1600, 1400, 220)
        assert r.moneyness == 'ITM'

    def test_moneyness_otm_call(self):
        r = calculate_options_value('call', 1400, 1600, 40)
        assert r.moneyness == 'OTM'

    def test_moneyness_atm(self):
        r = calculate_options_value('call', 1500, 1500, 50)
        assert r.moneyness == 'ATM'

    def test_moneyness_itm_put(self):
        r = calculate_options_value('put', 1300, 1500, 220)
        assert r.moneyness == 'ITM'

    def test_intrinsic_plus_extrinsic_le_premium(self):
        # intrinsic + extrinsic <= premium (extrinsic = max(0, P - intrinsic))
        r = calculate_options_value('call', 1500, 1400, 120)
        assert abs(r.intrinsic_value + r.extrinsic_value - r.premium) < 0.001

    def test_invalid_option_type_raises(self):
        with pytest.raises(ValueError):
            calculate_options_value('forward', 1500, 1400, 80)

    def test_invalid_price_raises(self):
        with pytest.raises(ValueError):
            calculate_options_value('call', 0, 1400, 80)

    def test_invalid_premium_raises(self):
        with pytest.raises(ValueError):
            calculate_options_value('call', 1500, 1400, 0)


class TestDCF:
    def test_basic_intrinsic_value(self):
        r = calculate_dcf(50, 15, 4, 12, 10)
        assert isinstance(r, DCFResult)
        assert r.intrinsic_value > 0

    def test_intrinsic_equals_pv_cf_plus_pv_tv(self):
        r = calculate_dcf(50, 15, 4, 12, 10)
        assert abs(r.intrinsic_value - (r.pv_cash_flows + r.pv_terminal_value)) < 0.001

    def test_year_wise_length(self):
        r = calculate_dcf(50, 15, 4, 12, 10)
        assert len(r.year_wise) == 10

    def test_year_wise_cf_grows(self):
        r = calculate_dcf(50, 15, 4, 12, 10)
        for i in range(1, len(r.year_wise)):
            assert r.year_wise[i].projected_cf > r.year_wise[i-1].projected_cf

    def test_pv_decreases_each_year(self):
        # Assuming growth < discount rate eventually, PV should decrease later
        r = calculate_dcf(50, 10, 4, 12, 10)
        # At minimum, discount factor strictly decreases
        for i in range(1, len(r.year_wise)):
            assert r.year_wise[i].discount_factor < r.year_wise[i-1].discount_factor

    def test_terminal_value_positive(self):
        r = calculate_dcf(50, 15, 4, 12, 10)
        assert r.terminal_value > 0
        assert r.pv_terminal_value > 0

    def test_terminal_value_formula(self):
        r = calculate_dcf(50, 15, 4, 12, 10)
        last_cf   = r.year_wise[-1].projected_cf
        expected_tv = last_cf * 1.04 / (0.12 - 0.04)
        assert abs(r.terminal_value - expected_tv) < 0.01

    def test_margin_of_safety_undervalued(self):
        r = calculate_dcf(50, 15, 4, 12, 10, current_price=100)
        assert r.margin_of_safety_pct > 0   # intrinsic > 100 for these inputs

    def test_margin_of_safety_zero_when_no_price(self):
        r = calculate_dcf(50, 15, 4, 12, 10)
        assert r.margin_of_safety_pct == 0.0

    def test_higher_growth_higher_intrinsic(self):
        r1 = calculate_dcf(50, 10, 4, 12, 10)
        r2 = calculate_dcf(50, 15, 4, 12, 10)
        assert r2.intrinsic_value > r1.intrinsic_value

    def test_higher_discount_lower_intrinsic(self):
        r1 = calculate_dcf(50, 15, 4, 10, 10)
        r2 = calculate_dcf(50, 15, 4, 14, 10)
        assert r2.intrinsic_value < r1.intrinsic_value

    def test_discount_le_terminal_growth_raises(self):
        with pytest.raises(ValueError):
            calculate_dcf(50, 15, 12, 12, 10)   # discount == terminal

    def test_invalid_cf_raises(self):
        with pytest.raises(ValueError):
            calculate_dcf(0, 15, 4, 12, 10)

    def test_invalid_years_raises(self):
        with pytest.raises(ValueError):
            calculate_dcf(50, 15, 4, 12, 0)

    def test_negative_terminal_growth_raises(self):
        with pytest.raises(ValueError):
            calculate_dcf(50, 15, -1, 12, 10)

    def test_discount_factor_formula(self):
        r = calculate_dcf(50, 15, 4, 12, 5)
        for yr in r.year_wise:
            expected_df = 1 / (1.12 ** yr.year)
            assert abs(yr.discount_factor - expected_df) < 0.0001

    def test_pv_equals_cf_times_df(self):
        r = calculate_dcf(50, 15, 4, 12, 5)
        for yr in r.year_wise:
            assert abs(yr.present_value - yr.projected_cf * yr.discount_factor) < 0.001


class TestIncomeTax:
    # ── New regime basic ─────────────────────────────────────────
    def test_zero_tax_below_12l_new_regime(self):
        # ₹12L taxable → slab tax = 60,000 → 87A rebate wipes it out
        r = calculate_tax(12_00_000, regime='new', is_salaried=False)
        assert r.total_tax == 0.0

    def test_zero_tax_salaried_12_75l(self):
        # Salaried with ₹75k std deduction → taxable = ₹12L → zero tax
        r = calculate_tax(12_75_000, regime='new', is_salaried=True)
        assert r.total_tax == 0.0

    def test_rebate_87a_new_regime(self):
        r = calculate_tax(10_00_000, regime='new', is_salaried=False)
        assert r.rebate_87a > 0
        assert r.income_tax == 0.0

    def test_no_rebate_above_12l_new(self):
        r = calculate_tax(13_00_000, regime='new', is_salaried=False)
        assert r.rebate_87a == 0.0
        assert r.income_tax > 0

    def test_standard_deduction_new_salaried(self):
        r = calculate_tax(15_00_000, regime='new', is_salaried=True)
        assert r.standard_deduction == 75_000
        assert r.taxable_income == 14_25_000

    def test_no_standard_deduction_self_employed(self):
        r = calculate_tax(15_00_000, regime='new', is_salaried=False)
        assert r.standard_deduction == 0
        assert r.taxable_income == 15_00_000

    def test_new_regime_slab_tax_20l(self):
        # 20L taxable: 5%×4L + 10%×4L + 15%×4L + 20%×4L
        # = 20000 + 40000 + 60000 + 80000 = 200000
        r = calculate_tax(20_00_000, regime='new', is_salaried=False)
        assert abs(r.slab_tax - 2_00_000) < 1

    def test_cess_is_4pct(self):
        r = calculate_tax(20_00_000, regime='new', is_salaried=False)
        expected_cess = (r.income_tax + r.surcharge) * 0.04
        assert abs(r.cess - expected_cess) < 0.01

    def test_total_tax_components(self):
        r = calculate_tax(25_00_000, regime='new', is_salaried=False)
        assert abs(r.total_tax - (r.income_tax + r.surcharge + r.cess)) < 0.01

    def test_effective_rate(self):
        r = calculate_tax(25_00_000, regime='new', is_salaried=False)
        assert abs(r.effective_rate_pct - r.total_tax / 25_00_000 * 100) < 0.001

    def test_monthly_inhand(self):
        r = calculate_tax(20_00_000, regime='new', is_salaried=False)
        assert abs(r.monthly_inhand - (20_00_000 - r.total_tax) / 12) < 0.01

    def test_slab_breakdown_present(self):
        r = calculate_tax(20_00_000, regime='new', is_salaried=False)
        assert len(r.slab_breakdown) > 0

    def test_slab_breakdown_tax_sums_to_slab_tax(self):
        r = calculate_tax(20_00_000, regime='new', is_salaried=False)
        assert abs(sum(s.tax_in_slab for s in r.slab_breakdown) - r.slab_tax) < 0.01

    # ── Old regime ───────────────────────────────────────────────
    def test_standard_deduction_old_salaried(self):
        r = calculate_tax(10_00_000, regime='old', is_salaried=True)
        assert r.standard_deduction == 50_000

    def test_rebate_87a_old_regime(self):
        # taxable ≤ 5L in old regime → rebate up to 12,500
        r = calculate_tax(5_00_000, regime='old', is_salaried=False)
        assert r.rebate_87a > 0
        assert r.total_tax == 0.0

    def test_80c_deduction_capped_at_150000(self):
        r = calculate_tax(15_00_000, regime='old', is_salaried=False, deduction_80c=2_00_000)
        assert r.other_deductions == 1_50_000  # capped

    def test_old_regime_deductions_reduce_taxable(self):
        r_no_ded  = calculate_tax(15_00_000, regime='old', is_salaried=False)
        r_with_ded = calculate_tax(15_00_000, regime='old', is_salaried=False,
                                   deduction_80c=1_50_000, deduction_80d=25_000)
        assert r_with_ded.taxable_income < r_no_ded.taxable_income

    def test_deductions_not_applied_in_new_regime(self):
        r_clean = calculate_tax(15_00_000, regime='new', is_salaried=False)
        r_ded   = calculate_tax(15_00_000, regime='new', is_salaried=False,
                                deduction_80c=1_50_000)
        assert r_clean.taxable_income == r_ded.taxable_income

    # ── Surcharge ────────────────────────────────────────────────
    def test_no_surcharge_below_50l(self):
        r = calculate_tax(40_00_000, regime='new', is_salaried=False)
        assert r.surcharge == 0.0

    def test_surcharge_10pct_between_50l_1cr(self):
        r = calculate_tax(60_00_000, regime='new', is_salaried=False)
        assert r.surcharge_rate == 0.10
        assert abs(r.surcharge - r.income_tax * 0.10) < 0.01

    def test_surcharge_capped_25pct_new_regime(self):
        r = calculate_tax(6_00_00_000, regime='new', is_salaried=False)
        assert r.surcharge_rate == 0.25

    def test_surcharge_37pct_old_regime_above_5cr(self):
        r = calculate_tax(6_00_00_000, regime='old', is_salaried=False)
        assert r.surcharge_rate == 0.37

    # ── Validation ───────────────────────────────────────────────
    def test_invalid_regime_raises(self):
        with pytest.raises(ValueError):
            calculate_tax(10_00_000, regime='middle')

    def test_zero_income_raises(self):
        with pytest.raises(ValueError):
            calculate_tax(0)

    def test_negative_deduction_raises(self):
        with pytest.raises(ValueError):
            calculate_tax(10_00_000, deduction_80c=-1000)

    # ── Result fields ────────────────────────────────────────────
    def test_result_regime_field(self):
        r = calculate_tax(10_00_000, regime='new')
        assert r.regime == 'new'

    def test_new_regime_better_without_deductions(self):
        # For typical income with no deductions, new regime usually wins
        n = calculate_tax(15_00_000, regime='new', is_salaried=False)
        o = calculate_tax(15_00_000, regime='old', is_salaried=False)
        # New regime should be <= old when no deductions
        assert n.total_tax <= o.total_tax


class TestHomeLoan:
    def test_emi_formula(self):
        # ₹50L at 8.5% for 20 years
        r   = calculate_home_loan(50_00_000, 8.5, 20)
        mr  = 8.5 / 12 / 100
        n   = 240
        expected_emi = 50_00_000 * mr * (1 + mr) ** n / ((1 + mr) ** n - 1)
        assert abs(r.monthly_emi - expected_emi) < 0.01

    def test_total_payment(self):
        r = calculate_home_loan(50_00_000, 8.5, 20)
        assert abs(r.total_payment - r.monthly_emi * 240) < 1

    def test_total_interest(self):
        r = calculate_home_loan(50_00_000, 8.5, 20)
        assert abs(r.total_interest - (r.total_payment - 50_00_000)) < 1

    def test_total_interest_positive(self):
        r = calculate_home_loan(50_00_000, 8.5, 20)
        assert r.total_interest > 0

    def test_year_wise_count_whole_years(self):
        r = calculate_home_loan(50_00_000, 8.5, 20)
        assert len(r.year_wise) == 20

    def test_year_wise_count_with_extra_months(self):
        # 5 years 6 months → 6 year-groups (last partial)
        r = calculate_home_loan(50_00_000, 8.5, 5, tenure_months=6)
        assert len(r.year_wise) == 6

    def test_opening_balance_year1_equals_principal(self):
        r = calculate_home_loan(30_00_000, 9.0, 15)
        assert r.year_wise[0].opening_balance == 30_00_000

    def test_closing_balance_decreases_each_year(self):
        r = calculate_home_loan(30_00_000, 9.0, 15)
        for i in range(1, len(r.year_wise)):
            assert r.year_wise[i].closing_balance < r.year_wise[i-1].closing_balance

    def test_final_closing_balance_near_zero(self):
        r = calculate_home_loan(30_00_000, 9.0, 15)
        assert r.year_wise[-1].closing_balance < 1.0

    def test_opening_matches_prev_closing(self):
        r = calculate_home_loan(30_00_000, 9.0, 10)
        for i in range(1, len(r.year_wise)):
            assert abs(r.year_wise[i].opening_balance - r.year_wise[i-1].closing_balance) < 0.01

    def test_total_paid_per_year_sums_to_total(self):
        r = calculate_home_loan(30_00_000, 9.0, 10)
        summed = sum(yr.total_paid for yr in r.year_wise)
        assert abs(summed - r.total_payment) < 1

    def test_interest_in_year1_greater_than_last_year(self):
        # Early years are interest-heavy
        r = calculate_home_loan(50_00_000, 8.5, 20)
        assert r.year_wise[0].interest_paid > r.year_wise[-1].interest_paid

    def test_principal_in_last_year_greater_than_first(self):
        r = calculate_home_loan(50_00_000, 8.5, 20)
        assert r.year_wise[-1].principal_paid > r.year_wise[0].principal_paid

    def test_total_months_stored(self):
        r = calculate_home_loan(30_00_000, 9.0, 10, tenure_months=6)
        assert r.total_months == 126

    def test_zero_rate_emi_equals_principal_over_months(self):
        r = calculate_home_loan(12_00_000, 0, 10)
        assert abs(r.monthly_emi - 10_000) < 0.01

    def test_zero_rate_zero_interest(self):
        r = calculate_home_loan(12_00_000, 0, 10)
        assert abs(r.total_interest) < 1

    def test_invalid_principal_raises(self):
        with pytest.raises(ValueError):
            calculate_home_loan(0, 8.5, 20)

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError):
            calculate_home_loan(50_00_000, -1, 20)

    def test_zero_tenure_raises(self):
        with pytest.raises(ValueError):
            calculate_home_loan(50_00_000, 8.5, 0, tenure_months=0)

    def test_invalid_tenure_months_raises(self):
        with pytest.raises(ValueError):
            calculate_home_loan(50_00_000, 8.5, 5, tenure_months=12)

    def test_higher_rate_higher_emi(self):
        r_low  = calculate_home_loan(50_00_000, 7.0, 20)
        r_high = calculate_home_loan(50_00_000, 9.0, 20)
        assert r_high.monthly_emi > r_low.monthly_emi

    def test_longer_tenure_lower_emi(self):
        r_short = calculate_home_loan(50_00_000, 8.5, 15)
        r_long  = calculate_home_loan(50_00_000, 8.5, 25)
        assert r_long.monthly_emi < r_short.monthly_emi

    def test_longer_tenure_more_interest(self):
        r_short = calculate_home_loan(50_00_000, 8.5, 15)
        r_long  = calculate_home_loan(50_00_000, 8.5, 25)
        assert r_long.total_interest > r_short.total_interest


class TestFormatInr:
    def test_basic(self):
        assert format_inr(100_000) == "₹100,000.00"

    def test_decimal(self):
        assert format_inr(1234.56) == "₹1,234.56"

    def test_large_amount(self):
        assert format_inr(10_000_000) == "₹10,000,000.00"
