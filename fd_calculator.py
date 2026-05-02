"""Fixed Deposit (FD) Investment Calculator"""

from dataclasses import dataclass, field
from enum import Enum


class CompoundingFrequency(Enum):
    MONTHLY = 12
    QUARTERLY = 4
    HALF_YEARLY = 2
    YEARLY = 1


FREQUENCY_LABELS = {
    CompoundingFrequency.MONTHLY: "Monthly",
    CompoundingFrequency.QUARTERLY: "Quarterly",
    CompoundingFrequency.HALF_YEARLY: "Half-Yearly",
    CompoundingFrequency.YEARLY: "Yearly",
}


@dataclass
class YearResult:
    year: int           # 0 = partial-month row
    opening_balance: float
    interest_earned: float
    closing_balance: float
    topup: float = 0.0
    period_months: int = 12   # < 12 for the trailing partial row


@dataclass
class FDResult:
    principal: float
    annual_rate: float
    tenure_years: int
    tenure_months: int          # extra months beyond whole years
    compounding: CompoundingFrequency
    maturity_amount: float
    total_interest: float
    year_wise: list[YearResult]
    total_topups: float = 0.0


def calculate_fd(
    principal: float,
    annual_rate_percent: float,
    tenure_years: int,
    compounding: CompoundingFrequency = CompoundingFrequency.QUARTERLY,
    tenure_months: int = 0,
) -> FDResult:
    """A = P * (1 + r/n)^(n*t), with optional extra months."""
    return calculate_fd_with_topups(
        principal, annual_rate_percent, tenure_years,
        [0.0] * tenure_years, compounding, tenure_months,
    )


def calculate_fd_with_topups(
    principal: float,
    annual_rate_percent: float,
    tenure_years: int,
    topups: list[float],
    compounding: CompoundingFrequency = CompoundingFrequency.QUARTERLY,
    tenure_months: int = 0,
) -> FDResult:
    """
    FD with optional annual top-ups and optional extra months.

    topups: list of length tenure_years; topups[i] is added before year i+1 compounds.
    tenure_months: additional months (0–11) compounded after the whole years.
    """
    if principal <= 0:
        raise ValueError("Principal must be positive")
    if annual_rate_percent <= 0:
        raise ValueError("Interest rate must be positive")
    if tenure_years < 1 and tenure_months < 1:
        raise ValueError("Tenure must be at least 1 month")
    if tenure_years > 0 and len(topups) != tenure_years:
        raise ValueError("topups length must equal tenure_years")
    if any(t < 0 for t in topups):
        raise ValueError("Top-up amounts must be non-negative")
    if not (0 <= tenure_months <= 11):
        raise ValueError("tenure_months must be between 0 and 11")

    r = annual_rate_percent / 100
    n = compounding.value
    year_wise = []
    balance = principal

    for year in range(1, tenure_years + 1):
        topup = topups[year - 1]
        opening = balance + topup
        closing = opening * (1 + r / n) ** n
        interest = closing - opening
        year_wise.append(YearResult(year, opening, interest, closing, topup, 12))
        balance = closing

    if tenure_months > 0:
        opening = balance
        closing = opening * (1 + r / n) ** (tenure_months * n / 12)
        interest = closing - opening
        year_wise.append(YearResult(0, opening, interest, closing, 0.0, tenure_months))
        balance = closing

    maturity = year_wise[-1].closing_balance
    total_topups = sum(topups)
    return FDResult(
        principal=principal,
        annual_rate=annual_rate_percent,
        tenure_years=tenure_years,
        tenure_months=tenure_months,
        compounding=compounding,
        maturity_amount=maturity,
        total_interest=maturity - principal - total_topups,
        year_wise=year_wise,
        total_topups=total_topups,
    )


@dataclass
class FVYearResult:
    label: str              # "Yr 1", "+6m", etc.
    nominal_value: float    # investment value (grows with return rate)
    real_value: float       # purchasing power in today's money
    amount_needed: float    # PV × (1+inf)^elapsed — needed to match today's purchasing power


@dataclass
class FVResult:
    present_value: float
    return_rate: float
    inflation_rate: float
    tenure_years: int
    tenure_months: int
    nominal_fv: float
    real_fv: float
    amount_needed_fv: float   # PV × (1+inf)^total_tenure (inflation-only mode hero metric)
    total_growth: float
    inflation_loss: float     # nominal_fv - real_fv
    year_wise: list[FVYearResult]


def calculate_future_value(
    present_value: float,
    annual_return_percent: float,
    tenure_years: int,
    inflation_percent: float = 0.0,
    tenure_months: int = 0,
) -> FVResult:
    """
    Future value supporting three modes:
      - Return only  (inflation_percent=0): shows nominal growth.
      - Inflation only (annual_return_percent=0): shows purchasing-power erosion
        and the amount needed to maintain today's buying power.
      - Both: shows nominal FV vs real (inflation-adjusted) value.

    At least one of annual_return_percent or inflation_percent must be > 0.
    """
    if present_value <= 0:
        raise ValueError("Present value must be positive")
    if annual_return_percent < 0:
        raise ValueError("Return rate must be non-negative")
    if inflation_percent < 0:
        raise ValueError("Inflation rate must be non-negative")
    if annual_return_percent == 0 and inflation_percent == 0:
        raise ValueError("Enter at least a return rate or an inflation rate")
    if not (0 <= tenure_months <= 11):
        raise ValueError("tenure_months must be between 0 and 11")
    if tenure_years == 0 and tenure_months == 0:
        raise ValueError("Tenure must be at least 1 month")

    r   = annual_return_percent / 100
    inf = inflation_percent / 100
    year_wise = []
    nominal   = present_value
    elapsed   = 0.0

    for y in range(1, tenure_years + 1):
        if r > 0:
            nominal = nominal * (1 + r)
        elapsed = float(y)
        real   = nominal / (1 + inf) ** elapsed if inf > 0 else nominal
        needed = present_value * (1 + inf) ** elapsed if inf > 0 else 0.0
        year_wise.append(FVYearResult(f"Yr {y}", nominal, real, needed))

    if tenure_months > 0:
        frac = tenure_months / 12
        if r > 0:
            nominal = nominal * (1 + r) ** frac
        elapsed += frac
        real   = nominal / (1 + inf) ** elapsed if inf > 0 else nominal
        needed = present_value * (1 + inf) ** elapsed if inf > 0 else 0.0
        year_wise.append(FVYearResult(f"+{tenure_months}m", nominal, real, needed))

    last = year_wise[-1]
    return FVResult(
        present_value=present_value,
        return_rate=annual_return_percent,
        inflation_rate=inflation_percent,
        tenure_years=tenure_years,
        tenure_months=tenure_months,
        nominal_fv=nominal,
        real_fv=last.real_value,
        amount_needed_fv=last.amount_needed,
        total_growth=nominal - present_value,
        inflation_loss=nominal - last.real_value,
        year_wise=year_wise,
    )


@dataclass
class OptionsResult:
    option_type: str        # 'call' or 'put'
    current_price: float
    strike_price: float
    premium: float
    intrinsic_value: float
    extrinsic_value: float  # time value = max(0, premium - intrinsic)
    breakeven: float
    moneyness: str          # 'ITM', 'ATM', 'OTM'


def calculate_options_value(
    option_type: str,
    current_price: float,
    strike_price: float,
    premium: float,
) -> OptionsResult:
    """
    Intrinsic value  = max(0, S-K) for call, max(0, K-S) for put.
    Extrinsic value  = max(0, premium - intrinsic)  (time value).
    Breakeven        = K + premium (call) or K - premium (put).
    """
    if option_type not in ('call', 'put'):
        raise ValueError("option_type must be 'call' or 'put'")
    if current_price <= 0:
        raise ValueError("Current price must be positive")
    if strike_price <= 0:
        raise ValueError("Strike price must be positive")
    if premium <= 0:
        raise ValueError("Premium must be positive")

    is_call = option_type == 'call'
    intrinsic  = max(0.0, current_price - strike_price if is_call else strike_price - current_price)
    extrinsic  = max(0.0, premium - intrinsic)
    breakeven  = strike_price + premium if is_call else strike_price - premium

    diff_pct = abs(current_price - strike_price) / strike_price * 100
    if diff_pct < 0.5:
        moneyness = 'ATM'
    elif (is_call and current_price > strike_price) or (not is_call and current_price < strike_price):
        moneyness = 'ITM'
    else:
        moneyness = 'OTM'

    return OptionsResult(
        option_type=option_type,
        current_price=current_price,
        strike_price=strike_price,
        premium=premium,
        intrinsic_value=intrinsic,
        extrinsic_value=extrinsic,
        breakeven=breakeven,
        moneyness=moneyness,
    )


@dataclass
class DCFYearResult:
    year: int
    projected_cf: float
    discount_factor: float
    present_value: float


@dataclass
class DCFResult:
    initial_cf: float
    growth_rate: float
    terminal_growth_rate: float
    discount_rate: float
    projection_years: int
    pv_cash_flows: float
    terminal_value: float
    pv_terminal_value: float
    intrinsic_value: float
    current_price: float        # 0 if not provided
    margin_of_safety_pct: float # positive = undervalued, None if no price given
    year_wise: list[DCFYearResult]


def calculate_dcf(
    initial_cash_flow: float,
    growth_rate_percent: float,
    terminal_growth_rate_percent: float,
    discount_rate_percent: float,
    projection_years: int = 10,
    current_price: float = 0.0,
) -> DCFResult:
    """
    Discounted Cash Flow valuation.

    Projects cash flows for `projection_years` at `growth_rate_percent`,
    computes terminal value using Gordon Growth Model, discounts everything
    at `discount_rate_percent`. Intrinsic value = PV(CFs) + PV(TV).
    Margin of Safety = (intrinsic - market_price) / intrinsic * 100.
    """
    if initial_cash_flow <= 0:
        raise ValueError("Initial cash flow must be positive")
    if growth_rate_percent <= 0:
        raise ValueError("Growth rate must be positive")
    if discount_rate_percent <= 0:
        raise ValueError("Discount rate must be positive")
    if projection_years < 1:
        raise ValueError("Projection years must be at least 1")
    if discount_rate_percent <= terminal_growth_rate_percent:
        raise ValueError("Discount rate must be greater than terminal growth rate")
    if terminal_growth_rate_percent < 0:
        raise ValueError("Terminal growth rate must be non-negative")
    if current_price < 0:
        raise ValueError("Current price must be non-negative")

    r   = discount_rate_percent / 100
    g   = growth_rate_percent / 100
    gt  = terminal_growth_rate_percent / 100

    year_wise   = []
    cf          = initial_cash_flow
    total_pv_cf = 0.0

    for y in range(1, projection_years + 1):
        cf  = cf * (1 + g)
        df  = 1 / (1 + r) ** y
        pv  = cf * df
        total_pv_cf += pv
        year_wise.append(DCFYearResult(y, cf, df, pv))

    terminal_value    = cf * (1 + gt) / (r - gt)
    pv_terminal       = terminal_value / (1 + r) ** projection_years
    intrinsic_value   = total_pv_cf + pv_terminal

    mos = (intrinsic_value - current_price) / intrinsic_value * 100 if current_price > 0 else 0.0

    return DCFResult(
        initial_cf=initial_cash_flow,
        growth_rate=growth_rate_percent,
        terminal_growth_rate=terminal_growth_rate_percent,
        discount_rate=discount_rate_percent,
        projection_years=projection_years,
        pv_cash_flows=total_pv_cf,
        terminal_value=terminal_value,
        pv_terminal_value=pv_terminal,
        intrinsic_value=intrinsic_value,
        current_price=current_price,
        margin_of_safety_pct=mos,
        year_wise=year_wise,
    )


# ── Income Tax Calculator (FY 2025-26) ──────────────────────────

NEW_TAX_SLABS: list[tuple[float, float]] = [
    (400_000,    0.00),
    (800_000,    0.05),
    (1_200_000,  0.10),
    (1_600_000,  0.15),
    (2_000_000,  0.20),
    (2_400_000,  0.25),
    (float("inf"), 0.30),
]

OLD_TAX_SLABS: list[tuple[float, float]] = [
    (250_000,    0.00),
    (500_000,    0.05),
    (1_000_000,  0.20),
    (float("inf"), 0.30),
]


@dataclass
class TaxSlabResult:
    slab_from: float
    slab_to: float
    rate: float
    income_in_slab: float
    tax_in_slab: float


@dataclass
class TaxResult:
    regime: str               # 'new' or 'old'
    gross_income: float
    standard_deduction: float
    other_deductions: float   # 80C + 80D + HRA + other (old regime only)
    taxable_income: float
    slab_tax: float
    rebate_87a: float
    income_tax: float         # after rebate
    surcharge_rate: float
    surcharge: float
    cess: float
    total_tax: float
    effective_rate_pct: float
    monthly_inhand: float
    slab_breakdown: list[TaxSlabResult]


def _slab_tax(taxable: float, slabs: list[tuple[float, float]]) -> tuple[float, list[TaxSlabResult]]:
    tax, prev, breakdown = 0.0, 0.0, []
    for limit, rate in slabs:
        if taxable <= prev:
            break
        in_slab = min(taxable, limit) - prev
        slab_t  = in_slab * rate
        tax    += slab_t
        breakdown.append(TaxSlabResult(prev, min(taxable, limit), rate, in_slab, slab_t))
        prev = limit
        if taxable <= limit:
            break
    return tax, breakdown


def _surcharge_rate(taxable: float, new_regime: bool) -> float:
    if taxable <= 5_000_000:   return 0.00
    if taxable <= 10_000_000:  return 0.10
    if taxable <= 20_000_000:  return 0.15
    if taxable <= 50_000_000:  return 0.25
    return 0.25 if new_regime else 0.37   # new regime caps surcharge at 25%


def calculate_tax(
    gross_income: float,
    regime: str = 'new',
    is_salaried: bool = True,
    deduction_80c: float = 0.0,
    deduction_80d: float = 0.0,
    hra_exemption: float = 0.0,
    other_deductions: float = 0.0,
) -> TaxResult:
    """
    Calculate income tax under new or old regime (FY 2025-26).

    New regime: standard deduction ₹75,000 (salaried); 87A rebate up to
    ₹60,000 for taxable income ≤ ₹12,00,000; surcharge capped at 25%.

    Old regime: standard deduction ₹50,000 (salaried); 80C/80D/HRA and
    other deductions applied; 87A rebate ₹12,500 for taxable ≤ ₹5,00,000.
    """
    if regime not in ('new', 'old'):
        raise ValueError("regime must be 'new' or 'old'")
    if gross_income <= 0:
        raise ValueError("Gross income must be positive")
    if any(d < 0 for d in [deduction_80c, deduction_80d, hra_exemption, other_deductions]):
        raise ValueError("Deductions must be non-negative")

    is_new = regime == 'new'
    std_ded      = (75_000 if is_new else 50_000) if is_salaried else 0.0
    ded_80c      = min(deduction_80c, 150_000)    # 80C cap
    old_ded      = ded_80c + deduction_80d + hra_exemption + other_deductions
    other_ded    = 0.0 if is_new else old_ded
    total_ded    = std_ded + other_ded
    taxable      = max(0.0, gross_income - total_ded)

    slabs        = NEW_TAX_SLABS if is_new else OLD_TAX_SLABS
    slab_t, bkd  = _slab_tax(taxable, slabs)

    rebate = 0.0
    if is_new  and taxable <= 1_200_000: rebate = min(slab_t, 60_000)
    if not is_new and taxable <= 500_000: rebate = min(slab_t, 12_500)

    income_tax   = max(0.0, slab_t - rebate)
    sr_rate      = _surcharge_rate(taxable, is_new)
    surcharge    = income_tax * sr_rate
    cess         = (income_tax + surcharge) * 0.04
    total_tax    = income_tax + surcharge + cess
    eff_rate     = total_tax / gross_income * 100
    inhand       = (gross_income - total_tax) / 12

    return TaxResult(
        regime=regime,
        gross_income=gross_income,
        standard_deduction=std_ded,
        other_deductions=other_ded,
        taxable_income=taxable,
        slab_tax=slab_t,
        rebate_87a=rebate,
        income_tax=income_tax,
        surcharge_rate=sr_rate,
        surcharge=surcharge,
        cess=cess,
        total_tax=total_tax,
        effective_rate_pct=eff_rate,
        monthly_inhand=inhand,
        slab_breakdown=bkd,
    )


# ── Home Loan EMI Calculator ─────────────────────────────────────

@dataclass
class LoanYearResult:
    year: int
    opening_balance: float
    principal_paid: float
    interest_paid: float
    total_paid: float
    closing_balance: float


@dataclass
class LoanResult:
    principal: float
    annual_rate: float
    total_months: int
    monthly_emi: float
    total_payment: float
    total_interest: float
    year_wise: list[LoanYearResult]


def calculate_home_loan(
    principal: float,
    annual_rate_percent: float,
    tenure_years: int,
    tenure_months: int = 0,
) -> LoanResult:
    """
    Calculate home loan EMI and year-wise amortization schedule.

    EMI = P × r × (1+r)^n / ((1+r)^n − 1)
    where r = monthly interest rate, n = total months.
    Zero-interest edge case: EMI = P / n.
    """
    if principal <= 0:
        raise ValueError("Principal must be positive")
    if annual_rate_percent < 0:
        raise ValueError("Interest rate must be non-negative")
    if tenure_years == 0 and tenure_months == 0:
        raise ValueError("Tenure must be at least 1 month")
    if not (0 <= tenure_months <= 11):
        raise ValueError("tenure_months must be between 0 and 11")

    n = tenure_years * 12 + tenure_months
    r = annual_rate_percent / 12 / 100

    if r == 0:
        emi = principal / n
    else:
        emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)

    balance   = principal
    year_wise = []
    month_num = 0

    for year in range(1, tenure_years + 2):   # +1 handles trailing months
        months_in_year = min(12, n - (year - 1) * 12)
        if months_in_year <= 0:
            break

        opening    = balance
        y_principal = 0.0
        y_interest  = 0.0

        for _ in range(months_in_year):
            month_num  += 1
            interest    = balance * r
            principal_p = min(emi - interest, balance)
            y_principal += principal_p
            y_interest  += interest
            balance     -= principal_p
            if balance < 0.005:
                balance = 0.0

        year_wise.append(LoanYearResult(
            year          = year,
            opening_balance = opening,
            principal_paid  = y_principal,
            interest_paid   = y_interest,
            total_paid      = y_principal + y_interest,
            closing_balance = balance,
        ))

        if balance == 0:
            break

    total_payment   = emi * n
    total_interest  = total_payment - principal

    return LoanResult(
        principal      = principal,
        annual_rate    = annual_rate_percent,
        total_months   = n,
        monthly_emi    = emi,
        total_payment  = total_payment,
        total_interest = total_interest,
        year_wise      = year_wise,
    )


# ── Car Loan EMI Calculator ──────────────────────────────────────

@dataclass
class CarLoanResult:
    car_price: float
    down_payment: float
    loan_amount: float
    annual_rate: float
    total_months: int
    monthly_emi: float
    total_loan_payment: float   # EMI × n
    total_interest: float
    total_cost: float           # down_payment + total_loan_payment
    year_wise: list[LoanYearResult]


def calculate_car_loan(
    car_price: float,
    down_payment: float,
    annual_rate_percent: float,
    tenure_years: int,
    tenure_months: int = 0,
) -> CarLoanResult:
    """
    Calculate car loan EMI and year-wise amortization schedule.

    loan_amount = car_price - down_payment
    EMI formula same as home loan: P × r(1+r)^n / ((1+r)^n - 1)
    """
    if car_price <= 0:
        raise ValueError("Car price must be positive")
    if down_payment < 0:
        raise ValueError("Down payment cannot be negative")
    if down_payment >= car_price:
        raise ValueError("Down payment must be less than car price")
    if annual_rate_percent < 0:
        raise ValueError("Interest rate must be non-negative")
    if tenure_years == 0 and tenure_months == 0:
        raise ValueError("Tenure must be at least 1 month")
    if not (0 <= tenure_months <= 11):
        raise ValueError("tenure_months must be between 0 and 11")

    principal = car_price - down_payment
    n = tenure_years * 12 + tenure_months
    r = annual_rate_percent / 12 / 100

    if r == 0:
        emi = principal / n
    else:
        emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)

    balance   = principal
    year_wise = []

    for year in range(1, tenure_years + 2):
        months_in_year = min(12, n - (year - 1) * 12)
        if months_in_year <= 0:
            break

        opening     = balance
        y_principal = 0.0
        y_interest  = 0.0

        for _ in range(months_in_year):
            interest    = balance * r
            principal_p = min(emi - interest, balance)
            y_principal += principal_p
            y_interest  += interest
            balance     -= principal_p
            if balance < 0.005:
                balance = 0.0

        year_wise.append(LoanYearResult(
            year            = year,
            opening_balance = opening,
            principal_paid  = y_principal,
            interest_paid   = y_interest,
            total_paid      = y_principal + y_interest,
            closing_balance = balance,
        ))

        if balance == 0:
            break

    total_loan_payment = emi * n
    total_interest     = total_loan_payment - principal

    return CarLoanResult(
        car_price          = car_price,
        down_payment       = down_payment,
        loan_amount        = principal,
        annual_rate        = annual_rate_percent,
        total_months       = n,
        monthly_emi        = emi,
        total_loan_payment = total_loan_payment,
        total_interest     = total_interest,
        total_cost         = down_payment + total_loan_payment,
        year_wise          = year_wise,
    )


# ── Rent Increment Calculator ────────────────────────────────────

@dataclass
class RentYearResult:
    year: int
    monthly_rent: float
    annual_rent: float
    cumulative_paid: float


@dataclass
class RentResult:
    initial_monthly_rent: float
    annual_increase_pct: float
    years: int
    final_monthly_rent: float
    total_paid: float
    rent_growth_pct: float
    year_wise: list[RentYearResult]


def calculate_rent(
    initial_monthly_rent: float,
    annual_increase_pct: float,
    years: int,
) -> RentResult:
    """
    Calculate year-wise rent given an annual percentage increase.

    monthly_rent(y) = initial × (1 + pct/100)^(y-1)
    """
    if initial_monthly_rent <= 0:
        raise ValueError("Initial monthly rent must be positive")
    if annual_increase_pct < 0:
        raise ValueError("Annual increase percentage cannot be negative")
    if years <= 0:
        raise ValueError("Number of years must be at least 1")

    year_wise: list[RentYearResult] = []
    cumulative = 0.0

    for y in range(1, years + 1):
        monthly = initial_monthly_rent * (1 + annual_increase_pct / 100) ** (y - 1)
        annual  = monthly * 12
        cumulative += annual
        year_wise.append(RentYearResult(
            year            = y,
            monthly_rent    = monthly,
            annual_rent     = annual,
            cumulative_paid = cumulative,
        ))

    final_monthly = year_wise[-1].monthly_rent
    growth_pct    = (final_monthly - initial_monthly_rent) / initial_monthly_rent * 100

    return RentResult(
        initial_monthly_rent = initial_monthly_rent,
        annual_increase_pct  = annual_increase_pct,
        years                = years,
        final_monthly_rent   = final_monthly,
        total_paid           = cumulative,
        rent_growth_pct      = growth_pct,
        year_wise            = year_wise,
    )


# ── Investment Returns (Compound Interest) Calculator ───────────

@dataclass
class RoiYearResult:
    year: int
    contribution: float
    opening_balance: float    # after this year's contribution, before growth
    interest_earned: float
    closing_balance: float
    total_invested: float     # cumulative invested up to and including this year


@dataclass
class RoiResult:
    initial_investment: float
    annual_investment: float
    annual_return_pct: float
    years: int
    future_value: float
    total_invested: float
    total_return: float
    wealth_multiplier: float
    effective_cagr_pct: float
    year_wise: list[RoiYearResult]


def calculate_roi(
    initial_investment: float,
    annual_investment: float,
    annual_return_pct: float,
    years: int,
) -> RoiResult:
    """
    Compound investment returns with optional yearly contributions.

    Convention: contributions are made at the start of each year (annuity-due),
    so each contribution earns the full year's return.

    closing_y = (closing_{y-1} + annual) × (1 + r)
    opening of year 1 = initial + annual
    """
    if initial_investment < 0 or annual_investment < 0:
        raise ValueError("Investment amounts cannot be negative")
    if initial_investment == 0 and annual_investment == 0:
        raise ValueError("At least one of initial or annual investment must be positive")
    if annual_return_pct < 0:
        raise ValueError("Annual return rate cannot be negative")
    if years <= 0:
        raise ValueError("Number of years must be at least 1")

    r = annual_return_pct / 100
    balance  = initial_investment
    invested = initial_investment
    year_wise: list[RoiYearResult] = []

    for y in range(1, years + 1):
        opening   = balance + annual_investment
        invested += annual_investment
        closing   = opening * (1 + r)
        interest  = closing - opening
        year_wise.append(RoiYearResult(
            year            = y,
            contribution    = annual_investment,
            opening_balance = opening,
            interest_earned = interest,
            closing_balance = closing,
            total_invested  = invested,
        ))
        balance = closing

    future_value      = balance
    total_return      = future_value - invested
    wealth_multiplier = future_value / invested if invested > 0 else 0.0
    effective_cagr    = ((future_value / invested) ** (1 / years) - 1) * 100 if invested > 0 else 0.0

    return RoiResult(
        initial_investment = initial_investment,
        annual_investment  = annual_investment,
        annual_return_pct  = annual_return_pct,
        years              = years,
        future_value       = future_value,
        total_invested     = invested,
        total_return       = total_return,
        wealth_multiplier  = wealth_multiplier,
        effective_cagr_pct = effective_cagr,
        year_wise          = year_wise,
    )


def format_inr(amount: float) -> str:
    return f"₹{amount:,.2f}"


def print_result(result: FDResult) -> None:
    has_topups = result.total_topups > 0
    width = 78 if has_topups else 65

    print("\n" + "=" * width)
    print(" FIXED DEPOSIT CALCULATOR - RESULT ".center(width, "="))
    print("=" * width)

    tenure_str = f"{result.tenure_years} yr" if result.tenure_years else ""
    if result.tenure_months:
        tenure_str += f" {result.tenure_months} mo"
    print(f"\n  Principal Amount   : {format_inr(result.principal)}")
    print(f"  Annual Rate        : {result.annual_rate:.2f}%")
    print(f"  Tenure             : {tenure_str.strip()}")
    print(f"  Compounding        : {FREQUENCY_LABELS[result.compounding]}")
    if has_topups:
        print(f"  Total Top-ups      : {format_inr(result.total_topups)}")
        print(f"  Total Invested     : {format_inr(result.principal + result.total_topups)}")

    print("\n" + "-" * width)
    if has_topups:
        print(
            f"  {'Year':<6} {'Top-up':>12} {'Opening Balance':>18} "
            f"{'Interest Earned':>18} {'Closing Balance':>18}"
        )
    else:
        print(f"  {'Year':<6} {'Opening Balance':>18} {'Interest Earned':>18} {'Closing Balance':>18}")
    print("-" * width)

    for yr in result.year_wise:
        label = f"Yr {yr.year}" if yr.period_months == 12 else f"+{yr.period_months}m"
        if has_topups:
            topup_str = f"+{format_inr(yr.topup)}" if yr.topup > 0 else "—"
            print(
                f"  {label:<8} {topup_str:>12} "
                f"{format_inr(yr.opening_balance):>18} "
                f"{format_inr(yr.interest_earned):>18} "
                f"{format_inr(yr.closing_balance):>18}"
            )
        else:
            print(
                f"  {label:<8} "
                f"{format_inr(yr.opening_balance):>18} "
                f"{format_inr(yr.interest_earned):>18} "
                f"{format_inr(yr.closing_balance):>18}"
            )

    print("=" * width)
    print(f"  Total Interest     : {format_inr(result.total_interest)}")
    print(f"  Maturity Amount    : {format_inr(result.maturity_amount)}")
    print("=" * width + "\n")


def get_float(prompt: str, min_val: float = 0, allow_zero: bool = False) -> float:
    while True:
        try:
            value = float(input(prompt).replace(",", ""))
            if allow_zero and value < 0:
                print("  Please enter a non-negative value.")
                continue
            if not allow_zero and value <= min_val:
                print(f"  Please enter a value greater than {min_val}.")
                continue
            return value
        except ValueError:
            print("  Invalid input. Please enter a number.")


def get_int(prompt: str, min_val: int = 1) -> int:
    while True:
        try:
            value = int(input(prompt))
            if value < min_val:
                print(f"  Please enter a value of at least {min_val}.")
                continue
            return value
        except ValueError:
            print("  Invalid input. Please enter a whole number.")


def select_compounding() -> CompoundingFrequency:
    options = list(CompoundingFrequency)
    print("\n  Compounding frequency options:")
    for i, freq in enumerate(options, 1):
        print(f"    {i}. {FREQUENCY_LABELS[freq]}")
    while True:
        try:
            choice = int(input("  Select option (default 2 = Quarterly): ") or "2")
            if 1 <= choice <= len(options):
                return options[choice - 1]
            print(f"  Enter a number between 1 and {len(options)}.")
        except ValueError:
            print("  Invalid input.")


def get_tenure() -> tuple[int, int]:
    """Return (years, months) with at least 1 month total."""
    while True:
        years = get_int("  Enter Tenure - Years (0 for months only): ", min_val=0)
        try:
            mo_raw = input("  Additional Months (0-11, Enter = 0): ").strip()
            months = int(mo_raw) if mo_raw else 0
        except ValueError:
            print("  Invalid months. Try again.")
            continue
        if not (0 <= months <= 11):
            print("  Months must be between 0 and 11.")
            continue
        if years == 0 and months == 0:
            print("  Tenure must be at least 1 month. Try again.")
            continue
        return years, months


def collect_topups(tenure: int) -> list[float]:
    print(f"\n  Enter top-up amount for each year (press Enter to skip / enter 0 for none):")
    topups = []
    for year in range(1, tenure + 1):
        amount = get_float(f"    Year {year} top-up (₹): ", allow_zero=True)
        topups.append(amount)
    return topups


def main() -> None:
    print("\n" + "=" * 65)
    print(" FIXED DEPOSIT (FD) INVESTMENT CALCULATOR ".center(65, "="))
    print("=" * 65)

    principal = get_float("\n  Enter Principal Amount (₹): ")
    rate = get_float("  Enter Annual Interest Rate (%): ")
    tenure, extra_months = get_tenure()
    compounding = select_compounding()

    print("\n  Would you like to add annual top-ups?")
    print("  (Top-up = additional amount invested at the start of each year)")
    use_topups = input("  Add top-ups? (y/n, default n): ").strip().lower() == "y"

    if use_topups:
        topups = collect_topups(tenure)
        result = calculate_fd_with_topups(principal, rate, tenure, topups, compounding, extra_months)
    else:
        result = calculate_fd(principal, rate, tenure, compounding, extra_months)

    print_result(result)

    while True:
        again = input("  Calculate another FD? (y/n): ").strip().lower()
        if again == "y":
            main()
            break
        elif again == "n":
            print("\n  Thank you for using FD Calculator!\n")
            break


if __name__ == "__main__":
    main()
