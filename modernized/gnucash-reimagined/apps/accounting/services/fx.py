"""
Foreign exchange (FX) calculation services.

Implements:
- Exchange rate lookups (nearest-in-time)
- Currency conversions
- Multi-currency transaction validation

Accounting Semantics:
    Foreign exchange (FX) is the process of converting one currency to another.
    In accounting, FX is used for:
    - Multi-currency transactions (e.g., buying goods in foreign currency)
    - Foreign currency revaluation (adjusting balances at period-end)
    - Translation of foreign subsidiary financial statements

    Exchange Rate Lookup (BR-FX-001):
    Exchange rates are looked up using the "nearest-in-time" principle:
    1. Exact date match
    2. Most recent rate before the date
    3. None if no rate found

    Dual-Field Model (ADR-009):
    Each journal line has two fields:
    - amount: Quantity in the account's commodity (e.g., 10,000 USD)
    - value: Quantity in the transaction currency (e.g., 13,400 SGD)

    The exchange rate is implicit: rate = value / amount

    Trading Accounts:
    For multi-currency transactions, trading accounts are used to balance
    the commodity mismatch. For example:
    - Debit USD Bank Account (amount: 10,000 USD, value: 13,400 SGD)
    - Credit EUR Bank Account (amount: 8,500 EUR, value: 13,400 SGD)
    - Trading accounts balance the currency differences

    Realized vs Unrealized Gains/Losses:
    - Realized: Gain/loss when foreign currency is actually exchanged
    - Unrealized: Gain/loss from revaluing foreign currency balances at period-end
"""

from decimal import Decimal
from typing import Optional

from django.db.models import Q

from apps.accounting.models import Commodity, ExchangeRate


class FXService:
    """
    Service for foreign exchange calculations.

    Accounting Semantics:
        This service provides methods for:
        - Looking up exchange rates (nearest-in-time)
        - Converting amounts between currencies
        - Validating multi-currency transactions
        - Calculating realized/unrealized gains/losses
    """

    @staticmethod
    def get_exchange_rate(
        from_commodity: Commodity,
        to_commodity: Commodity,
        rate_date,
        tenant,
    ) -> Optional[ExchangeRate]:
        """
        Get exchange rate for a specific date with fallback logic.

        Accounting Semantics:
            BR-FX-001: Price lookup nearest-in-time

            Priority:
            1. Exact date match
            2. Most recent rate before the date
            3. None if no rate found

            This implements the "nearest-in-time" principle for exchange rates.
            If no rate exists for the exact transaction date, use the most recent
            prior rate. This handles weekends, holidays, and missing data gracefully.

        Args:
            from_commodity: Source commodity
            to_commodity: Target commodity
            rate_date: Date of the transaction
            tenant: Multi-tenant isolation

        Returns:
            ExchangeRate instance or None if not found
        """
        if from_commodity == to_commodity:
            # Same commodity, rate is 1:1
            return None

        return ExchangeRate.get_rate(
            from_commodity=from_commodity,
            to_commodity=to_commodity,
            rate_date=rate_date,
            tenant=tenant,
        )

    @staticmethod
    def convert_amount(
        amount: Decimal,
        from_commodity: Commodity,
        to_commodity: Commodity,
        rate_date,
        tenant,
    ) -> Decimal:
        """
        Convert an amount from one commodity to another.

        Accounting Semantics:
            Converts an amount using the exchange rate at the specified date.
            If no rate is found, returns the original amount (assumes 1:1 rate).

            The result is rounded to the target commodity's precision.

        Args:
            amount: Amount to convert
            from_commodity: Source commodity
            to_commodity: Target commodity
            rate_date: Date for exchange rate lookup
            tenant: Multi-tenant isolation

        Returns:
            Converted amount in target commodity (rounded)
        """
        if from_commodity == to_commodity:
            # Same commodity, no conversion needed
            return amount

        rate = FXService.get_exchange_rate(
            from_commodity=from_commodity,
            to_commodity=to_commodity,
            rate_date=rate_date,
            tenant=tenant,
        )

        if rate is None:
            # No rate found, return original amount (assumes 1:1)
            return amount

        converted = amount * rate.rate

        # Round to target commodity precision
        return to_commodity.round_amount(converted)

    @staticmethod
    def calculate_dual_fields(
        account_commodity: Commodity,
        transaction_commodity: Commodity,
        amount: Decimal,
        rate_date,
        tenant,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate dual-field amount/value for a journal line.

        Accounting Semantics:
            ADR-009: Dual-field multi-currency model

            Each journal line has:
            - amount: Quantity in account's commodity
            - value: Quantity in transaction currency

            This method calculates both fields given:
            - The amount in the account's commodity
            - The exchange rate at the transaction date

        Args:
            account_commodity: Account's commodity
            transaction_commodity: Transaction currency
            amount: Amount in account's commodity
            rate_date: Date for exchange rate lookup
            tenant: Multi-tenant isolation

        Returns:
            Tuple of (amount, value) where:
            - amount: In account's commodity
            - value: In transaction currency
        """
        # Amount is already in account's commodity
        amount_rounded = account_commodity.round_amount(amount)

        # Calculate value in transaction currency
        value = FXService.convert_amount(
            amount=amount_rounded,
            from_commodity=account_commodity,
            to_commodity=transaction_commodity,
            rate_date=rate_date,
            tenant=tenant,
        )

        return (amount_rounded, value)

    @staticmethod
    def validate_transaction_balance(
        lines: list[dict],
        transaction_currency: Commodity,
    ) -> bool:
        """
        Validate that a multi-currency transaction is balanced.

        Accounting Semantics:
            BR-ACCT-002: Balance checked per commodity for multi-currency

            For a transaction to be balanced:
            - Each commodity must sum to zero independently
            - Trading accounts handle cross-commodity imbalances

        Args:
            lines: List of dicts with keys: account, amount, value
            transaction_currency: Transaction currency

        Returns:
            True if balanced, False otherwise
        """
        from collections import defaultdict
        commodity_totals = defaultdict(lambda: Decimal("0.00"))

        for line in lines:
            account = line["account"]
            amount = line["amount"]
            value = line["value"]

            # Amount is in account's commodity
            commodity_totals[account.commodity.mnemonic] += amount
            # Value is in transaction currency
            commodity_totals[transaction_currency.mnemonic] += value

        # Check that each commodity sums to zero
        for commodity_code, total in commodity_totals.items():
            # Allow for rounding tolerance (0.5 cents)
            if abs(total) > Decimal("0.005"):
                return False

        return True

    @staticmethod
    def get_rate_for_date_range(
        from_commodity: Commodity,
        to_commodity: Commodity,
        start_date,
        end_date,
        tenant,
    ) -> list[ExchangeRate]:
        """
        Get all exchange rates within a date range.

        Accounting Semantics:
            This is used for period-end revaluation and reporting.
            Returns all rates between start_date and end_date.

        Args:
            from_commodity: Source commodity
            to_commodity: Target commodity
            start_date: Start of date range
            end_date: End of date range
            tenant: Multi-tenant isolation

        Returns:
            List of ExchangeRate instances within the date range
        """
        return ExchangeRate.objects.filter(
            from_commodity=from_commodity,
            to_commodity=to_commodity,
            rate_date__gte=start_date,
            rate_date__lte=end_date,
            tenant=tenant,
        ).order_by("rate_date")

    @staticmethod
    def calculate_realized_gain_loss(
        original_amount: Decimal,
        original_rate: Decimal,
        settlement_amount: Decimal,
        settlement_rate: Decimal,
        commodity: Commodity,
    ) -> Decimal:
        """
        Calculate realized gain/loss on foreign currency transaction.

        Accounting Semantics:
            Realized gain/loss occurs when a foreign currency transaction
            is settled at a different rate than the original transaction.

            Formula:
            realized_gain_loss = (settlement_rate - original_rate) * original_amount

            Example:
            - Bought goods for 1,000 EUR at rate 1.20 (recorded as $1,200)
            - Paid 1,000 EUR at rate 1.25 (paid $1,250)
            - Realized loss: (1.25 - 1.20) * 1,000 = $50

        Args:
            original_amount: Original foreign currency amount
            original_rate: Exchange rate at transaction date
            settlement_amount: Settlement foreign currency amount
            settlement_rate: Exchange rate at settlement date
            commodity: Foreign currency commodity

        Returns:
            Realized gain/loss in base currency (positive = gain, negative = loss)
        """
        original_base = original_amount * original_rate
        settlement_base = settlement_amount * settlement_rate

        gain_loss = settlement_base - original_base

        return commodity.round_amount(gain_loss)

    @staticmethod
    def calculate_unrealized_gain_loss(
        balance: Decimal,
        original_rate: Decimal,
        current_rate: Decimal,
        commodity: Commodity,
    ) -> Decimal:
        """
        Calculate unrealized gain/loss on foreign currency balance.

        Accounting Semantics:
            Unrealized gain/loss occurs when a foreign currency balance
            is revalued at period-end using the current exchange rate.

            Formula:
            unrealized_gain_loss = (current_rate - original_rate) * balance

            Example:
            - Foreign bank account: 1,000 EUR
            - Original rate: 1.20 (recorded as $1,200)
            - Current rate: 1.25 (now worth $1,250)
            - Unrealized gain: (1.25 - 1.20) * 1,000 = $50

        Args:
            balance: Foreign currency balance
            original_rate: Exchange rate when balance was recorded
            current_rate: Current exchange rate (at period-end)
            commodity: Foreign currency commodity

        Returns:
            Unrealized gain/loss in base currency (positive = gain, negative = loss)
        """
        original_base = balance * original_rate
        current_base = balance * current_rate

        gain_loss = current_base - original_base

        return commodity.round_amount(gain_loss)
