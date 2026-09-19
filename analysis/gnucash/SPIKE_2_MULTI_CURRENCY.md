# Spike 2: Multi-Currency Accounting Semantics

**Version:** 1.0  
**Date:** 2026-09-19  
**Status:** Research Complete — Ready for Design Review  
**Spike Lead:** Architecture Team

---

## Executive Summary

This spike investigates GnuCash's multi-currency implementation and designs a clean target model for an SME cloud accounting product. The research reveals that GnuCash uses a dual-field approach (`amount` vs `value`) where:
- **amount** = quantity in the account's commodity
- **value** = quantity in the transaction's balancing currency

GnuCash supports two balancing modes:
1. **Without trading accounts** (simpler): All splits must balance in the transaction currency
2. **With trading accounts** (complex): Per-commodity balancing via special trading accounts

For the FVA platform, we recommend **hiding trading-account mechanics from users** and implementing **automatic system-managed FX accounting** with explicit realized/unrealized FX journal entries. This preserves accounting correctness while delivering modern UX.

---

## Table of Contents

1. [Research Findings: GnuCash Implementation](#1-research-findings-gnucash-implementation)
2. [Semantic Model: 16 Areas](#2-semantic-model-16-areas)
3. [Worked Examples](#3-worked-examples)
4. [Concrete Model Recommendation](#4-concrete-model-recommendation)
5. [Migration Strategy](#5-migration-strategy)
6. [Recommendations & Next Steps](#6-recommendations--next-steps)

---

## 1. Research Findings: GnuCash Implementation

### 1.1 Core Data Model: Amount vs Value

**Source:** `libgnucash/engine/Split.h` (lines 225-231)

```
Split Structure:
├─ amount: quantity in account's commodity (e.g., USD 10,000)
├─ value: quantity in transaction's balancing currency (e.g., SGD 13,400)
├─ account: points to Account with its own commodity
└─ parent: points to Transaction with common_currency
```

**Key Insight:**
- `amount` answers: "How many units of the account's commodity?"
- `value` answers: "How many units of the transaction's currency is this worth?"
- The ratio `value / amount` is the implicit exchange rate

**Example:**
```
Account: Accounts Receivable (USD)
Transaction Currency: SGD
Split:
  amount = 10,000 USD
  value = 13,400 SGD
  implicit rate = 13,400 / 10,000 = 1.34 SGD/USD
```

### 1.2 Transaction Structure

**Source:** `libgnucash/engine/Transaction.h` (lines 22-53), `Transaction.cpp`

```
Transaction Structure:
├─ date_posted: when transaction occurred
├─ date_entered: when recorded
├─ date_due: payment deadline
├─ description: narrative
├─ common_currency: the balancing currency (all values sum to zero in this)
├─ splits: list of Split objects
└─ is_balanced: sum(values) == 0
```

**Critical Rule:**
- All `value` fields must sum to zero in the transaction's `common_currency`
- `amount` fields balance per-account-commodity only when using trading accounts

### 1.3 Trading Accounts

**Source:** `libgnucash/engine/Scrub.cpp` (lines 637-782), `Transaction.cpp` (lines 969-1121)

**Purpose:**
Trading accounts are special accounts (type `ACCT_TYPE_TRADING`) that allow multi-currency transactions to balance per-commodity rather than in aggregate.

**How They Work:**

Without Trading Accounts:
```
Transaction: Transfer USD 100 to EUR account
Split 1: Bank-USD    amount=-100 USD   value=-134 SGD
Split 2: Bank-EUR    amount=+85 EUR    value=+134 SGD
Balanced? YES (values sum to 0 in SGD)
```

With Trading Accounts:
```
Transaction: Transfer USD 100 to EUR account
Split 1: Bank-USD       amount=-100 USD   value=-134 SGD
Split 2: Trading-USD    amount=+100 USD   value=+134 SGD
Split 3: Trading-EUR    amount=-85 EUR    value=-134 SGD
Split 4: Bank-EUR       amount=+85 EUR    value=+134 SGD
Balanced? YES (per-commodity AND in aggregate)
```

**Trading Account Benefits:**
1. Explicit FX gain/loss tracking
2. Per-commodity balance verification
3. Clear audit trail for currency conversions

**Trading Account Drawbacks:**
1. Complex for end users
2. Requires special "scrubbing" logic to maintain
3. Obscures the economic substance

### 1.4 Exchange Rate Storage

**Source:** `libgnucash/engine/gnc-pricedb.cpp`

```
GNCPrice Structure:
├─ commodity: what is being priced (e.g., USD)
├─ currency: what it's priced in (e.g., SGD)
├─ date: when this price is effective
├─ value: the price (e.g., 1.34)
├─ source: user:price-editor, Finance::Quote, etc.
└─ type: optional classification
```

**Key Features:**
- Historical prices supported (time-series)
- Multiple sources (manual, auto-fetched, transaction-implied)
- Lookup: "nearest price in time" for a given commodity/currency pair
- Used for reporting, revaluation, and FX calculations

### 1.5 Invoice Multi-Currency Posting

**Source:** `libgnucash/engine/gncInvoice.c` (lines 1442-1733)

**Invoice Structure:**
```
GncInvoice:
├─ currency: document currency (e.g., USD)
├─ entries: line items (quantities, prices in document currency)
├─ posted_acc: receivable/payable account
├─ posted_txn: the journal transaction
└─ posted_lot: for tracking payments
```

**Posting Logic:**

1. Create transaction with `currency = invoice->currency`
2. For each entry:
   - Calculate value in invoice currency
   - Create split to expense/asset account
   - Set `amount` and `value` using `xaccSplitSetBaseValue`
3. Create balancing split to receivable/payable account
4. Transaction balances in invoice currency

**Example:**
```
Invoice: USD 10,000 (entity base: SGD, rate 1.34)

Transaction (currency: USD):
  Split 1: Expense
    amount = 10,000 USD
    value = 10,000 USD
  Split 2: Accounts Receivable
    amount = -10,000 USD
    value = -10,000 USD

Result: AR shows USD 10,000, but reports convert to SGD using price db
```

### 1.6 Capital Gains and FX Realization

**Source:** `libgnucash/engine/cap-gains.cpp`

**Mechanism:**
- Uses "lots" to track cost basis
- When lot is closed (sold/paid), calculates realized gain/loss
- Creates automatic gain/loss splits
- Marks splits with `gains` flag (GAINS_STATUS_GAINS)

**FX Gain/Loss Calculation:**
```
At Invoice Date:
  AR = USD 10,000 × 1.34 = SGD 13,400

At Payment Date:
  AR = USD 10,000 × 1.365 = SGD 13,650

FX Loss = SGD 13,650 - SGD 13,400 = SGD 250

Journal Entry:
  Dr FX Loss              SGD 250
  Cr Accounts Receivable  SGD 250
```

### 1.7 Revaluation (Unrealized FX)

**Source:** `libgnucash/engine/Scrub.cpp`, `cap-gains.cpp`

**Process:**
1. Identify foreign-currency balances at period end
2. Look up current exchange rate
3. Calculate difference from book value
4. Create adjusting entry:
   ```
   Dr Unrealized FX Gain/Loss
   Cr Foreign Currency Asset/Liability
   ```
5. Reverse at period start (or keep, depending on policy)

---

## 2. Semantic Model: 16 Areas

### 2.1 Entity Functional/Base Currency

**Definition:**
The entity's base currency (also called "functional currency" or "reporting currency") is the currency in which:
- Financial statements are prepared
- Tax obligations are calculated
- Economic substance is measured

**How Defined:**
```python
class LegalEntity(models.Model):
    name = models.CharField(max_length=255)
    base_currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    # base_currency is set at entity creation
    # Changing it requires revaluation of all historical transactions
```

**Can It Change?**
- **Technically:** Yes, but rare and disruptive
- **Practically:** Only when business fundamentally changes (e.g., relocation)
- **Implications:**
  - All historical transactions must be revalued
  - Comparative financial statements affected
  - Tax implications
  - Audit trail complexity

**Recommendation:**
- Allow change with explicit warning and audit trail
- Require revaluation wizard
- Lock change after period close

### 2.2 Document Currency

**Definition:**
The currency in which a business document (invoice, bill, quote) is denominated.

**How Defined:**
```python
class Document(models.Model):
    document_type = models.CharField(choices=[...])
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    # Document currency set at creation
    # Can differ from entity base currency
```

**Relationship to Base Currency:**
- Document currency = what customer/vendor sees
- Base currency = what entity reports in
- Exchange rate captured at document date for reporting

**Example:**
```
Entity Base: SGD
Invoice Currency: USD
Invoice Amount: USD 10,000
Reported Amount: SGD 13,400 (at invoice date rate)
```

### 2.3 Journal Transaction Currency

**Definition:**
The currency in which a journal transaction balances (all split values sum to zero).

**Design Decision:**
We retain transaction currency as an explicit field for:
1. GnuCash migration compatibility
2. Multi-currency transaction clarity
3. FX gain/loss calculation

**How Defined:**
```python
class JournalEntry(models.Model):
    transaction_currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    # All split values must sum to zero in this currency
    # May differ from entity base currency
```

**Derivation:**
- For simple transactions: transaction currency = entity base currency
- For multi-currency: transaction currency = primary document currency (if any)
- For manual entries: user selects, or defaults to base currency

**Recommendation:**
- Keep transaction currency explicit
- Default to entity base currency
- Allow override for multi-currency scenarios

### 2.4 JournalLine Amount

**Definition:**
The `amount` field represents the quantity in the **account's commodity**.

**What It Represents:**
- For a USD bank account: amount = USD quantity
- For a SGD expense account: amount = SGD quantity
- For a stock account: amount = number of shares

**In Which Currency:**
The account's commodity (which may differ from transaction currency).

**Example:**
```
Account: Bank-USD (commodity: USD)
Transaction Currency: SGD
JournalLine:
  amount = 10,000 (USD)
  This means: 10,000 units of the account's commodity
```

**Semantic Meaning:**
- "How many units of this account's commodity are affected?"
- Used for account balance calculation
- Critical for foreign-currency accounts

### 2.5 JournalLine Base/Reporting Value

**Definition:**
The `value` field represents the quantity in the **transaction's balancing currency**.

**What It Represents:**
- The economic value in the transaction's currency
- Used for transaction balancing (all values sum to zero)
- Basis for FX gain/loss calculation

**How Calculated:**
```
value = amount × exchange_rate

Where:
- amount = in account's commodity
- exchange_rate = account_commodity → transaction_currency
```

**In Which Currency:**
The transaction's currency (not necessarily the entity's base currency).

**Example:**
```
Account: Bank-USD (commodity: USD)
Transaction Currency: SGD
Exchange Rate: 1.34 SGD/USD

JournalLine:
  amount = 10,000 (USD)
  value = 13,400 (SGD)
  
This means: 10,000 USD is worth 13,400 SGD in this transaction
```

**Semantic Meaning:**
- "What is this amount worth in the transaction's currency?"
- Used for double-entry balancing
- Critical for multi-currency transactions

### 2.6 Account Currency

**Definition:**
Each account has a commodity (currency for cash/bank/AP/AR accounts, or other commodity for stock/inventory accounts).

**How Defined:**
```python
class Account(models.Model):
    name = models.CharField(max_length=255)
    commodity = models.ForeignKey(Commodity, on_delete=models.PROTECT)
    # For most accounts: commodity is a currency
    # For asset accounts: could be stock, inventory item, etc.
```

**Can Accounts Have Different Currencies?**
Yes. Examples:
- Bank-USD account (commodity: USD)
- Bank-SGD account (commodity: SGD)
- Inventory-Account (commodity: units)
- Stock-AAP account (commodity: shares)

**Implications:**
- Transactions affecting multiple accounts may involve multiple commodities
- Requires exchange rate handling
- Trading accounts or automatic FX needed for balancing

### 2.7 Exchange-Rate Storage

**Definition:**
Exchange rates are stored as price records in a price database.

**How Stored:**
```python
class ExchangeRate(models.Model):
    from_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates_from')
    to_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates_to')
    date = models.DateField()
    rate = models.DecimalField(max_digits=20, decimal_places=10)
    source = models.CharField(max_length=50)  # 'manual', 'central_bank', 'transaction'
    
    class Meta:
        unique_together = ('from_currency', 'to_currency', 'date')
```

**Granularity:**
- **Daily rates:** One rate per currency pair per day
- **Multiple sources:** Manual entry, central bank, market data
- **Historical:** Full time-series maintained

**Query Pattern:**
```python
# Get rate effective on a specific date
rate = ExchangeRate.objects.filter(
    from_currency=usd,
    to_currency=sgd,
    date__lte=transaction_date
).order_by('-date').first()
```

### 2.8 Rate Source and Effective Date

**Sources:**
1. **Manual Entry:** User enters rate at transaction time
2. **Transaction-Implied:** Rate derived from transaction amounts
3. **Central Bank:** Auto-fetched from official sources
4. **Market Data:** Auto-fetched from financial APIs

**Effective Date Determination:**
```
Priority:
1. Explicit rate on transaction (if user provided)
2. Rate on transaction date (if available)
3. Most recent rate before transaction date
4. System default rate (fallback)
```

**Storage:**
```python
class JournalEntry(models.Model):
    # ... other fields
    exchange_rate_source = models.CharField(max_length=50, blank=True)
    exchange_rate_date = models.DateField(null=True, blank=True)
    
    # If user provides explicit rate, store it
    # Otherwise, derive from price database
```

### 2.9 Realized FX

**When Realized:**
FX gain/loss is realized when:
1. Foreign-currency receivable/payable is settled
2. Foreign-currency bank balance is converted
3. Foreign-currency transaction is completed

**How Calculated:**
```
At Transaction Date:
  AR = USD 10,000 × 1.34 = SGD 13,400

At Settlement Date:
  AR = USD 10,000 × 1.365 = SGD 13,650

Realized FX Loss = SGD 13,650 - SGD 13,400 = SGD 250
```

**Journal Entry:**
```
Dr Accounts Payable (USD)     SGD 13,650
Dr FX Loss                    SGD 250
Cr Bank (USD)                 SGD 13,650
Cr Accounts Receivable (USD)  SGD 250

Or simpler:
Dr FX Loss                    SGD 250
Cr Accounts Payable (USD)     SGD 250
```

**Automatic Recognition:**
The system should:
1. Detect settlement of foreign-currency item
2. Look up original transaction rate
3. Look up settlement rate
4. Calculate difference
5. Create automatic FX gain/loss entry

### 2.10 Unrealized FX

**When Unrealized:**
FX gain/loss is unrealized when:
1. Foreign-currency balance exists at period end
2. Exchange rate has changed since transaction date
3. Item is not yet settled

**Period-End Revaluation:**
```
At Transaction Date (Jan 15):
  AR = USD 10,000 × 1.34 = SGD 13,400

At Period End (Mar 31):
  AR = USD 10,000 × 1.35 = SGD 13,500

Unrealized FX Gain = SGD 13,500 - SGD 13,400 = SGD 100
```

**Journal Entry:**
```
Dr Accounts Receivable (USD)   SGD 100
Cr Unrealized FX Gain          SGD 100
```

**Reversal:**
- Reverse at period start (traditional approach)
- Or keep and adjust continuously (modern approach)

**Recommendation:**
- Create explicit revaluation entries at period end
- Use separate "Unrealized FX Gain/Loss" account
- Reverse in next period or keep as adjusting entries

### 2.11 Settlement

**How Settlement Works:**

Scenario: USD 10,000 invoice, paid when rate changes from 1.34 to 1.365

**At Invoice Date:**
```
Dr Expense/Asset              SGD 13,400
Cr Accounts Payable (USD)     SGD 13,400

AR/AP retains: USD 10,000
```

**At Payment Date:**
```
Option 1: Direct Settlement
Dr Accounts Payable (USD)     SGD 13,650
Cr Bank (USD)                 SGD 13,650

Option 2: With Explicit FX
Dr Accounts Payable (USD)     SGD 13,400
Dr FX Loss                    SGD 250
Cr Bank (USD)                 SGD 13,650
```

**What Happens:**
1. System looks up original invoice rate (1.34)
2. System looks up payment rate (1.365)
3. Calculates difference (SGD 250 loss)
4. Creates journal entries
5. Marks invoice as paid
6. Updates AR/AP balance

### 2.12 Revaluation

**How Period-End Revaluation Works:**

1. **Identify Foreign-Currency Balances:**
   - Scan all accounts with non-base currency
   - Calculate current balance in foreign currency
   - Convert to base currency at period-end rate

2. **Compare to Book Value:**
   - Book value = sum of all transaction values
   - Revalued value = foreign balance × period-end rate
   - Difference = unrealized FX gain/loss

3. **Create Adjusting Entry:**
   ```
   For each foreign-currency account:
     Dr/Cr Account (adjustment)
     Cr/Dr Unrealized FX Gain/Loss
   ```

4. **Accounts Revalued:**
   - Foreign-currency bank accounts
   - Accounts receivable in foreign currency
   - Accounts payable in foreign currency
   - Foreign-currency loans

5. **Journal Entries:**
   ```
   Example: USD bank account, balance USD 50,000
   Book value: SGD 67,000 (at historical rates)
   Period-end rate: 1.35
   Revalued: SGD 67,500
   Adjustment: SGD 500 gain
   
   Dr Bank (USD)                SGD 500
   Cr Unrealized FX Gain        SGD 500
   ```

### 2.13 Rounding Differences

**How Handled:**
Rounding differences occur when:
- Exchange rate calculation produces fractional cents
- Multiple conversions accumulate error
- Tax calculations interact with FX

**Where They Go:**
```
Option 1: FX Gain/Loss Account (recommended)
  - Treat as minor FX gain/loss
  - Simpler, cleaner

Option 2: Separate Rounding Account
  - Track separately
  - More granular, but cluttered
```

**Recommendation:**
- Round to account's commodity precision (SCU)
- Absorb differences into FX gain/loss
- Materiality threshold: ignore differences < SGD 0.01

**Implementation:**
```python
def calculate_fx_gain_loss(original_value, current_value):
    difference = current_value - original_value
    # Round to base currency precision
    difference = round(difference, 2)
    # If difference is negligible, ignore
    if abs(difference) < 0.01:
        return Decimal('0.00')
    return difference
```

### 2.14 Multi-Currency Balancing

**How Transactions Balance:**

**Option 1: Aggregate Balancing (without trading accounts)**
- All split values sum to zero in transaction currency
- Amounts may not balance per-commodity
- Simpler, but obscures FX mechanics

**Option 2: Per-Commodity Balancing (with trading accounts)**
- Each commodity balances separately
- Trading accounts absorb FX differences
- More explicit, but complex

**Recommendation for FVA:**
Use **automatic trading-account mechanics** internally, but hide from users:
```
User sees:
  Dr Expense (SGD)          13,400
  Cr Accounts Payable (USD) 10,000
  
System creates internally:
  Dr Expense (SGD)              13,400
  Cr Trading-SGD                13,400
  Dr Trading-USD                13,400
  Cr Accounts Payable (USD)     13,400 (value in SGD)
  
But user never sees trading accounts
```

### 2.15 Migration of GnuCash Trading-Account Books

**Challenge:**
GnuCash books may use explicit trading accounts. We need to migrate without breaking accounting correctness.

**Migration Strategy:**

**Option 1: Preserve Trading Accounts**
- Keep trading accounts as-is
- Mark as "system-managed" (read-only for users)
- Pros: Faithful migration, no data loss
- Cons: Complexity remains

**Option 2: Convert to Automatic FX**
- Remove trading-account splits
- Recalculate as automatic FX entries
- Pros: Cleaner model, better UX
- Cons: Risk of calculation errors

**Recommendation:**
**Hybrid approach:**
1. Migrate trading accounts as "system" accounts (hidden from users)
2. Provide migration report showing conversion
3. Allow users to "clean up" by converting to automatic FX
4. Maintain audit trail of conversion

**Implementation:**
```python
def migrate_trading_accounts(gnucash_book):
    for transaction in gnucash_book.transactions:
        if has_trading_splits(transaction):
            # Keep trading splits but mark as system-generated
            for split in transaction.splits:
                if split.account.type == ACCT_TYPE_TRADING:
                    split.is_system = True
                    split.account.is_hidden = True
```

### 2.16 Interaction with Future Securities/Commodities

**How Model Handles Securities:**
```
Stock Purchase:
  Dr Investment-AAP (commodity: shares)  amount=100 shares
  Cr Bank (commodity: USD)               amount=-15,000 USD
  
  value fields in transaction currency (USD):
  Dr Investment-AAP   value=15,000 USD
  Cr Bank             value=-15,000 USD
```

**How Model Handles Commodities:**
```
Gold Purchase:
  Dr Inventory-Gold (commodity: oz)  amount=10 oz
  Cr Bank (commodity: USD)           amount=-18,000 USD
  
  value fields in transaction currency (USD):
  Dr Inventory-Gold   value=18,000 USD
  Cr Bank             value=-18,000 USD
```

**Relationship to Currency Exchange Rates:**
- Securities/commodities have prices in currencies
- Price database stores: (commodity, currency, date, price)
- For stocks: price = USD per share
- For gold: price = USD per oz
- For currencies: price = SGD per USD (exchange rate)

**Unified Model:**
```python
class Commodity(models.Model):
    type = models.CharField(choices=[
        ('currency', 'Currency'),
        ('stock', 'Stock'),
        ('commodity', 'Commodity'),
    ])
    symbol = models.CharField(max_length=20)  # USD, AAPL, GOLD
    name = models.CharField(max_length=255)

class Price(models.Model):
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE)
    currency = models.ForeignKey(Commodity, on_delete=models.CASCADE, related_name='prices_in')
    date = models.DateField()
    price = models.DecimalField(max_digits=20, decimal_places=10)
    
    # For currencies: this is an exchange rate
    # For stocks: this is the stock price
    # For commodities: this is the commodity price
```

---

## 3. Worked Examples

### Example 1: Foreign-Currency Invoice and Payment

**Scenario:**
- Entity base currency: SGD
- Supplier invoice: USD 10,000
- Invoice date: Jan 15, 2026 (rate: 1.34 SGD/USD)
- Payment date: Feb 15, 2026 (rate: 1.365 SGD/USD)

**At Invoice Date (Jan 15):**

```
Journal Entry:
  Date: 2026-01-15
  Transaction Currency: USD
  
  Split 1: Office Expense
    amount: 10,000 USD
    value: 10,000 USD
    
  Split 2: Accounts Payable (USD)
    amount: -10,000 USD
    value: -10,000 USD
    
  (Transaction balances: 10,000 + (-10,000) = 0 in USD)
```

**Reporting Impact:**
```
Income Statement (in SGD):
  Office Expense: SGD 13,400 (10,000 × 1.34)

Balance Sheet (in SGD):
  Accounts Payable: SGD 13,400 (10,000 × 1.34)
```

**At Payment Date (Feb 15):**

```
Journal Entry:
  Date: 2026-02-15
  Transaction Currency: USD
  
  Split 1: Accounts Payable (USD)
    amount: 10,000 USD
    value: 10,000 USD
    
  Split 2: FX Loss
    amount: 250 SGD
    value: 250 SGD
    
  Split 3: Bank (USD)
    amount: -10,000 USD
    value: -13,650 USD
    
  (Transaction balances: 10,000 + 250 + (-13,650) = -3,400... wait, this doesn't balance)
```

**Correction - Proper Entry:**

```
Journal Entry:
  Date: 2026-02-15
  Transaction Currency: SGD
  
  Split 1: Accounts Payable (USD)
    amount: 10,000 USD
    value: 13,400 SGD  (original book value)
    
  Split 2: FX Loss
    amount: 250 SGD
    value: 250 SGD
    
  Split 3: Bank (USD)
    amount: -10,000 USD
    value: -13,650 SGD
    
  (Transaction balances: 13,400 + 250 + (-13,650) = 0 in SGD)
```

**Realized FX Loss:**
```
Original payable: SGD 13,400
Payment required: SGD 13,650
FX Loss: SGD 250

This is a realized loss because the payable is now settled.
```

### Example 2: Period-End Revaluation

**Scenario:**
- Entity base currency: SGD
- Foreign receivable: USD 10,000 (from invoice on Jan 15)
- Period end: Mar 31, 2026
- Rate at period end: 1.35 SGD/USD
- Original rate: 1.34 SGD/USD

**Before Revaluation:**
```
Accounts Receivable (USD):
  Book value: SGD 13,400 (10,000 × 1.34)
  
Foreign Receivable Balance:
  USD 10,000
```

**Revaluation Calculation:**
```
Current value: USD 10,000 × 1.35 = SGD 13,500
Book value: SGD 13,400
Unrealized FX Gain: SGD 100
```

**Revaluation Journal Entry:**
```
Date: 2026-03-31
Transaction Currency: SGD

Split 1: Accounts Receivable (USD)
  amount: 0 (no change in USD)
  value: 100 SGD (adjustment)
  
Split 2: Unrealized FX Gain
  amount: -100 SGD
  value: -100 SGD
  
(Transaction balances: 100 + (-100) = 0 in SGD)
```

**After Revaluation:**
```
Accounts Receivable (USD):
  Book value: SGD 13,500 (10,000 × 1.35)
  
Unrealized FX Gain:
  Balance: SGD 100 (in equity/reserves)
```

**Reporting Impact:**
```
Balance Sheet (in SGD):
  Accounts Receivable: SGD 13,500
  
Equity:
  Unrealized FX Gain: SGD 100
  
Income Statement:
  (No impact - unrealized gains go to equity)
```

**Reversal (Optional):**
```
Date: 2026-04-01
Reverse the revaluation entry:

Split 1: Accounts Receivable (USD)
  amount: 0
  value: -100 SGD
  
Split 2: Unrealized FX Gain
  amount: 100 SGD
  value: 100 SGD
```

### Example 3: Multi-Currency Transaction with Multiple Lines

**Scenario:**
- Entity base currency: SGD
- Transaction: Pay USD 5,000 and EUR 3,000 from respective bank accounts
- Expenses: SGD 12,000 total
- Rates: USD/SGD = 1.34, EUR/SGD = 1.50

**Transaction Structure:**
```
Date: 2026-02-15
Transaction Currency: SGD (explicitly chosen for balancing)

Split 1: Office Expense
  account: Expense (commodity: SGD)
  amount: 12,000 SGD
  value: 12,000 SGD
  
Split 2: Bank (USD)
  account: Bank-USD (commodity: USD)
  amount: -5,000 USD
  value: -6,700 SGD  (5,000 × 1.34)
  
Split 3: Bank (EUR)
  account: Bank-EUR (commodity: EUR)
  amount: -3,000 EUR
  value: -4,500 SGD  (3,000 × 1.50)
  
Split 4: FX Adjustment
  account: FX Gain/Loss (commodity: SGD)
  amount: -800 SGD
  value: -800 SGD
  
(Transaction balances: 12,000 + (-6,700) + (-4,500) + (-800) = 0 in SGD)
```

**Exchange Rate Handling:**
```
USD Expense:
  amount: 5,000 USD
  value: 6,700 SGD
  Implicit rate: 6,700 / 5,000 = 1.34 SGD/USD

EUR Expense:
  amount: 3,000 EUR
  value: 4,500 SGD
  Implicit rate: 4,500 / 3,000 = 1.50 SGD/EUR

Total Expense:
  SGD 6,700 + SGD 4,500 = SGD 11,200
  
But total expense is SGD 12,000
Difference: SGD 800 (FX adjustment)
```

**FX Adjustment Explanation:**
```
The transaction has SGD 12,000 expense but only SGD 11,200 from foreign currency.
The SGD 800 difference is treated as:
  - Either additional expense (if rate was unfavorable)
  - Or FX gain (if rate was favorable)
  
In this case, it's an FX gain (negative expense) because:
  We paid SGD 11,200 equivalent for SGD 12,000 expense
  Net benefit: SGD 800
```

**Alternative Interpretation:**
```
If the expense was actually USD 5,000 + EUR 3,000 = SGD 11,200
But user entered SGD 12,000 by mistake, then:
  - This is a data entry error
  - System should flag the imbalance
  - User should correct the entry
```

---

## 4. Concrete Model Recommendation

### 4.1 Django Model Definitions

```python
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Commodity(models.Model):
    """Currency, stock, or other tradable commodity"""
    COMMODITY_TYPES = [
        ('currency', 'Currency'),
        ('stock', 'Stock'),
        ('commodity', 'Commodity'),
        ('crypto', 'Cryptocurrency'),
    ]
    
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    type = models.CharField(max_length=20, choices=COMMODITY_TYPES)
    symbol = models.CharField(max_length=20, unique=True)  # USD, SGD, AAPL, BTC
    name = models.CharField(max_length=255)
    fraction = models.IntegerField(default=100)  # SCU: 100 for 2 decimals
    
    class Meta:
        verbose_name_plural = 'commodities'
    
    def __str__(self):
        return f"{self.symbol} - {self.name}"


class Currency(Commodity):
    """Proxy model for currency-specific operations"""
    class Meta:
        proxy = True
    
    def save(self, *args, **kwargs):
        self.type = 'currency'
        super().save(*args, **kwargs)


class ExchangeRate(models.Model):
    """Historical exchange rates between currencies"""
    from_currency = models.ForeignKey(
        Commodity, 
        on_delete=models.CASCADE, 
        related_name='rates_from'
    )
    to_currency = models.ForeignKey(
        Commodity, 
        on_delete=models.CASCADE, 
        related_name='rates_to'
    )
    date = models.DateField()
    rate = models.DecimalField(max_digits=20, decimal_places=10)
    source = models.CharField(max_length=50, default='manual')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('from_currency', 'to_currency', 'date')
        indexes = [
            models.Index(fields=['from_currency', 'to_currency', 'date']),
        ]
    
    def __str__(self):
        return f"{self.from_currency.symbol}/{self.to_currency.symbol} @ {self.rate} on {self.date}"


class Account(models.Model):
    """Chart of accounts"""
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]
    
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    commodity = models.ForeignKey(Commodity, on_delete=models.PROTECT)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    is_hidden = models.BooleanField(default=False)  # For system accounts
    is_system = models.BooleanField(default=False)  # System-managed (e.g., trading accounts)
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class JournalEntry(models.Model):
    """Transaction header"""
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    date = models.DateField()
    date_entered = models.DateTimeField(auto_now_add=True)
    date_due = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=255)
    transaction_currency = models.ForeignKey(
        Commodity, 
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    is_balanced = models.BooleanField(default=False)
    is_readonly = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-date_entered']
    
    def __str__(self):
        return f"JE-{self.guid} on {self.date}"
    
    def check_balance(self):
        """Check if transaction is balanced (sum of values = 0)"""
        total = sum(line.value for line in self.lines.all())
        self.is_balanced = (total == 0)
        return self.is_balanced


class JournalLine(models.Model):
    """Transaction line (split)"""
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='lines')
    
    # Amount in account's commodity
    amount = models.DecimalField(
        max_digits=20, 
        decimal_places=10,
        help_text="Quantity in account's commodity"
    )
    
    # Value in transaction's currency
    value = models.DecimalField(
        max_digits=20, 
        decimal_places=10,
        help_text="Quantity in transaction's balancing currency"
    )
    
    memo = models.CharField(max_length=255, blank=True)
    reconcile_status = models.CharField(max_length=1, default='n')  # n, c, y
    is_system = models.BooleanField(default=False)  # For auto-generated FX lines
    
    class Meta:
        ordering = ['entry', 'guid']
    
    def __str__(self):
        return f"Line {self.guid}: {self.account.code} {self.amount} {self.value}"
    
    @property
    def implicit_rate(self):
        """Calculate implicit exchange rate (value / amount)"""
        if self.amount == 0:
            return Decimal('1.0')
        return self.value / self.amount


class LegalEntity(models.Model):
    """Business entity with its own ledger"""
    guid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    base_currency = models.ForeignKey(
        Commodity, 
        on_delete=models.PROTECT,
        related_name='entities'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
```

### 4.2 How Amount/Value Work

**Amount Field:**
- Represents quantity in the **account's commodity**
- For a USD bank account: `amount = 10,000` means 10,000 USD
- For a stock account: `amount = 100` means 100 shares
- Used for account balance calculation

**Value Field:**
- Represents quantity in the **transaction's currency**
- Used for transaction balancing (all values sum to zero)
- Basis for FX gain/loss calculation

**Relationship:**
```
value = amount × exchange_rate

Where:
- exchange_rate = account_commodity → transaction_currency
```

**Example:**
```python
# Transaction in SGD, affecting USD bank account
entry = JournalEntry.objects.create(
    date='2026-01-15',
    transaction_currency=sgd,  # Transaction balances in SGD
    description='Office supplies'
)

# Split 1: Expense (SGD account)
JournalLine.objects.create(
    entry=entry,
    account=expense_account,  # commodity: SGD
    amount=Decimal('13400.00'),  # 13,400 SGD
    value=Decimal('13400.00')    # 13,400 SGD (same, because same currency)
)

# Split 2: Bank (USD account)
JournalLine.objects.create(
    entry=entry,
    account=bank_usd,  # commodity: USD
    amount=Decimal('-10000.00'),  # -10,000 USD
    value=Decimal('-13400.00')    # -13,400 SGD (converted at 1.34)
)

# Transaction balances: 13,400 + (-13,400) = 0 in SGD
```

### 4.3 How FX is Handled

**Automatic FX Recognition:**

The system implements automatic FX accounting:

1. **At Transaction Date:**
   - Record transaction in document currency
   - Convert to entity base currency for reporting
   - Store both amount and value

2. **At Settlement Date:**
   - Detect settlement of foreign-currency item
   - Calculate FX gain/loss
   - Create automatic journal entry

3. **At Period End:**
   - Revalue foreign-currency balances
   - Calculate unrealized FX gain/loss
   - Create adjusting entries

**Implementation:**

```python
class FXService:
    """Service for handling FX calculations"""
    
    @staticmethod
    def get_rate(from_currency, to_currency, date):
        """Get exchange rate effective on date"""
        rate = ExchangeRate.objects.filter(
            from_currency=from_currency,
            to_currency=to_currency,
            date__lte=date
        ).order_by('-date').first()
        
        return rate.rate if rate else Decimal('1.0')
    
    @staticmethod
    def calculate_realized_fx(original_entry, settlement_date):
        """Calculate realized FX gain/loss"""
        # Get original value
        original_value = sum(
            line.value for line in original_entry.lines.all()
            if line.account.type in ['asset', 'liability']
        )
        
        # Get settlement value
        settlement_rate = FXService.get_rate(
            original_entry.transaction_currency,
            entity.base_currency,
            settlement_date
        )
        settlement_value = original_value * settlement_rate
        
        # Calculate difference
        fx_gain_loss = settlement_value - original_value
        
        return fx_gain_loss
    
    @staticmethod
    def create_fx_entry(original_entry, fx_amount, settlement_date):
        """Create FX gain/loss journal entry"""
        entry = JournalEntry.objects.create(
            date=settlement_date,
            transaction_currency=entity.base_currency,
            description=f'FX gain/loss on {original_entry.description}'
        )
        
        # FX gain/loss line
        JournalLine.objects.create(
            entry=entry,
            account=fx_account,
            amount=fx_amount,
            value=fx_amount,
            is_system=True
        )
        
        # Offset to AR/AP
        JournalLine.objects.create(
            entry=entry,
            account=original_entry.lines.get(account__type='liability').account,
            amount=-fx_amount,
            value=-fx_amount,
            is_system=True
        )
        
        return entry
```

### 4.4 How This Supports Target UX

**User Experience:**

1. **Simple Invoice Entry:**
   ```
   User creates invoice in USD 10,000
   System automatically:
     - Converts to SGD 13,400 for reporting
     - Stores both USD and SGD amounts
     - Tracks FX exposure
   ```

2. **Automatic Settlement:**
   ```
   User pays USD 10,000 when rate is 1.365
   System automatically:
     - Calculates FX loss of SGD 250
     - Creates FX journal entry
     - Updates AR balance
     - Marks invoice as paid
   ```

3. **Period-End Revaluation:**
   ```
   User runs "Period End" wizard
   System automatically:
     - Identifies foreign-currency balances
     - Revalues at period-end rates
     - Creates unrealized FX entries
     - Generates revaluation report
   ```

**What Users See:**
- Invoice amount in original currency (USD 10,000)
- Equivalent in base currency (SGD 13,400)
- FX gain/loss at settlement (SGD 250)
- No trading accounts
- No complex journal entries

**What System Does:**
- Maintains dual-currency tracking
- Calculates FX automatically
- Creates balancing entries
- Preserves audit trail

### 4.5 How This Supports GnuCash Migration

**Migration Strategy:**

1. **Import GnuCash Data:**
   ```python
   def import_gnucash_book(gnucash_file):
       # Parse GnuCash file
       book = parse_gnucash(gnucash_file)
       
       # Import entities
       for account in book.accounts:
           Account.objects.create(
               name=account.name,
               code=account.code,
               type=account.type,
               commodity=map_commodity(account.commodity),
               is_hidden=(account.type == 'trading')
           )
       
       # Import transactions
       for transaction in book.transactions:
           entry = JournalEntry.objects.create(
               date=transaction.date,
               transaction_currency=map_commodity(transaction.currency),
               description=transaction.description
           )
           
           for split in transaction.splits:
               JournalLine.objects.create(
                   entry=entry,
                   account=map_account(split.account),
                   amount=split.amount,
                   value=split.value,
                   memo=split.memo
               )
   ```

2. **Handle Trading Accounts:**
   ```python
   def migrate_trading_accounts():
       # Option 1: Keep as system accounts
       for account in Account.objects.filter(type='trading'):
           account.is_system = True
           account.is_hidden = True
           account.save()
       
       # Option 2: Convert to automatic FX
       # (more complex, requires recalculating all transactions)
   ```

3. **Preserve Accounting Correctness:**
   ```python
   def verify_migration():
       # Check all transactions balance
       for entry in JournalEntry.objects.all():
           if not entry.check_balance():
               raise ValidationError(f"Transaction {entry.guid} is not balanced")
       
       # Check account balances match
       for account in Account.objects.all():
           gnucash_balance = get_gnucash_balance(account.guid)
           fva_balance = account.get_balance()
           if gnucash_balance != fva_balance:
               raise ValidationError(f"Balance mismatch for {account.code}")
   ```

---

## 5. Migration Strategy

### 5.1 Phase 1: Schema Migration

1. **Create Commodity/Currency Tables:**
   - Import all commodities from GnuCash
   - Map to our Commodity model
   - Preserve commodity types (currency, stock, etc.)

2. **Create Account Structure:**
   - Import chart of accounts
   - Map account types
   - Preserve hierarchy
   - Mark trading accounts as system/hidden

3. **Create Entity and Base Currency:**
   - Import root account as entity
   - Set base currency from book options

### 5.2 Phase 2: Transaction Migration

1. **Import Transactions:**
   - Import all transactions
   - Preserve date, description, currency
   - Import all splits with amount/value

2. **Verify Balancing:**
   - Check each transaction balances
   - Flag imbalanced transactions for review
   - Preserve GnuCash balancing logic

3. **Handle Trading Accounts:**
   - Keep trading splits but mark as system
   - Hide trading accounts from UI
   - Provide migration report

### 5.3 Phase 3: Validation

1. **Balance Verification:**
   - Compare account balances to GnuCash
   - Verify all transactions balanced
   - Check FX calculations

2. **Audit Trail:**
   - Preserve all GnuCash metadata
   - Maintain import log
   - Track migration decisions

3. **User Review:**
   - Provide migration summary
   - Highlight trading accounts
   - Allow cleanup options

---

## 6. Recommendations & Next Steps

### 6.1 Immediate Recommendations

1. **Adopt Dual-Field Model:**
   - Implement `amount` and `value` fields as designed
   - Preserve GnuCash semantics
   - Enable multi-currency support

2. **Hide Trading Accounts:**
   - Mark as system accounts
   - Hide from user interface
   - Preserve for migration compatibility

3. **Implement Automatic FX:**
   - Build FX service for automatic calculations
   - Create realized/unrealized FX entries
   - Provide FX reporting

4. **Build Exchange Rate Infrastructure:**
   - Create exchange rate table
   - Support multiple sources (manual, auto)
   - Implement historical rate lookup

### 6.2 Design Decisions Made

1. **Transaction Currency:** Retained as explicit field (not derived)
2. **Amount vs Value:** Both retained with GnuCash semantics
3. **Trading Accounts:** Hidden from users, preserved for migration
4. **FX Handling:** Automatic with explicit journal entries
5. **Exchange Rates:** Stored historically with date granularity

### 6.3 Open Questions for Next Spike

1. **Multi-Tenancy:** How to isolate data between tenants?
   - Row-level security vs schema-per-tenant
   - Shared commodity/exchange-rate tables

2. **Period-End Processing:** How to structure period-close workflow?
   - Revaluation automation
   - Locking mechanism
   - Audit trail

3. **Reporting:** How to generate multi-currency reports?
   - Translation at historical vs current rates
   - Consolidation across entities
   - FX gain/loss reporting

4. **Performance:** How to handle large datasets?
   - Indexing strategy for exchange rates
   - Query optimization for balance calculations
   - Caching strategy

### 6.4 Implementation Priority

1. **P0 (Must Have):**
   - Core journal entry/line models
   - Multi-currency support
   - Exchange rate storage
   - Basic FX calculations

2. **P1 (Should Have):**
   - Automatic FX recognition
   - Period-end revaluation
   - GnuCash migration tool
   - FX reporting

3. **P2 (Nice to Have):**
   - Auto-fetch exchange rates
   - Advanced FX hedging
   - Multi-entity consolidation
   - FX exposure dashboard

### 6.5 Success Criteria

1. **Functional:**
   - Can record multi-currency transactions
   - Can calculate FX gain/loss automatically
   - Can migrate GnuCash books without data loss
   - Can generate accurate financial reports

2. **Performance:**
   - Transaction posting < 100ms
   - Balance calculation < 50ms
   - Exchange rate lookup < 10ms
   - Report generation < 5s

3. **Quality:**
   - All transactions balance
   - FX calculations accurate to 2 decimals
   - Migration preserves all data
   - Audit trail complete

---

## Appendix A: GnuCash Source References

**Key Files Researched:**
- `libgnucash/engine/Transaction.h` — Transaction structure, amount/value documentation
- `libgnucash/engine/Split.h` — Split structure, amount vs value semantics
- `libgnucash/engine/Transaction.cpp` — Balancing logic, trading account handling
- `libgnucash/engine/Scrub.cpp` — Trading account balancing functions
- `libgnucash/engine/cap-gains.cpp` — Capital gains and FX realization
- `libgnucash/engine/gnc-pricedb.cpp` — Exchange rate storage
- `libgnucash/engine/gncInvoice.c` — Invoice multi-currency posting
- `libgnucash/engine/gncEntry.c` — Entry value calculations

**Key Functions:**
- `xaccSplitGetAmount()` / `xaccSplitGetValue()` — Amount/value accessors
- `xaccTransUseTradingAccounts()` — Trading account flag
- `gnc_transaction_balance_trading()` — Trading account balancing
- `gncInvoicePostToAccount()` — Invoice posting with currency conversion
- `gnc_price_get_value()` — Exchange rate lookup

---

## Appendix B: Glossary

**Amount:** Quantity in account's commodity  
**Value:** Quantity in transaction's balancing currency  
**Commodity:** Anything tradable (currency, stock, etc.)  
**Trading Account:** Special account for per-commodity balancing  
**Realized FX:** FX gain/loss from settled transactions  
**Unrealized FX:** FX gain/loss from outstanding balances  
**SCU:** Smallest Commodity Unit (e.g., 100 for 2 decimal places)  
**Base Currency:** Entity's functional/reporting currency  
**Transaction Currency:** Currency in which transaction balances  

---

**End of Spike 2 Report**

**Next Steps:**
1. Review this report with architecture team
2. Validate semantic model with accounting advisors
3. Begin implementation of core models
4. Plan GnuCash migration testing
5. Proceed to Spike 3 (Period-End Processing)

