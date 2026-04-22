"""Fixed Deposit (FD) Investment Calculator"""

from dataclasses import dataclass
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
    year: int
    opening_balance: float
    interest_earned: float
    closing_balance: float


@dataclass
class FDResult:
    principal: float
    annual_rate: float
    tenure_years: int
    compounding: CompoundingFrequency
    maturity_amount: float
    total_interest: float
    year_wise: list[YearResult]


def calculate_fd(
    principal: float,
    annual_rate_percent: float,
    tenure_years: int,
    compounding: CompoundingFrequency = CompoundingFrequency.QUARTERLY,
) -> FDResult:
    """
    Calculate FD maturity amount using compound interest formula:
    A = P * (1 + r/n)^(n*t)

    Where n is compounding frequency per year.
    """
    if principal <= 0:
        raise ValueError("Principal must be positive")
    if annual_rate_percent <= 0:
        raise ValueError("Interest rate must be positive")
    if tenure_years < 1:
        raise ValueError("Tenure must be at least 1 year")

    r = annual_rate_percent / 100
    n = compounding.value
    year_wise = []

    balance = principal
    for year in range(1, tenure_years + 1):
        opening = balance
        closing = opening * (1 + r / n) ** n
        interest = closing - opening
        year_wise.append(YearResult(year, opening, interest, closing))
        balance = closing

    maturity = year_wise[-1].closing_balance
    return FDResult(
        principal=principal,
        annual_rate=annual_rate_percent,
        tenure_years=tenure_years,
        compounding=compounding,
        maturity_amount=maturity,
        total_interest=maturity - principal,
        year_wise=year_wise,
    )


def format_inr(amount: float) -> str:
    """Format amount in Indian number system (lakhs/crores)."""
    return f"₹{amount:,.2f}"


def print_result(result: FDResult) -> None:
    width = 65

    print("\n" + "=" * width)
    print(" FIXED DEPOSIT CALCULATOR - RESULT ".center(width, "="))
    print("=" * width)

    print(f"\n  Principal Amount   : {format_inr(result.principal)}")
    print(f"  Annual Rate        : {result.annual_rate:.2f}%")
    print(f"  Tenure             : {result.tenure_years} year(s)")
    print(f"  Compounding        : {FREQUENCY_LABELS[result.compounding]}")

    print("\n" + "-" * width)
    print(f"  {'Year':<6} {'Opening Balance':>18} {'Interest Earned':>18} {'Closing Balance':>18}")
    print("-" * width)

    for yr in result.year_wise:
        print(
            f"  {yr.year:<6} "
            f"{format_inr(yr.opening_balance):>18} "
            f"{format_inr(yr.interest_earned):>18} "
            f"{format_inr(yr.closing_balance):>18}"
        )

    print("=" * width)
    print(f"  Total Interest     : {format_inr(result.total_interest)}")
    print(f"  Maturity Amount    : {format_inr(result.maturity_amount)}")
    print("=" * width + "\n")


def get_float(prompt: str, min_val: float = 0) -> float:
    while True:
        try:
            value = float(input(prompt).replace(",", ""))
            if value <= min_val:
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


def main() -> None:
    print("\n" + "=" * 65)
    print(" FIXED DEPOSIT (FD) INVESTMENT CALCULATOR ".center(65, "="))
    print("=" * 65)

    principal = get_float("\n  Enter Principal Amount (₹): ")
    rate = get_float("  Enter Annual Interest Rate (%): ")
    tenure = get_int("  Enter Tenure (years, min 1): ", min_val=1)
    compounding = select_compounding()

    result = calculate_fd(principal, rate, tenure, compounding)
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
