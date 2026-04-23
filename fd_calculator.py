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
