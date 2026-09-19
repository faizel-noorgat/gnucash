# Business Rules — GnuCash

**Extracted:** 237 rules (47 P0, 164 P1, 26 P2)
**Rounds:** 3
**System:** gnucash

---

## P0 Rules (Critical — Money / Regulatory / Data Integrity)

### 1. Invoice Total Computation - Entry Sum with Tax

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gncInvoice.c:917-1006`  
**Confidence:** High

**Plain English:** An invoice total is the sum of all entry net values plus the sum of all tax amounts per tax account; taxes are accumulated per account and each tax account's total is rounded half-up to the invoice currency's denominator before summing.

**Given:** An invoice with multiple entries, each having a net value and associated tax amounts by account, and a currency with a specific denomination fraction  
**When:** the invoice total is computed  
**Then:** total = sum(entry values) + sum(tax values per account, each rounded half-up to currency denom)

**And:** Rounding uses GNC_HOW_DENOM_EXACT | GNC_HOW_RND_ROUND_HALF_UP

**Parameters:** denom = gnc_commodity_get_fraction(invoice currency); rounding = GNC_HOW_RND_ROUND_HALF_UP

**Edge Cases:**
- If any entry has a bad numeric value it is skipped with a warning
- Tax totals per account are rounded before summing to prevent imbalanced postings
- Credit notes negate both the net values and tax amounts

---

### 2. Entry Value - Discount How: PRETAX vs SAMETIME vs POSTTAX

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gncEntry.c:1231-1275`  
**Confidence:** Medium

**Plain English:** The order of discount and tax application depends on discount_how: PRETAX applies discount first (reducing tax base), SAMETIME applies discount and tax on same base (pretax), POSTTAX computes tax first then discount on pretax+tax.

**Given:** pretax=$100, tax=10%, discount=20%  
**When:** discount_how=POSTTAX  
**Then:** tax=$10, after_tax=$110, discount=$22, customer pays=$110-$22=$88

**Parameters:** GNC_DISC_PRETAX=0, GNC_DISC_SAMETIME=1, GNC_DISC_POSTTAX=2

**⚠️ SME Question:** P0 panel doubts spec fidelity: The rule correctly describes the discount/tax calculation logic and arrives at accurate final amounts ($88 for POSTTAX), but contains a critical factual error in the enum parameter values. The rule states GNC_DISC_PRETAX=0, GNC_DISC_SAMETIME=1, GNC_DISC_POSTTAX=2, but the actual values are 1, 2, 3 respectively (gncEntry.h:51-53). This is P0 because it directly affects financial calculations: PRETAX results in $88 customer payment (tax on discounted amount), SAMETIME results in $90 (tax on original amount), and POSTTAX results in $88 (discount on after-tax amount). A regulator or auditor would care if tax calculation methodology changed silently, as this has compliance implications and moves real money.

---

### 3. Entry Value - Tax Included Back-Computation

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gncEntry.c:1186-1210`  
**Confidence:** High

**Plain English:** When prices are tax-included, the pre-tax value is derived by: pretax = (aggregate - fixed_taxes) / (1 + total_tax_percent); the net price is then pretax / qty.

**Given:** aggregate=$110 (qty=10, price=$11), tax table with 10% PERCENT and $0 VALUE  
**When:** tax_included=true  
**Then:** pretax = (110 - 0) / (1 + 0.10) = 100; net_price = 100 / 10 = 10; the $10 difference is tax

**Parameters:** tpercent = sum of PERCENT tax entries / 100; tvalue = sum of VALUE tax entries; pretax = (aggregate - tvalue) / (1 + tpercent)

**Edge Cases:**
- If qty is zero, net_price cannot be computed (division by zero guard at line 1200)

---

### 4. Entry Values Are Rounded to Currency Denominator

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gncEntry.c:1431-1453`  
**Confidence:** High

**Plain English:** All entry values (invoice value, discount value, tax values, bill value) are rounded to the invoice/bill currency's commodity denominator (SCU) using round-half-up before being used for postings.

**Given:** An invoice in USD (SCU=100, i.e. cents) with computed entry value of $33.335  
**When:** values are recomputed  
**Then:** value_rounded = $33.34 (rounded half-up to 2 decimal places); tax values per account similarly rounded

**Parameters:** denom = gnc_commodity_get_fraction(currency); default denom = 100000 if no invoice/bill attached

---

### 5. Invoice Posting - Split Value Conversion for Multi-Commodity

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gncInvoice.c:1408-1436`  
**Confidence:** High

**Plain English:** When an invoice is posted and a split's account currency differs from the invoice currency, the amount is converted using the invoice's stored price: converted_amount = value / price, rounded half-up.

**Given:** Invoice in USD (denom=100) with entry value=$100, account commodity is EUR with price USD/EUR=1.25  
**When:** gncInvoicePostAddSplit processes the split  
**Then:** split value = $100 (USD); split amount = 100/1.25 = 80 EUR (rounded half-up)

**Parameters:** converted_amount = gnc_numeric_div(value, gnc_price_get_value(price), GNC_DENOM_AUTO, GNC_HOW_RND_ROUND_HALF_UP)

---

### 6. Rounding Modes Available

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gnc-numeric.h:143-177`  
**Confidence:** High

**Plain English:** GnuCash supports 8 rounding modes: FLOOR (toward -infinity), CEIL (toward +infinity), TRUNC (toward zero), PROMOTE (away from zero), ROUND_HALF_DOWN (ties toward zero), ROUND_HALF_UP (ties away from zero), ROUND (ties to nearest even), NEVER (throw error if rounding needed).

**Given:** A computed value of 3.5 with denominator 1  
**When:** ROUND_HALF_DOWN rounding is applied  
**Then:** result = 3

---

### 7. Default Financial Rounding is ROUND_HALF_UP

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gncInvoice.c:910-911,973-974,1000-1001; libgnucash/engine/gncEntry.c:1431-1452`  
**Confidence:** Medium

**Plain English:** Across invoice, entry, and tax computations, the default rounding mode is GNC_HOW_RND_ROUND_HALF_UP, meaning ties (exactly 0.5 of the smallest unit) are rounded away from zero. This is the standard financial rounding used throughout.

**Given:** A computed tax amount of $3.335 in a USD account (SCU=100)  
**When:** rounded for posting  
**Then:** result = $3.34 (rounded half-up to cents)

**⚠️ SME Question:** P0 panel doubts spec fidelity: The rule is partially faithful but P0 is justified. ROUND_HALF_UP is correctly identified for critical tax/invoice posting paths (verified at cited lines), and the $3.335→$3.34 example is accurate per the 'round away from zero' definition. However, the rule oversimplifies by calling it 'the default used throughout' - the code actually uses ROUND_HALF_UP (21 occurrences) specifically for final posting operations, while ROUND/banker's rounding (7 occurrences) handles intermediate calculations. This is genuinely P0 because: (1) it directly moves money through tax and invoice calculations, (2) tax authorities mandate specific rounding methods, and (3) the code explicitly states these roundings prevent imbalanced transactions - a silent change would cause audit failures, regulatory non-compliance, and cumulative financial errors.

---

### 8. FIFO Policy - Lot Selection

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/policy.cpp:118-124`  
**Confidence:** High

**Plain English:** Under FIFO (First In, First Out) policy, the lot selected for a closing split is the earliest (oldest) open lot with an opposite-signed balance in the same account and currency.

**Given:** Account with open lots: Lot A (opened Jan 1, balance +50), Lot B (opened Feb 1, balance +30)  
**When:** a sell split of -20 shares arrives under FIFO policy  
**Then:** Lot A is selected (earliest open lot with matching opposite sign)

---

### 9. Invoice Post Sign Convention: Customer Invoice vs Credit Note

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gncInvoice.c:1515-1531`  
**Confidence:** Medium

**Plain English:** When posting an invoice, the total and tax amounts are negated if the document is a customer document XOR a credit note (i.e., customer invoice or vendor credit note posts with positive sign; customer credit note and vendor invoice post with inverted sign).

**Given:** An invoice with owner type (customer/vendor/employee) and is_credit_note flag  
**When:** Posting to an account  
**Then:** If (is_cust_doc != is_cn): negate total and each tax account value; else keep signs as-is

**Parameters:** is_cust_doc = (owner_type == GNC_OWNER_CUSTOMER); is_cn = gncInvoiceGetIsCreditNote()

**⚠️ SME Question:** P0 panel doubts spec fidelity: The Given/When/Then specification is FAITHFUL to the code: the XOR condition (is_cust_doc != is_cn) at line 1522 correctly identifies when to negate total and tax values. However, the Plain English interpretation is UNFAITHFUL and BACKWARDS. The rule states "customer invoice or vendor credit note posts with positive sign; customer credit note and vendor invoice post with inverted sign" but the code shows the opposite: customer invoice (XOR=TRUE) and vendor credit note (XOR=TRUE) get NEGATED, while customer credit note (XOR=FALSE) and vendor invoice (XOR=FALSE) keep their original signs. The XOR logic itself is correct, but the explanatory interpretation is inverted. This is a P0 rule because it directly affects financial posting accuracy - negating the wrong document types would cause incorrect account balances and break the accounting equation. The defect is in the interpretation layer, not the Given/When/Then specification, but downstream teams relying on the Plain English explanation would implement the wrong behavior.

---

### 10. Entry Value Computation: Aggregate = qty * price

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gncEntry.c:1131-1210`  
**Confidence:** Medium

**Plain English:** An invoice/bill entry's gross value is computed as quantity multiplied by unit price, with arithmetic reduction and rounding. If tax is included in the price, the pre-tax amount is back-computed as (aggregate - fixed_tax) / (1 + tax_percent).

**Given:** An entry with quantity q, unit price p, tax table with percentage entries summing to T% and value entries summing to V, tax_included flag  
**When:** gncEntryComputeValueInt() computes the value  
**Then:** aggregate = q * p (GNC_HOW_DENOM_REDUCE | GNC_HOW_RND_ROUND); if tax_included: pretax = (aggregate - V) / (1 + T/100); else pretax = aggregate

**Parameters:** percent constant = 100/1; GNC_HOW_DENOM_REDUCE; GNC_HOW_RND_ROUND for aggregate; GNC_HOW_RND_ROUND_HALF_UP for share-price splits

**⚠️ SME Question:** P0 panel doubts spec fidelity: CORE LOGIC FAITHFUL: The rule correctly describes the aggregate calculation (aggregate = qty * price with GNC_HOW_DENOM_REDUCE | GNC_HOW_RND_ROUND at line 1153) and the pre-tax back-computation when tax_included is true (pretax = (aggregate - tvalue) / (1 + tpercent) at lines 1192-1198, where tpercent is already converted to decimal form). The else branch (pretax = aggregate at line 1209) is also correct. P0 JUSTIFIED: This function computes invoice/bill entry values with tax calculations. Errors here would cause incorrect customer invoices, incorrect tax reporting, and revenue recognition failures. Tax computation methods are regulated by tax authorities. This absolutely moves money and enforces compliance. FAITHFULNESS ISSUE: The rule's parameters section claims "GNC_HOW_RND_ROUND_HALF_UP for share-price splits" but this is (a) NOT in the cited code range 1131-1210, and (b) mischaracterizes the actual usage - lines 1432-1452 use GNC_HOW_RND_ROUND_HALF_UP for rounding entry monetary values (i_value_rounded, i_disc_value_rounded, i_tax_value_rounded), not for share-price splits. The rule conflates information from outside the cited range and misidentifies its purpose. RECOMMENDATION: Remove the "GNC_HOW_RND_ROUND_HALF_UP for share-price splits" parameter from this rule card, or create a separate rule card for the entry-value rounding logic at lines 1431-1453 if that's a distinct business rule worth capturing. | P0 justified: the function computes invoice/bill entry monetary values — it directly moves money and is the authoritative aggregation primitive called by gncEntryRecomputeValues (line 1424), gncEntryComputeValue (line 1337), and downstream billing flows. Any mismatch in the rounding contract propagates to cent-level differences in customer invoices.

Faithful = false. The cited code at libgnucash/engine/gncEntry.c:1131-1210 diverges from the claim on four load-bearing points:

1. ROUND_HALF_UP is FABRICATED for this function. The claim lists 'GNC_HOW_RND_ROUND_HALF_UP for share-price splits' as a parameter, but grep confirms ROUND_HALF_UP is used only in gncEntryRecomputeValues (lines 1431, 1434, 1441, 1445, 1452, 1530) — a separate caller that post-rounds the final output. Inside gncEntryComputeValueInt itself, every division/multiplication uses GNC_HOW_RND_ROUND (banker's rounding, enum value 0x07 per gnc-numeric.h:172), including the i_net_price computation at line 1202. 'Share-price split' is not a concept in this function — it is a hallucinated parameter.

2. Missing precondition: the tax_included branch is guarded by 'tax_table && tax_included' (line 1186), not 'tax_included' alone. If tax_table is NULL with tax_included=TRUE, the code falls through to pretax = aggregate. The claim's 'if tax_included: pretax = ...' misstates the guard.

3. Omitted output: i_net_price = pretax / qty (line 1202) with banker's rounding, returned through the net_price out-parameter (line 1323-1324). This is a money-bearing value the claim ignores.

4. Intermediate rounding modes not stated: tpercent→decimal conversion uses GNC_HOW_DENOM_EXACT | GNC_HOW_RND_NEVER (line 1181 — no rounding); the pretax division uses GNC_HOW_DENOM_REDUCE | GNC_HOW_RND_ROUND (line 1198); the tvalue accumulation uses GNC_HOW_DENOM_LCD (line 1167-1168). Only the aggregate multiplication (line 1153) is correctly characterized as REDUCE | ROUND.

What IS correct in the claim: aggregate = qty * price with REDUCE|ROUND (line 1153); percent = 100/1 (line 1142); the algebraic formula pretax = (aggregate - V) / (1 + T/100) (line 1192-1198); the else-branch pretax = aggregate (line 1209). The core formula is right but the rounding contract — the load-bearing P0 detail — is wrong.

---

### 11. Discount Application Order: PRETAX / SAMETIME / POSTTAX

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gncEntry.c:1231-1275`  
**Confidence:** High

**Plain English:** Discounts are applied to entries in one of three modes: PRETAX (discount off pre-tax; tax computed on pretax-discount), SAMETIME (discount and tax both computed off pretax), or POSTTAX (discount computed off pretax+tax). Percentage discounts are converted by dividing by 100.

**Given:** An entry with pretax amount, discount d, discount_type (VALUE or PERCENT), and discount_how  
**When:** Computing the final entry value  
**Then:** PRETAX: discount_amt = d (or pretax*d/100 if percent); result = pretax - discount; tax_base = pretax - discount. SAMETIME: discount_amt off pretax; tax_base = pretax. POSTTAX: if percent, discount = (pretax + pretax*T/100 + V) * d/100; result = pretax - discount; tax_base = pretax

**Parameters:** GNC_DISC_PRETAX=1, GNC_DISC_SAMETIME=2, GNC_DISC_POSTTAX=3; GNC_AMT_TYPE_VALUE=1, GNC_AMT_TYPE_PERCENT

---

### 12. Lot Closure Rule: Balance Equals Zero

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/gnc-lot.cpp:486-524`  
**Confidence:** High

**Plain English:** A lot is considered closed (is_closed=TRUE) when the sum of the adjusted amounts of all its splits equals zero; otherwise it remains open.

**Given:** A GNCLot with splits s1..sN, each with an adjusted_amount (via xaccSplitGetAdjustedAmount)  
**When:** gnc_lot_get_balance() is called  
**Then:** balance = sum of all split adjusted_amounts; if balance == 0, is_closed = TRUE; else is_closed = FALSE

**Parameters:** zero comparison via gnc_numeric_equal(); adjusted amount used (not raw amount)

---

### 13. Capital Gains: Pro-Rata Cost Basis per Lot Split

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/cap-gains.cpp:710-747`  
**Confidence:** Medium

**Plain English:** For a realized split in a lot, capital gain is computed pro-rata: (lot_value/lot_amount) * split_adjusted_amount - split_value. A non-zero gain triggers creation of a balancing 'Realized Gain/Loss' transaction with two equal-and-opposite splits.

**Given:** A lot with total amount A and total value V, and a current split with adjusted_amount a and value v  
**When:** xaccSplitComputeCapGains computes the gain  
**Then:** frac = a / A (GNC_HOW_DENOM_REDUCE); basis = frac * V (GNC_HOW_RND_ROUND_HALF_UP); cap_gain = basis - v (GNC_HOW_DENOM_FIXED); if cap_gain != 0, create Realized Gain/Loss transaction with 2 splits of +cap_gain and -cap_gain

**Parameters:** Rounding modes: GNC_HOW_DENOM_REDUCE for fraction, GNC_HOW_RND_ROUND_HALF_UP for basis, GNC_HOW_DENOM_FIXED for gain

**Edge Cases:**
- Numeric overflow during computation aborts silently with PERR (line 734-747)
- Malformed lot (opening + split > balance) aborts (line 700-707)

**⚠️ SME Question:** P0 panel doubts spec fidelity: The rule captures the core formula correctly but has critical ambiguities: (1) 'lot amount A and lot value V' are misleading — the code uses the balance BEFORE the current split via gnc_lot_get_balance_before(), not the total lot balance; (2) the rule omits that lot_split gets amount=0 (crucial for lot balance integrity); (3) the rule doesn't specify which split gets +cap_gain vs -cap_gain (lot_split gets +cap_gain, gain_split gets -cap_gain); (4) existing transactions can be updated, not just created; (5) the rule omits GNC_HOW_DENOM_EXACT flag from the basis calculation. These omissions could lead to incorrect modernization implementation. P0 is justified as this is core accounting logic affecting financial reporting.

---

### 14. Numeric Overflow / Argument Validation

**Priority:** P0  
**Category:** Validation  
**Source:** `libgnucash/engine/gnc-numeric.h:223-232`  
**Confidence:** Medium

**Plain English:** Every gnc_numeric arithmetic operation can fail with error codes: GNC_ERROR_ARG (invalid input), GNC_ERROR_OVERFLOW (intermediate overflow), GNC_ERROR_DENOM_DIFF (incompatible denominators), GNC_ERROR_REMAINDER (non-exact division). Code must check results via gnc_numeric_check().

**Given:** A gnc_numeric value (numerator/denominator pair)  
**When:** Arithmetic operations are performed  
**Then:** Result encodes error in a sentinel value; gnc_numeric_check(result) returns 0 for OK or one of GNC_ERROR_ARG/OVERFLOW/DENOM_DIFF/REMAINDER

**Parameters:** GNC_ERROR_OK=0, GNC_ERROR_ARG=-1, GNC_ERROR_OVERFLOW=-2, GNC_ERROR_DENOM_DIFF=-3, GNC_ERROR_REMAINDER=-4

**⚠️ SME Question:** P0 panel doubts spec fidelity: The error code values (0, -1, -2, -3, -4) and names match the cited enum exactly. However, the rule text is unfaithful because it omits the critical encoding mechanism: line 343 states "Error values always have a denominator of zero" - this is the sentinel that signals an error. The Given/When/Then says "Result encodes error in a sentinel value" but never specifies that denom=0 is the sentinel. This is a P0 data integrity rule for financial calculations, and the omission means a modernization effort cannot faithfully reproduce the behavior without discovering this detail independently. The rule correctly identifies that gnc_numeric_check() extracts the error code, but the encoding detail (denom=0) is essential for verification and replication.

---

### 15. Invoice Paid State = Posted Lot Closed

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/gncInvoice.c:1987-1992`  
**Confidence:** Medium

**Plain English:** An invoice is considered paid only when its associated posted lot has been fully balanced to zero; this is the only condition that marks an invoice as paid.

**Given:** An invoice is posted (posted_txn exists)  
**When:** gncInvoiceIsPaid is called on a posted invoice whose posted_lot balance is zero  
**Then:** gncInvoiceIsPaid returns TRUE because gnc_lot_is_closed(posted_lot) returns TRUE

**And:** invoice.posted_txn is not null AND invoice.posted_lot.balance == 0

**Parameters:** none (derived state)

**Edge Cases:**
- Invoice with no posted_lot: gncInvoiceIsPaid returns FALSE even if balance is zero in some other lot

**⚠️ SME Question:** P0 panel doubts spec fidelity: The rule is P0 because it determines when an invoice is considered paid, which directly affects financial reporting, payment tracking, and accounts receivable. However, the Given/When/Then is NOT faithful to the code in three critical ways:

1. **posted_txn is not checked**: The Given states "An invoice is posted (posted_txn exists)" and the And clause requires "invoice.posted_txn is not null", but gncInvoiceIsPaid (lines 1987-1992) never checks posted_txn. It only checks posted_lot. An invoice could theoretically have a posted_lot without a posted_txn, and gncInvoiceIsPaid would still evaluate it.

2. **Missing edge case - zero balance with no splits**: The rule states "posted_lot balance is zero" implies paid, but gnc_lot_get_balance (gnc-lot.cpp:496-500) explicitly sets is_closed = FALSE when a lot has no splits, even though it returns zero balance. A lot with zero balance but no splits is NOT considered closed/paid.

3. **Missing caching behavior**: The rule doesn't capture that is_closed is lazily computed and cached (gnc-lot.cpp:372). Once computed, gnc_lot_is_closed returns the cached value without recomputing balance. This means the "paid" state can persist even if underlying splits change, until the cache is invalidated (is_closed < 0).

The correct behavior: An invoice is paid when posted_lot exists AND (posted_lot has splits AND sum of split adjusted amounts == 0) OR (posted_lot was previously marked as closed via cached is_closed flag). The function does NOT require posted_txn to exist.

---

### 16. Invoice Posted State Derivation

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/gncInvoice.c:1981-1985`  
**Confidence:** High

**Plain English:** An invoice is considered 'posted' if and only if it has an attached posted transaction; the presence of posted_txn is the sole determinant.

**Given:** An invoice exists  
**When:** gncInvoiceIsPosted is called on an invoice with posted_txn set to a valid Transaction  
**Then:** gncInvoiceIsPosted returns TRUE

**And:** invoice.posted_txn is a non-null Transaction object

**Parameters:** none (derived state)

**Edge Cases:**
- If posted_txn is set to NULL, invoice becomes 'not posted' regardless of other state

---

### 17. Invoice Unposted→Posted Transition

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/gncInvoice.c:1442-1733`  
**Confidence:** Medium

**Plain English:** Posting an invoice creates a new lot, a new transaction (with invoice ID as its number, owner name as description), and splits for each entry; if autopay is TRUE, the system attempts to apply existing payments and opposite-sign documents to close or reduce the lot balance.

**Given:** An invoice in Not-Posted state with entries and a valid target account  
**When:** gncInvoicePostToAccount is invoked  
**Then:** A new GNCLot is created, a new Transaction is created with type INVOICE ('I'), posted_txn/posted_lot/posted_acc are set, and the transaction is marked read-only with reason 'Generated from an invoice. Try unposting the invoice.'

**And:** gncInvoiceIsPosted(invoice) == FALSE AND acc is a valid Account

**Parameters:** post_date, due_date, memo, accumulate_splits (boolean), autopay (boolean)

**Edge Cases:**
- Billing terms are stabilized via gncBillTermReturnChild(terms, TRUE) before posting — child terms may be created
- For employee invoices, credit-card account path is checked via gncEmployeeGetCCard

**⚠️ SME Question:** P0 panel doubts spec fidelity: P0 is justified: this function creates financial transactions that affect account balances, enforces data integrity via read-only protection on invoice-generated transactions, and handles automatic payment application — all core accounting operations that regulators and auditors would care about. However, the rule is NOT faithful to the code in several ways: (1) The claim "with type INVOICE ('I')" is inaccurate — the code never sets a transaction type to 'I'. Instead, gncInvoiceGetTypeString returns localized strings like "Invoice", "Bill", "Expense", "Credit Note" which are used as the action parameter in gnc_set_num_action. (2) The claim "invoice ID as its number" is only conditionally true — gnc_set_num_action checks a book option (num_action): when FALSE, the transaction number is set to the invoice ID; when TRUE, the transaction number is set to the type string instead. (3) The "And gncInvoiceIsPosted(invoice) == FALSE AND acc is a valid Account" is a precondition that should appear in the Given clause, not the Then clause — the guard at line 1463 returns NULL if the invoice is already posted. The core behavior (creates lot, creates transaction, sets posted_txn/posted_acc, marks read-only with the specified message, conditionally applies autopay) is correct, but the specific details about transaction type and number assignment are not accurately represented. | The rule contains a critical error in the postcondition: it states "gncInvoiceIsPosted(invoice) == FALSE" but after posting, the invoice should be posted (TRUE). The code at line 1463 checks if the invoice is already posted and returns NULL if so (precondition), but after posting completes, gncInvoiceAttachToTxn is called at line 1710, which sets posted_txn via gncInvoiceSetPostedTxn at line 1268. The gncInvoiceIsPosted function (line 1981-1985) returns TRUE when posted_txn is a valid transaction, so after posting it should return TRUE, not FALSE. Additionally, the claim that the transaction number is set to the invoice ID is conditional on a book option (num_action). At line 1504, gnc_set_num_action is called, and the engine-helpers.c implementation (lines 134-140) shows that when num_action is TRUE, the transaction number is set to the action/type parameter instead of the invoice ID. This conditional behavior is not mentioned in the rule. These discrepancies would cause a modernization to implement incorrect behavior. The rule is P0-justified because it creates transactions with splits that affect account balances (moves money) and ensures invoices are properly posted with correct transactions and lots (guards data integrity).

---

### 18. Transaction Void Transition

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/Transaction.cpp:2503-2531`  
**Confidence:** High

**Plain English:** Voiding a transaction sets its note to 'Voided transaction', preserves former notes in kvp[void_former_notes_str], records the void reason and UTC ISO-8601 timestamp in kvp, sets every split to VREC ('v'), and marks the transaction read-only with reason 'Transaction Voided'. Voiding is refused if the transaction is already read-only (e.g. generated by business features).

**Given:** A non-voided transaction whose read-only flag is not set  
**When:** xaccTransVoid is called with a reason string  
**Then:** xaccTransGetVoidStatus returns TRUE, all splits have reconcile flag 'v' (VREC), and xaccTransGetReadOnly is non-null

**And:** transaction is not currently read-only

**Parameters:** reason (string stored in kvp[void_reason_str])

**Edge Cases:**
- Voiding a read-only transaction is refused silently with PWARN ('Refusing to void a read-only transaction!')

---

### 19. Split Reconciliation State Machine (5 states)

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/Split.cpp:1818-1842; libgnucash/engine/Split.h:73-77`  
**Confidence:** High

**Plain English:** A split's reconcile flag is a single character with exactly 5 legal values: 'n' (unreconciled), 'c' (cleared), 'y' (reconciled), 'f' (frozen into accounting period), 'v' (void). Any other character is rejected with 'Bad reconciled flag' error and the flag is not changed. Changing the flag recomputes the owning account's balance.

**Given:** A split with current reconcile flag X  
**When:** xaccSplitSetReconcile is called with one of the 5 legal characters  
**Then:** split.reconciled is updated; split is marked dirty; owning account balance is recomputed

**And:** split.reconciled ∈ {'n','c','y','f','v'}

**Parameters:** NREC='n', CREC='c', YREC='y', FREC='f', VREC='v'

**Edge Cases:**
- Any other character is rejected with 'Bad reconciled flag' error and the flag is NOT changed

---

### 20. Auto-Apply Payments Balancing Rules

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/gncOwner.c:1256-1392`  
**Confidence:** High

**Plain English:** Auto-apply balances lots pairwise in the same account. A lot pair is eligible only if: (a) both lots are open (not closed), (b) both have at least one split, (c) both are in the same account, (d) their balances have OPPOSITE signs. Matching logic: (1) both document lots → create lot link transaction; (2) both payment lots → offset the smaller-abs lot with part of the larger-abs lot; (3) one document + one payment → offset the document lot with the payment lot. After each offset, QOF_EVENT_MODIFY is fired on any invoice attached to the affected lot.

**Given:** An owner with a set of open lots that may include both document lots (with invoices) and payment lots  
**When:** gncOwnerAutoApplyPaymentsWithLots is invoked after posting or applying payments  
**Then:** Lots are balanced; lot link transactions may be created; QOF_EVENT_MODIFY is emitted on attached invoices

**And:** owner is non-null AND lots is non-null

**Parameters:** none

**Edge Cases:**
- Empty lots are destroyed during iteration
- Lots that become closed mid-iteration are skipped

---

### 21. Discount/Tax Application Order

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gncEntry.c:1231-1273`  
**Confidence:** Medium

**Plain English:** How discount and tax combine is controlled by GncDiscountHow: PRETAX applies discount before tax (tax base = pretax - discount); SAMETIME applies both to pretax (discount and tax on same base); POSTTAX applies tax before discount (discount base = pretax + tax).

**Given:** An entry with tax and discount  
**When:** entry total is computed for an invoice line  
**Then:** Discount amount and tax amount are computed in the specified order

**And:** entry.discount_how ∈ {PRETAX, SAMETIME, POSTTAX}

**Parameters:** GNC_DISC_PRETAX=1, GNC_DISC_SAMETIME=2, GNC_DISC_POSTTAX=3

**Edge Cases:**
- Comment documents specific formulas: PRETAX=pretax discount with pretax-discount tax base; SAMETIME=both on pretax; POSTTAX=pretax+tax base with pretax tax

**⚠️ SME Question:** Citation was corrected by referee (The cited location (gncEntry.h:49-87) only declares the GncDiscountHow enum (PRETAX=1, SAMETIME=2, POSTTAX=3) and contains a documentation comment describing the discount/tax application order. The actual implementation of this behavior is in gncEntry.c function gncEntryComputeValueInt, lines 1231-1273, where a switch on discount_how implements: (1) PRETAX: discount computed from pretax, then pretax is set to pretax-discount so tax is computed on the reduced base (line 1248: pretax = result); (2) SAMETIME: discount computed from pretax, tax computed on original pretax (line 1248 not executed); (3) POSTTAX: discount computed on pretax+tax+tvalue (lines 1258-1266 compute after_tax then discount is based on that). The rule is genuinely implemented in executable code, but at the corrected location, not at the cited header file.) — confirm libgnucash/engine/gncEntry.c:1231-1273 is the authoritative implementation.

---

### 22. Transaction Read-Only Guard

**Priority:** P0  
**Category:** Validation  
**Source:** `libgnucash/engine/Transaction.cpp:1970-1980, 2345, 2510-2514`  
**Confidence:** Medium

**Plain English:** A transaction marked read-only cannot be voided (xaccTransVoid refuses with a warning) and cannot be edited through the UI. Read-only status is set by invoice posting (with reason 'Generated from an invoice...') and by voiding ('Transaction Voided'). It is cleared by unposting or unvoiding.

**Given:** A transaction that has been marked read-only (e.g., by invoice posting or voiding)  
**When:** xaccTransVoid or any edit is attempted on a read-only transaction  
**Then:** xaccTransVoid logs warning and returns early; UI prevents editing

**And:** transaction.kvp['trans-read-only-reason'] is non-null

**Parameters:** kvp path = {TRANS_READ_ONLY_REASON}

**Edge Cases:**
- UI paths may bypass this check in some dialogs — grep for xaccTransGetReadOnly usages

**⚠️ SME Question:** P0 panel doubts spec fidelity: PARTIALLY FAITHFUL with critical errors. Core behavior verified: (1) xaccTransVoid correctly refuses to void read-only transactions at lines 2510-2514 with PWARN("Refusing to void a read-only transaction!") and early return; (2) Read-only is set by invoice posting at gncInvoice.c:1713 with reason "Generated from an invoice. Try unposting the invoice."; (3) Read-only is set by voiding at Transaction.cpp:2529 with reason "Transaction Voided"; (4) Read-only is cleared by unposting at gncInvoice.c:1753 and unvoiding at Transaction.cpp:2571. CRITICAL ERRORS: (1) The rule states kvp path is 'trans-read-only-reason' but the actual KVP key is "trans-read-only" (Transaction.cpp:184 defines TRANS_READ_ONLY_REASON as "trans-read-only", not "trans-read-only-reason"); (2) "UI prevents editing" is unverifiable from cited engine code — no UI layer evidence in Transaction.cpp; (3) Invoice reason text is "Generated from an invoice. Try unposting the invoice." not "Generated from an invoice...". P0 is justified: this guards data integrity by preventing modification of invoice-generated transactions and voided transactions, which are financial records that must preserve audit trails. The Given/When structure is correct but the Then clause contains factual errors in the KVP path specification and an unverifiable UI claim.

---

### 23. Tax Amount Type Interpretation

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gncTaxTable.h:78-82`  
**Confidence:** High

**Plain English:** Tax table entries specify amounts as either an absolute currency value (GNC_AMT_TYPE_VALUE) or a percentage (GNC_AMT_TYPE_PERCENT).

**Given:** A tax table entry with an amount  
**When:** tax is computed for an entry  
**Then:** The amount is applied as value or percentage based on amount_type

**And:** taxtable.amount_type ∈ {VALUE, PERCENT}

**Parameters:** GNC_AMT_TYPE_VALUE=1 (absolute currency amount), GNC_AMT_TYPE_PERCENT (percentage)

**Edge Cases:**
- Enum starts at 1, not 0

---

### 24. Invoice Partial-Pay Application via Lot Balancing

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/gncInvoice.c:1728-1729, 259-263; libgnucash/engine/gncOwner.c:750, 1256`  
**Confidence:** High

**Plain English:** When a payment is applied to a posted invoice (via gncInvoiceApplyPayment or autopay), a payment lot is created, attached to the owner, and balanced against the invoice's posted lot. The invoice's 'paid' status flips to TRUE only when the posted_lot balance becomes zero; partial payments keep the invoice in 'open' state.

**Given:** A posted invoice whose lot is open (not yet fully paid)  
**When:** gncInvoiceApplyPayment or gncInvoiceAutoApplyPayments is called  
**Then:** Payment lot is created with TXN_TYPE_PAYMENT ('P'); link transaction may be created with TXN_TYPE_LINK ('L'); invoice.is_paid flips to TRUE when posted_lot balance reaches zero

**And:** invoice.posted_lot has attached splits with balances of opposite sign (payments vs document)

**Parameters:** none

**Edge Cases:**
- Partial payments keep the invoice in 'open' state — only full balance → paid

---

### 25. Euro Conversion Rates (Fixed)

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gnc-euro.cpp:32-55`  
**Confidence:** High

**Plain English:** Fixed conversion rates for legacy European currencies to EUR, as established by EU regulation. These rates are permanent and cannot be changed.

**Given:** A legacy European currency code (e.g., DEM, FRF, ITL)  
**When:** Converting to or from Euro  
**Then:** Use the fixed rate from the table: e.g., DEM=1.95583, FRF=6.55957, ITL=1936.27 (rates per 1 EUR)

**Parameters:** 20 currency rates hardcoded as GncNumeric fractions (e.g., {137603, 10000} for ATS)

**Edge Cases:**
- Returns zero for non-Euro currencies or invalid currency codes
- Rates are fixed by EU regulation and cannot be changed

---

### 26. Euro Conversion To EUR Formula

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gnc-euro.cpp:80-92`  
**Confidence:** High

**Plain English:** Converts a legacy currency amount to Euro by dividing by the fixed conversion rate, then rounding half-up to 2 decimal places per EC Regulation 1103/97.

**Given:** Amount V in legacy currency with conversion rate R  
**When:** Converting to Euro  
**Then:** Result = (V / R) rounded to 2 decimal places using RoundType::half_up

**Parameters:** V: gnc_numeric amount, R: GncNumeric conversion rate from table

**Edge Cases:**
- Returns zero if currency is not a Euro legacy currency
- Rounding per EC Regulation 1103/97 is half-away-from-zero

---

### 27. Euro Conversion From EUR Formula

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/gnc-euro.cpp:96-106`  
**Confidence:** Medium

**Plain English:** Converts a Euro amount to legacy currency by multiplying by the fixed conversion rate, then rounding half-up to the commodity's fractional precision per EC Regulation 1103/97.

**Given:** Amount V in EUR with conversion rate R and target currency fraction F  
**When:** Converting from Euro to legacy currency  
**Then:** Result = (V × R) rounded to F decimal places using RoundType::half_up, where F = gnc_commodity_get_fraction(currency)

**Parameters:** V: gnc_numeric EUR amount, R: GncNumeric conversion rate, F: commodity fraction (e.g., 100 for cents)

**Edge Cases:**
- Returns zero if currency is not a Euro legacy currency
- Uses commodity fraction for precision (e.g., 100 for cents)

**⚠️ SME Question:** P0 panel doubts spec fidelity: The Given/When/Then is NOT faithful to the code. The rule correctly identifies the operation (multiply value by rate, then round using half_up per EC Regulation 1103/97), but the precision parameter description is fundamentally wrong. The rule states "rounded to F decimal places using RoundType::half_up, where F = gnc_commodity_get_fraction(currency)" and gives the example "F: commodity fraction (e.g., 100 for cents)". This is incorrect: gnc_commodity_get_fraction returns the denominator (100), not the number of decimal places (2). The code at line 105 calls `.convert<RoundType::half_up>(gnc_commodity_get_fraction(currency))`, which converts to denominator F (100 for cents = 2 decimal places), not F decimal places. If implemented as "rounded to F decimal places" where F=100, the result would be absurd. The correct specification should state: "rounded to denominator F (where F is the commodity fraction, e.g., 100 for cents, representing 2 decimal places)" or "rounded to a precision of 1/F". This is a P0 rule because it involves money conversion under EC Regulation 1103/97, and the parameter description error would lead to incorrect implementation. The rounding mode (half_up = half away from zero) is correctly identified and matches the regulatory requirement.

---

### 28. Financial Calculator - Basic Equation

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/app-utils/calculation/fin.c:1236-1520`  
**Confidence:** Medium

**Plain English:** The fundamental time-value-of-money equation: PV*(1+i)^n + PMT*(1+i*X)*[(1+i)^n - 1]/i + FV = 0, where X=0 for end-of-period payments, X=1 for beginning-of-period payments.

**Given:** Present value PV, periodic payment PMT, future value FV, interest rate i per period, number of periods n, and payment timing X  
**When:** Solving any financial calculator problem  
**Then:** All five variables (n, i, PV, PMT, FV) are related by this equation; any one can be solved given the other four

**Parameters:** PV: present value, PMT: periodic payment, FV: future value, i: effective interest rate per period, n: number of periods, X: 0 or 1 for payment timing

**Edge Cases:**
- Handles both discrete and continuous compounding
- Special cases when i=0 or n=0 require careful handling
- X=0 for end-of-period, X=1 for beginning-of-period

**⚠️ SME Question:** Citation was corrected by referee (The rule is correctly implemented in the codebase. The equation PV*(1+i)^n + PMT*(1+i*X)*[(1+i)^n - 1]/i + FV = 0 is realized through helper functions _A, _B, _C (lines 1236-1258) and solver functions _fi_calc_present_value (1385-1399), _fi_calc_payment (1417-1433), _fi_calc_future_value (1451-1466), and fi() (1517-1520). However, the cited lines 293-408 are purely a block comment describing the mathematical derivation — they contain no executable code. The actual implementation is in the functions listed above.) — confirm libgnucash/app-utils/calculation/fin.c:1236-1520 is the authoritative implementation.

---

### 29. Financial Calculator - Effective Interest Rate Conversion

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/app-utils/calculation/fin.c:1493-1513`  
**Confidence:** Medium

**Plain English:** Converts nominal annual interest rate to effective rate per payment period, accounting for compounding frequency (CF) and payment frequency (PF).

**Given:** Nominal annual rate NAR, compounding frequency CF, payment frequency PF  
**When:** Preparing interest rate for financial calculations  
**Then:** For discrete compounding: ieff = (1 + NAR/CF)^(CF/PF) - 1; For continuous: ieff = exp(NAR/PF) - 1

**Parameters:** NAR: nominal annual rate (decimal), CF: compounding frequency per year (1-365), PF: payment frequency per year (1-365)

**Edge Cases:**
- CF and PF can differ (e.g., monthly compounding with quarterly payments)
- Continuous compounding uses exp() instead of power formula

**⚠️ SME Question:** Citation was corrected by referee (The cited lines 264-284 are only a documentation block comment describing the formulas — they contain no executable logic. The actual implementation is in the static function `eff_int` at lines 1493-1513 of the same file, which implements exactly the specified formulas: discrete `pow((1.0 + nint/CF), CF/PF) - 1.0` (with a CF==PF shortcut to `nint/CF`, which is algebraically equivalent) and continuous `exp(nint/PF) - 1.0`. Parameters match (NAR=nint, CF=CF, PF=PF). The rule is genuinely implemented, but the citation is wrong.) — confirm libgnucash/app-utils/calculation/fin.c:1493-1513 is the authoritative implementation.

---

### 30. Financial Calculator - Payment Calculation

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/app-utils/calculation/fin.c:1417-1433`  
**Confidence:** Medium

**Plain English:** Calculates the periodic payment required to fully amortize a loan: PMT = -[PV * i * (1+i)^(N-X)] / [(1+i)^N - 1], where X=0 for end-of-period, X=1 for beginning-of-period payments.

**Given:** Present value PV, interest rate i per period, number of periods N, payment timing X  
**When:** Computing loan payment for fully amortized loan (FV=0)  
**Then:** PMT = -[PV * i * (1+i)^(N-X)] / [(1+i)^N - 1]

**Parameters:** PV: loan amount, i: effective interest rate per period, N: total number of payments, X: 0 (end) or 1 (beginning)

**Edge Cases:**
- Returns payment that reduces balance to exactly zero after N payments
- Handles both beginning and end of period payments

**⚠️ SME Question:** Citation was corrected by referee (The cited lines 446-453 are comments describing the PMT formula, not executable code. The actual implementation is in the _fi_calc_payment function at lines 1417-1433. When FV=0, the code computes: PMT = -(pv * (AA + 1.0)) / (AA * BB) where AA = _A(eint, per) = (1+i)^N - 1 and BB = _B(eint, bep) = (1 + i*beg)/i. This simplifies to: PMT = -pv * i * (1+i)^N / [(1+i*beg) * ((1+i)^N - 1)]. For beg=0 (X=0): reduces to -PV * i * (1+i)^N / [(1+i)^N - 1]. For beg=1 (X=1): reduces to -PV * i * (1+i)^(N-1) / [(1+i)^N - 1]. Both match the claimed formula PMT = -[PV * i * (1+i)^(N-X)] / [(1+i)^N - 1]. The rule is correctly implemented but the citation points to documentation comments rather than the executable code.) — confirm libgnucash/app-utils/calculation/fin.c:1417-1433 is the authoritative implementation.

---

### 31. Lot Closure State Derivation - Balance Equals Zero

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/gnc-lot.cpp:486-524`  
**Confidence:** Medium

**Plain English:** A lot's closed state is derived from its balance: when balance computation results in zero, the lot is marked as closed; otherwise it's open. The is_closed flag is cached and recomputed when balance is queried.

**Given:** A lot with multiple splits  
**When:** gnc_lot_get_balance is called  
**Then:** The balance is computed by summing all split adjusted amounts; if the sum equals zero, is_closed is set to TRUE; otherwise is_closed is set to FALSE

**Parameters:** LOT_CLOSED_FALSE=0; LOT_CLOSED_TRUE=1; LOT_CLOSED_UNKNOWN=-1 (initial state)

**Edge Cases:**
- Empty lots (no splits) are marked as not closed with zero balance
- The is_closed flag is set to LOT_CLOSED_UNKNOWN when splits are added/removed, forcing recomputation on next balance query

**⚠️ SME Question:** P0 panel doubts spec fidelity: P0 is justified: lot closure state directly affects financial reporting and transaction settlement status - this guards data integrity. However, the rule text is NOT faithful to the code. Critical defect: The Given/When/Then specification states "if the sum equals zero, is_closed is set to TRUE" but the code has a special case at line 498 where an empty splits list (balance = zero) sets is_closed = FALSE, not TRUE. This edge case contradicts the specification. Additionally, the parameters list is misleading - LOT_CLOSED_FALSE and LOT_CLOSED_TRUE are not defined constants in the code; only LOT_CLOSED_UNKNOWN exists. The code uses GLib's TRUE/FALSE macros directly. The rule would fail verification against the actual implementation.

---

### 32. Split Void State Transition - Zero Amounts and VREC Flag

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/Split.cpp:2207-2230`  
**Confidence:** High

**Plain English:** When a split is voided, its amount and value are saved to KVP (void-former-amount, void-former-value), then set to zero, and reconciliation state is set to VREC. When unvoided, the former values are restored and reconciliation is set to NREC.

**Given:** A split with amount A and value V  
**When:** xaccSplitVoid is called  
**Then:** A and V are saved to KVP as void-former-amount and void-former-value; split amount and value are set to zero; reconciliation state is set to VREC (voided reconciled)

**Parameters:** NREC=n (not reconciled); VREC=V (voided reconciled state); void_former_amt_str=void-former-amount; void_former_val_str=void-former-value

**Edge Cases:**
- Unvoiding restores the exact former amounts and sets reconciliation to NREC
- The void former values are cleared from KVP after unvoiding

---

### 33. Transaction Void State Transition - Read-Only Guard

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/Transaction.cpp:2503-2573`  
**Confidence:** High

**Plain English:** Voiding a transaction saves the reason and timestamp to KVP, sets all splits to void state, marks the transaction as read-only with reason, and replaces notes with 'Voided transaction'. Unvoiding restores former notes and clears read-only status.

**Given:** A transaction that is not read-only  
**When:** xaccTransVoid is called with a reason  
**Then:** Current timestamp is saved to void_time_str KVP; reason is saved to void_reason_str KVP; current notes are saved to void_former_notes_str; notes are replaced with 'Voided transaction'; all splits are voided; transaction is marked read-only with void reason

**Parameters:** trans_notes_str=notes; void_former_notes_str=void-former-notes; void_reason_str=void-reason; void_time_str=void-time

**Edge Cases:**
- Voiding a read-only transaction is refused with a warning
- Void status is determined by checking if void_time_str KVP exists and is not INT64_MAX
- Unvoiding only works if transaction is actually voided

---

### 34. Auto-Read-Only Threshold Calculation

**Priority:** P0  
**Category:** Calculation  
**Source:** `libgnucash/engine/qofbook.cpp:1006-1018`  
**Confidence:** Medium

**Plain English:** The auto-read-only threshold date is calculated by subtracting the configured number of days from today's date

**Given:** A book with auto-read-only enabled and num_days configured  
**When:** Calculating the read-only threshold date  
**Then:** threshold_date = today - num_days

**Parameters:** num_days = from book KVP 'autoreadonly-days' (double stored as cached gint)

**Edge Cases:**
- num_days is cached after first access; must be >0 to enable auto-read-only

**⚠️ SME Question:** P0 panel doubts spec fidelity: P0 justified: This rule guards data integrity by controlling which transactions become read-only based on age. However, the Given/When/Then is incomplete. The code only calculates threshold_date = today - num_days when num_days > 0. When num_days <= 0 (a valid state per the parameter spec showing min=0), the function returns nullptr (no threshold), not a calculated date. This edge case must be explicit for P0 verification. The core calculation and parameter source are correct, but the rule fails to specify the conditional logic and nullptr return behavior.

---

### 35. Transaction Auto-Read-Only Check

**Priority:** P0  
**Category:** Validation  
**Source:** `libgnucash/engine/Transaction.cpp:2373-2409`  
**Confidence:** High

**Plain English:** A transaction is read-only if auto-read-only is enabled, the transaction is not an SX template, and the transaction date is before the threshold date

**Given:** A transaction and book with auto-read-only enabled  
**When:** Checking if the transaction is read-only  
**Then:** Return true if: uses_autoreadonly(book) AND NOT isSXTemplate(trans) AND trans_date < threshold_date

**Parameters:** Threshold from qof_book_get_autoreadonly_gdate

**Edge Cases:**
- SX template transactions are always editable even if older than threshold

---

### 36. Rational Number - Overflow Detection in Division

**Priority:** P0  
**Category:** Validation  
**Source:** `libgnucash/engine/gnc-rational.cpp:318-321`  
**Confidence:** High

**Plain English:** Division checks for overflow after computing numerator and denominator; throws overflow_error if either is invalid

**Given:** Division operation with large operands  
**When:** Computing result = (a_num * b_den) / (a_den * b_num)  
**Then:** If numerator or denominator overflow, throw std::overflow_error('Operator/ overflowed.')

**Parameters:** Overflow checked via GncInt128::valid() on computed num and den

---

### 37. CSV Transaction Import: Required Columns

**Priority:** P0  
**Category:** Validation  
**Source:** `gnucash/import-export/csv-imp/gnc-import-tx.cpp:503-531`  
**Confidence:** High

**Plain English:** A CSV transaction import cannot proceed unless the user has selected a date column, a description column, and at least one of (amount, amount_neg); an account column OR a base account is also required (account column mandatory in multi-split mode).

**Given:** A CSV import configuration  
**When:** verify_column_selections runs  
**Then:** errors are reported for each missing required column: DATE, DESCRIPTION, one of AMOUNT/AMOUNT_NEG; ACCOUNT (multi-split) or ACCOUNT or base_account (single-split)

---

### 38. CSV Transaction Import: Multi-Currency Requires Price or Value

**Priority:** P0  
**Category:** Validation  
**Source:** `gnucash/import-export/csv-imp/gnc-import-tx.cpp:542-556`  
**Confidence:** High

**Plain English:** When the CSV import detects multi-currency transactions (accounts with differing commodities), the user must supply a price column, a value (or negated value) column, and in single-split mode also a transfer amount column, so that each split's foreign-currency amount can be fully determined.

**Given:** m_multi_currency == true  
**When:** verify_column_selections runs  
**Then:** in multi-split mode: requires PRICE or VALUE or VALUE_NEG; in single-split mode: requires PRICE or VALUE or VALUE_NEG or TAMOUNT or TAMOUNT_NEG

---

### 39. Import Match Score Thresholds and Auto-Actions

**Priority:** P0  
**Category:** Policy  
**Source:** `gnucash/import-export/import-backend.cpp:763-774;1176-1193;gnucash/gschemas/org.gnucash.GnuCash.dialogs.import.generic.gschema.xml.in:18-47`  
**Confidence:** Medium

**Plain English:** Match scores are bucketed: below display_threshold (default 1.0) the match is not shown; above auto_clear_threshold (default 6.0) it is auto-cleared (or auto-updated if update enabled and proposed); at or below auto_add_threshold (default 3.0) the transaction is auto-added as new; between the two the configured fallback action (skip, update, add) applies.

**Given:** A best match with probability P  
**When:** gnc_import_TransInfo_init_matches decides the default action  
**Then:** P >= 6 -> GNCImport_CLEAR (or UPDATE if update_proposed); P <= 3 -> GNCImport_ADD; else -> SKIP/UPDATE/ADD per user preference

**Parameters:** display_threshold=1.0, date_threshold=4.0, date_not_threshold=14.0, auto_add_threshold=3.0, auto_clear_threshold=6.0, atm_fee_threshold=2.0, hard-limit date=42 days

**⚠️ SME Question:** P0 panel doubts spec fidelity: This rule IS P0 because it guards data integrity in bank transaction import: auto-clear marks existing book transactions as reconciled (prob ≥ 6.0), auto-add creates new ledger entries (prob ≤ 3.0). Silent changes would cause duplicate entries (double-counted money), missed entries (unrecorded money), or false reconciliation status — all material to financial record accuracy and audit trails. A regulator/auditor would absolutely care. The core threshold logic is FAITHFUL to the code at import-backend.cpp:1176-1193. However, the rule contains one error: it claims "hard-limit date=42 days" which does NOT exist in the code. The comment at line 659 explicitly states "Changed 2005-02-21: Revert the hard-limiting behaviour back to the previous large penalty" — the code now applies a -5 probability penalty for datediff_day > date_not_threshold (14 days) but continues evaluation, with no hard cutoff. The date_threshold (4 days) and date_not_threshold (14 days) are day-difference values that feed into probability calculation, not probability scores themselves. The rule conflates these dimensions in its parameter list. | This is a legitimate P0 rule: it controls automated transaction matching behavior that directly affects data integrity during bank imports. Incorrect thresholds or logic could cause transactions to be auto-cleared when they should be reviewed, or auto-added when they should be matched to existing transactions, leading to duplicate entries or incorrect account states. However, the rule specification has defects: (1) The UPDATE condition for P >= 6 is incomplete - requires BOTH action_update_enabled AND update_proposed, not just update_proposed; (2) The 'hard-limit date=42 days' parameter is incorrect - this behavior was reverted in 2005 and no longer exists in the code. The code uses a -5 probability penalty instead.

---

### 40. OFX Import: Required Transaction Fields

**Priority:** P0  
**Category:** Validation  
**Source:** `gnucash/import-export/ofx/gnc-ofx-import.cpp:922-932`  
**Confidence:** High

**Plain English:** An OFX transaction is rejected (skipped) unless it has a valid amount AND a valid account ID. Both conditions are checked before any account selection occurs.

**Given:** An OfxTransactionData from libofx  
**When:** ofx_proc_transaction_cb runs  
**Then:** if !data.amount_valid -> skip with PERR; if !data.account_id_valid -> skip with PERR

---

### 41. Feature Flags: Unknown Feature Blocks Book Open

**Priority:** P0  
**Category:** Validation  
**Source:** `libgnucash/engine/gnc-features.cpp:82-105`  
**Confidence:** High

**Plain English:** When a book is opened, any feature-flag recorded in the book's KVP that is not in the current version's known features_table causes the open to fail with a message listing the unknown features. Obsolete features (previously known but now removed) are auto-erased from the KVP instead of blocking.

**Given:** A book with feature-flags set in KVP  
**When:** gnc_features_test_unknown runs  
**Then:** features not in features_table AND not in obsolete_features -> return localized error message; obsolete features -> qof_book_unset_feature removes them

**Parameters:** Known features: see gnc-features.cpp:36-48 (Credit Notes, Number Field Source, Extra data in addresses, GUID Bayesian, GUID Flat Bayesian, SQLite3 ISO Dates, Register Sort/Filter, Budget Unreversed, Budget Extra Cols, Equity Type Opening Balance)

---

### 42. Lot Splits Must Be Same Account

**Priority:** P0  
**Category:** Validation  
**Source:** `libgnucash/engine/gnc-lot.cpp:578-606`  
**Confidence:** Medium

**Plain English:** Adding a split to a lot rejects the operation if the split's account differs from the lot's existing account.

**Given:** a lot with account A  
**When:** gnc_lot_add_split is called with a split whose account is B (!= A)  
**Then:** the split is not added; an error is logged

**Parameters:** lot->account: Account*; split->account via xaccSplitGetAccount

**⚠️ SME Question:** P0 panel doubts spec fidelity: The rule is mostly faithful but has critical gaps:

**Faithfulness issues:**
1. **Function signature is void** - The rule says "rejects the operation" but gnc_lot_add_split() returns void. The caller receives no programmatic error signal; the only indication is a PERR log message (line 599-602). The split is not added, correct, but "rejects" implies the caller knows it failed.

2. **Missing the happy path for new lots** - Lines 593-596 handle when priv->account is null: the lot's account is SET to the split's account via xaccAccountInsertLot(). The rule only describes the rejection case, not this account-assignment case.

3. **Hidden side effects in error path** - Even when rejecting (lines 597-606), the code calls qof_instance_set_dirty() on line 592 (BEFORE the check) and gnc_lot_commit_edit() on line 603. So the lot is marked dirty and an edit transaction is committed even though nothing was added. This is a subtle data integrity issue.

4. **Given/When/Then is incomplete** - The specification says "the split is not added; an error is logged" but doesn't capture that the lot's dirty state is set and an edit is committed even on rejection.

**P0 justification:**
YES, this is genuinely P0. This enforces a fundamental data integrity invariant: all splits in a lot must belong to the same account. In double-entry bookkeeping, a lot groups related splits (for FIFO/LIFO, lot-based inventory tracking). Mixing accounts within a lot would corrupt the accounting model. This is not just a technical check - it's a business rule that guards the integrity of financial data.

**Recommendation:**
The rule text should be revised to:
- Clarify the function is void (no error return to caller)
- Mention the case where a lot with no account gets assigned the split's account
- Note that dirty state and edit commit occur even on rejection
- State: "Given a lot with account A and split with account B where A != B: the split is not added to the lot's splits list; an error is logged via PERR; however, the lot is still marked dirty and an edit transaction is committed"

---

### 43. Scrub Business - Double-Post Detection

**Priority:** P0  
**Category:** Validation  
**Source:** `libgnucash/engine/ScrubBusiness.c:547-568`  
**Confidence:** High

**Plain English:** A split belonging to a read-only, non-voided transaction of type TXN_TYPE_NONE that is assigned to a lot is recognized as a double-post artifact; the scrub clears read-only, detaches the split from the lot, and stamps a deletion-request memo.

**Given:** a split whose transaction is (read_only=TRUE, void=FALSE, txn_type=TXN_TYPE_NONE, assigned to a lot)  
**When:** gncScrubBusinessSplit is called  
**Then:** xaccTransClearReadOnly is called, split memo is set to a deletion warning, and the split is removed from the lot

**Parameters:** Txn-type TXN_TYPE_NONE is the trigger signature for historical double-post bug 754209

---

### 44. Scrub Business - Invoice State Correction

**Priority:** P0  
**Category:** Validation  
**Source:** `libgnucash/engine/ScrubBusiness.c:51-83`  
**Confidence:** High

**Plain English:** For each lot, the scrub verifies that the invoice associated via a split's transaction matches the invoice recorded on the lot KVP; if they disagree, the lot's invoice KVP is reattached to match the split-derived invoice.

**Given:** a lot whose split-derived invoice differs from lot's cached invoice  
**When:** gncScrubInvoiceState is called  
**Then:** the lot's invoice association is corrected to the split-derived invoice (or detached if no split-derived invoice exists, falling back to owner attachment)

**Parameters:** gncInvoiceDetachFromLot, gncInvoiceAttachToLot, gncOwnerAttachToLot

---

### 45. Invoice Unpost Destroys Link Transactions and Re-Balances Lots

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/gncInvoice.c:1736-1872`  
**Confidence:** High

**Plain English:** Unposting an invoice destroys the posted transaction, detaches the lot from the invoice, re-attaches the lot to the owner, destroys every TXN_TYPE_LINK transaction that linked this lot to other lots, and calls gncOwnerAutoApplyPaymentsWithLots on the remaining lots to re-balance. Lots left empty are destroyed. Optionally resets entry tax tables to parent tax tables.

**Given:** a posted invoice with a lot linked to 2 payment lots via link transactions  
**When:** gncInvoiceUnpost(invoice, TRUE) is called  
**Then:** posted_txn is destroyed, lot is detached from invoice, each link transaction is destroyed, remaining lots are re-balanced via auto-apply, entry tax tables reset to parent, posted_txn/lot/acc cleared, date_posted = INT64_MAX

**Parameters:** reset_tax_tables: gboolean; when TRUE, entry tax tables are replaced with their parent tables

---

### 46. Transaction Void State Machine

**Priority:** P0  
**Category:** Lifecycle  
**Source:** `libgnucash/engine/Transaction.cpp:2503-2531`  
**Confidence:** High

**Plain English:** Voiding a transaction: preserves the current notes as 'void-former-notes', replaces notes with 'Voided transaction', stores the void reason and ISO-8601 timestamp, zeros each split via xaccSplitVoid, and marks the transaction read-only with reason 'Transaction Voided'.

**Given:** a non-read-only transaction with notes 'Payment for services'  
**When:** xaccTransVoid(trans, 'Duplicate entry') is called  
**Then:** KVP 'notes' = 'Voided transaction', KVP 'void-former-notes' = 'Payment for services', KVP 'void-reason' = 'Duplicate entry', KVP 'void-time' = current ISO-8601 time, each split is zeroed, trans is marked read-only

**Parameters:** void_reason_str, void_time_str, void_former_notes_str KVP keys; read-only reason 'Transaction Voided'

---

### 47. Transaction Void Blocked By Read-Only

**Priority:** P0  
**Category:** Validation  
**Source:** `libgnucash/engine/Transaction.cpp:2510-2514`  
**Confidence:** High

**Plain English:** Voiding refuses to operate on any transaction already marked read-only (e.g. from invoice post); the request is silently dropped with a PWARN.

**Given:** a transaction with read-only KVP set (e.g. posted invoice transaction)  
**When:** xaccTransVoid is called  
**Then:** returns immediately without modifying the transaction

**Parameters:** xaccTransGetReadOnly check; returns non-NULL const char* reason

---

## P1 Rules (Important — Business Logic)

*164 rules omitted for brevity. See full JSON in workflow output.*

## P2 Rules (Display / Formatting)

*26 rules omitted for brevity.*

---

**Full data:** Workflow output at `/tmp/claude-1000/-projects-gnucash/4167734d-62b3-4401-8a66-a376364623af/tasks/w0yisof7f.output`
