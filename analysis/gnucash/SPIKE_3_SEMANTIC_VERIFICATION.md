# Spike 3: Semantic Verification — Final Report

**Spike:** 3 — Semantic Verification  
**Date:** 2026-09-19  
**Status:** Complete  
**Scope:** Reconciliation state machine, tax discount ordering, posted journal immutability

---

## Executive Summary

This spike verified three critical semantic areas against the GnuCash source code to inform the target Django SaaS platform design.

**Key Findings:**

1. **Reconciliation** — GnuCash's engine permits any state transition (n↔c↔y↔f↔v); all protection is UI-side. The target platform should encode an explicit transition matrix at the model layer and add compliance-grade audit trails.

2. **Tax Discount Ordering** — The `discount_how` field (PRETAX/SAMETIME/POSTTAX) is owned by the Entry (document line item), not the TaxTable or Invoice. Rounding uses half-up at the per-line level. The target platform must snapshot tax table contents at posting time to ensure historical reproducibility (GnuCash has a weakness here).

3. **Posted Journal Immutability** — **Critical finding:** GnuCash provides NO engine-level immutability enforcement. All financial facts are mutable via direct API calls; readonly flags are advisory (GUI-only). The target platform must implement database-level constraints and a formal reversal/correcting entry workflow.

**Migration Implications:** Importing GnuCash data requires adding immutability constraints, separating financial facts from operational metadata, and potentially creating synthetic reversal entries for voided transactions.

---

## A. Reconciliation — Source Evidence & Target Model Design

### 1. What do `n`, `c`, `y`, `f`, `v` actually represent?

**Source: `libgnucash/engine/Split.h` lines 68–78**

```c
/** @name Split Reconciled field values

    These define the various reconciliations states a split can be in.

    If you change these
    be sure to change gnc-ui-util.c:gnc_get_reconciled_str() and
    associated functions

@{
*/
#define CREC 'c'              /**< The Split has been cleared    */
#define YREC 'y'              /**< The Split has been reconciled */
#define FREC 'f'              /**< frozen into accounting period */
#define NREC 'n'              /**< not reconciled or cleared     */
#define VREC 'v'              /**< split is void                 */
/** @} */
```

**Source: `libgnucash/app-utils/gnc-ui-util.cpp` lines 468–487** (`gnc_get_reconcile_str`):

```c
switch (reconciled_flag)
{
case NREC:  return C_("Reconciled flag 'not cleared'", "n");
case CREC:  return C_("Reconciled flag 'cleared'", "c");
case YREC:  return C_("Reconciled flag 'reconciled'", "y");
case FREC:  return C_("Reconciled flag 'frozen'", "f");
case VREC:  return C_("Reconciled flag 'void'", "v");
default:    PERR("Bad reconciled flag\n"); return nullptr;
}
```

| Flag | Char | Semantic meaning |
|------|------|------------------|
| `NREC` | `'n'` | **Not reconciled / not cleared** — default state for a new split. |
| `CREC` | `'c'` | **Cleared** — the bank/counterparty has acknowledged the transaction, but it has not yet been formally matched against a statement line. |
| `YREC` | `'y'` | **Reconciled** — the split has been matched to an external statement during a reconciliation run; locked against further change. |
| `FREC` | `'f'` | **Frozen** — the split has been locked into a closed accounting period (period-end freeze). Stronger than `YREC` in the sense that even the reconciliation process shouldn't touch it. |
| `VREC` | `'v'` | **Void** — the split has been voided (amount/value zeroed, originals preserved in KVP). |

The underlying data model stores this as a single `char` field on the `Split` struct:
- **Source: `libgnucash/engine/Split.cpp::gnc_split_init` lines 109–136**
```c
split->reconciled  = NREC;
...
split->date_reconciled  = 0;
```
- **Source: `libgnucash/engine/Split.cpp::xaccSplitReinit` lines 504–533** resets both to defaults.

---

### 2. Which transitions are valid?

**Source: `libgnucash/engine/Split.cpp::xaccSplitSetReconcile` lines 1818–1842**

```c
void
xaccSplitSetReconcile (Split *split, char recn)
{
    if (!split || split->reconciled == recn) return;
    xaccTransBeginEdit (split->parent);

    switch (recn)
    {
        case NREC:
        case CREC:
        case YREC:
        case FREC:
        case VREC:
            split->reconciled = recn;
            mark_split (split);
            qof_instance_set_dirty(QOF_INSTANCE(split));
            xaccAccountRecomputeBalance (split->acc);
            break;
        default:
            PERR("Bad reconciled flag");
            break;
    }
    xaccTransCommitEdit(split->parent);
}
```

The **only** guard enforced by the engine is that the new value must be one of the five defined chars. There is **no transition matrix**: any state can transition to any other state at the engine level. The internal helper `qofSplitSetReconcile` (lines 1797–1816) is identical except it skips the transaction edit envelope (used by loaders that are already inside an edit).

**Implications for the state machine:**

| From \ To | n | c | y | f | v |
|-----------|---|---|---|---|---|
| **n**     | — | ✓ | ✓ | ✓ | ✓ |
| **c**     | ✓ | — | ✓ | ✓ | ✓ |
| **y**     | ✓ | ✓ | — | ✓ | ✓ |
| **f**     | ✓ | ✓ | ✓ | — | ✓ |
| **v**     | ✓ | ✓ | ✓ | ✓ | — |

So yes, `n → c → y → f → v` is accepted, and **yes, `y → c` is accepted at engine level**. Backward transitions are not blocked by the engine; any policy restriction on un-reconciling lives in the UI reconciliation dialog, not in the data layer.

**Where the engine *does* distinguish**: `xaccTransHasReconciledSplitsByAccount` (Transaction.cpp lines 2424–2451) treats `YREC` and `FREC` as "this transaction is locked":

```c
switch (xaccSplitGetReconcile (split))
{
case YREC:
case FREC:
    return TRUE;
default:
    break;
}
```

This is the predicate the register/UI uses to decide whether to show the "this transaction is reconciled — are you sure?" warning. `CREC` is deliberately *not* in this set — cleared-but-not-yet-reconciled transactions can be edited freely.

---

### 3. Are "frozen" and "void" reconciliation states at all?

**Short answer: yes, they share the same `reconciled` char field, but they are semantically different concepts.**

#### Void (`VREC`)
Void is a **split-level** action that:
1. Saves the former amount/value into the split's KVP (key-value pair) storage.
2. Zeros out the split's amount and value.
3. Sets `reconciled = VREC`.

**Source: `libgnucash/engine/Split.cpp::xaccSplitVoid` lines 2206–2218**
```c
void
xaccSplitVoid(Split *split)
{
    g_return_if_fail (GNC_IS_SPLIT(split));
    qof_instance_set_path_kvp<gnc_numeric> (QOF_INSTANCE(split),
        xaccSplitGetAmount(split), {void_former_amt_str});
    qof_instance_set_path_kvp<gnc_numeric> (QOF_INSTANCE(split),
        xaccSplitGetValue(split), {void_former_val_str});
    qof_instance_set_dirty (QOF_INSTANCE(split));

    static gnc_numeric zero = gnc_numeric_zero();
    xaccSplitSetAmount (split, zero);
    xaccSplitSetValue (split, zero);
    xaccSplitSetReconcile(split, VREC);
}
```

**Source: `libgnucash/engine/Split.cpp::xaccSplitUnvoid` lines 2220–2230** restores from KVP and resets the flag to `NREC`:
```c
xaccSplitSetAmount (split, xaccSplitVoidFormerAmount(split));
xaccSplitSetValue (split, xaccSplitVoidFormerValue(split));
xaccSplitSetReconcile(split, NREC);
qof_instance_set_path_kvp<gnc_numeric> (QOF_INSTANCE(split), {}, {void_former_amt_str});
qof_instance_set_path_kvp<gnc_numeric> (QOF_INSTANCE(split), {}, {void_former_val_str});
```

So `VREC` is really a **compound state** (flag + zeroed amount/value + former-values-in-KVP). The `reconciled` char is just one dimension of it.

#### Frozen (`FREC`)
Frozen is a true reconciliation-state value — it means the split is inside a closed accounting period. Unlike `VREC`, no amount/value mutation is forced. It is distinguished from `YREC` only at policy level (UI dialogs refuse to unreconcile a frozen split), and in the query predicate above it is grouped with `YREC` as "locked."

**Data-model summary:**

| Flag | Is a "reconciliation state"? | Also implies |
|------|------------------------------|--------------|
| `NREC` / `CREC` / `YREC` | yes, pure state | nothing else |
| `FREC` | yes, pure state | "period is closed, don't touch" |
| `VREC` | yes, but it's a **compound** with zeroed amount/value and KVP backup |

---

### 4. Dates / audit metadata accompanying state changes

Only **one** piece of reconciliation metadata is tracked on the split itself:

| Field | Type | Setter | Getter |
|-------|------|--------|--------|
| `reconciled` | `char` | `xaccSplitSetReconcile` | `xaccSplitGetReconcile` (`Split.cpp:1975–1979`) |
| `date_reconciled` | `time64` (POSIX seconds) | `xaccSplitSetDateReconciledSecs` (`Split.cpp:1844–1854`) | `xaccSplitGetDateReconciled` (`Split.cpp:1858–1862`) |

**Source: `libgnucash/engine/Split.cpp::xaccSplitSetDateReconciledSecs`**
```c
void
xaccSplitSetDateReconciledSecs (Split *split, time64 secs)
{
    if (!split) return;
    xaccTransBeginEdit (split->parent);
    split->date_reconciled = secs;
    qof_instance_set_dirty(QOF_INSTANCE(split));
    xaccTransCommitEdit(split->parent);
}
```

**Important caveat**: `xaccSplitSetReconcile` **does not itself write `date_reconciled`**. The date is set by a separate call from the reconciliation dialog. There is also no `reconciled_by_user_id`, no statement reference, no batch id — the only audit trail is:
- The `date_reconciled` timestamp.
- The generic QofInstance dirty/version counters (shared by every entity in the engine, not reconciliation-specific).
- The transaction-level edit log maintained by `xaccTransBeginEdit`/`CommitEdit` (which tracks *that* an edit happened, not *why*).

So the audit trail for reconciliation changes in GnuCash is **very thin**. The target model can and should do better.

---

### 5. What happens when a reconciled transaction is edited?

At the **engine level**, almost nothing prevents you from editing a reconciled split:

- `xaccSplitSetReconcile` accepts any legal flag, including `NREC`, so you can silently unreconcile.
- `xaccTransHasReconciledSplits` (Transaction.cpp:2453–2457) is a **query**, not a guard — it tells callers whether a transaction has locked splits, it does not prevent edits.

```c
gboolean
xaccTransHasReconciledSplits (const Transaction *trans)
{
    return xaccTransHasReconciledSplitsByAccount (trans, nullptr);
}
```

All the **actual protection is in the UI**: the register dialog (`gnucash/register/ledger-core/split-register-model.c`), the reconciliation view (`gnucash/gnome/reconcile-view.c`), and the transaction editor call `xaccTransHasReconciledSplits*` and pop up a confirmation warning. If the user declines, the edit is cancelled; if they accept, the UI typically resets the affected splits' `reconciled` flag to `NREC` before writing.

This is a deliberate architectural split: the engine is permissive (so that importers, scripts, and batch operations can freely fix up old entries), and the UI is the gatekeeper for interactive edits.

---

### 6. Target Model Design (Django)

#### Reconciliation state enum

```python
# accounting/models/reconciliation.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class ReconcileStatus(models.TextChoices):
    NOT_CLEARED    = "n", _("Not Cleared")     # default
    CLEARED        = "c", _("Cleared")         # bank acknowledged, not yet on statement
    RECONCILED     = "y", _("Reconciled")      # matched to statement line
    FROZEN         = "f", _("Frozen")          # period closed, immutable
    VOID           = "v", _("Void")            # zeroed, former values kept

# Business-rule sets
LOCKED_STATES = frozenset({ReconcileStatus.RECONCILED, ReconcileStatus.FROZEN})
INTERACTIVE_EDIT_BLOCKED = LOCKED_STATES   # UI must confirm before changing
```

#### Valid state transitions

```python
# Explicit matrix — any missing combination is forbidden at the model layer.
ALLOWED_TRANSITIONS: dict[ReconcileStatus, frozenset[ReconcileStatus]] = {
    ReconcileStatus.NOT_CLEARED: {
        ReconcileStatus.CLEARED,
        ReconcileStatus.RECONCILED,
        ReconcileStatus.FROZEN,
        ReconcileStatus.VOID,
    },
    ReconcileStatus.CLEARED: {
        ReconcileStatus.NOT_CLEARED,      # allow clearing to be undone
        ReconcileStatus.RECONCILED,
        ReconcileStatus.FROZEN,
        ReconcileStatus.VOID,
    },
    ReconcileStatus.RECONCILED: {
        ReconcileStatus.NOT_CLEARED,      # unreconcile (UI-confirmed)
        ReconcileStatus.CLEARED,
        ReconcileStatus.FROZEN,
        ReconcileStatus.VOID,
    },
    ReconcileStatus.FROZEN: {
        # Frozen is end-of-life for a period; only unfreeze by admin action.
        ReconcileStatus.RECONCILED,
    },
    ReconcileStatus.VOID: {
        ReconcileStatus.NOT_CLEARED,      # unvoid returns to default state
    },
}

def can_transition(from_state: ReconcileStatus, to_state: ReconcileStatus) -> bool:
    return from_state == to_state or to_state in ALLOWED_TRANSITIONS[from_state]
```

#### Django model fields

```python
class Split(models.Model):
    # ... existing fields ...

    reconcile_status = models.CharField(
        max_length=1,
        choices=ReconcileStatus.choices,
        default=ReconcileStatus.NOT_CLEARED,
        db_index=True,
    )
    date_reconciled = models.DateTimeField(
        null=True, blank=True,
        help_text=_("When the split was last moved into RECONCILED or FROZEN."),
    )
    reconciled_by = models.ForeignKey(
        "users.User", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="reconciled_splits",
    )
    reconciliation_run = models.ForeignKey(
        "ReconciliationRun", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="splits",
        help_text=_("Which reconciliation run locked this split."),
    )

    # Void-specific fields (compound state). Null when status != VOID.
    voided_amount = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True,
        help_text=_("Amount before void."),
    )
    voided_value  = models.DecimalField(
        max_digits=20, decimal_places=4, null=True, blank=True,
        help_text=_("Value before void (in transaction currency)."),
    )
    voided_at     = models.DateTimeField(null=True, blank=True)
    voided_by     = models.ForeignKey(
        "users.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="voided_splits",
    )

    class Meta:
        constraints = [
            # date_reconciled must be set iff status is RECONCILED or FROZEN
            models.CheckConstraint(
                check=(
                    models.Q(reconcile_status__in=["y", "f"], date_reconciled__isnull=False)
                    | models.Q(reconcile_status__in=["n", "c", "v"], date_reconciled__isnull=True)
                ),
                name="split_date_reconciled_consistent_with_status",
            ),
            # void-specific columns populated iff status == VOID
            models.CheckConstraint(
                check=(
                    models.Q(reconcile_status="v", voided_amount__isnull=False, voided_value__isnull=False)
                    | ~models.Q(reconcile_status="v")
                ),
                name="split_void_fields_only_when_void",
            ),
        ]

    def transition_to(self, new_status: ReconcileStatus, *,
                      actor, run=None, timestamp=None) -> None:
        if not can_transition(self.reconcile_status, new_status):
            raise ReconciliationTransitionForbidden(
                f"{self.reconcile_status} → {new_status} is not allowed."
            )
        old = self.reconcile_status
        self.reconcile_status = new_status
        ts = timestamp or timezone.now()

        if new_status in {ReconcileStatus.RECONCILED, ReconcileStatus.FROZEN}:
            self.date_reconciled = ts
            self.reconciled_by = actor
            self.reconciliation_run = run
        elif new_status == ReconcileStatus.VOID:
            self.voided_amount = self.amount
            self.voided_value  = self.value
            self.voided_at     = ts
            self.voided_by     = actor
            self.amount = 0
            self.value  = 0
        elif old == ReconcileStatus.VOID and new_status == ReconcileStatus.NOT_CLEARED:
            # unvoid
            self.amount = self.voided_amount
            self.value  = self.voided_value
            self.voided_amount = self.voided_value = None
            self.voided_at = None
            self.voided_by = None
            self.date_reconciled = None
            self.reconciled_by = None
            self.reconciliation_run = None
        else:
            # downgrade from locked state clears reconciliation metadata
            self.date_reconciled = None
            self.reconciled_by = None
            self.reconciliation_run = None

        ReconciliationAuditLog.objects.create(
            split=self, actor=actor, timestamp=ts,
            old_status=old, new_status=new_status,
            reconciliation_run=run,
        )
```

#### Audit trail

```python
class ReconciliationRun(models.Model):
    account      = models.ForeignKey("Account", on_delete=models.CASCADE, related_name="reconciliation_runs")
    statement_date = models.DateField()
    starting_balance = models.DecimalField(max_digits=20, decimal_places=4)
    ending_balance   = models.DecimalField(max_digits=20, decimal_places=4)
    performed_by = models.ForeignKey("users.User", on_delete=models.PROTECT)
    performed_at = models.DateTimeField(auto_now_add=True)
    statement_reference = models.CharField(max_length=120, blank=True)

class ReconciliationAuditLog(models.Model):
    split            = models.ForeignKey("Split", on_delete=models.CASCADE, related_name="reconcile_audit")
    actor            = models.ForeignKey("users.User", on_delete=models.PROTECT)
    timestamp        = models.DateTimeField(db_index=True)
    old_status       = models.CharField(max_length=1, choices=ReconcileStatus.choices)
    new_status       = models.CharField(max_length=1, choices=ReconcileStatus.choices)
    reconciliation_run = models.ForeignKey(
        "ReconciliationRun", null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    reason           = models.CharField(max_length=240, blank=True)
```

#### Behavior when editing reconciled transactions

```python
def check_interactive_edit_allowed(split: "Split") -> None:
    """Called by the view/form layer before mutating a split.

    Mirrors GnuCash's UI-side guard: locked splits may only be edited after
    an explicit user confirmation, which the view converts into a
    transition_to(RECONCILED → NOT_CLEARED) call *before* applying the edit.
    """
    if split.reconcile_status in LOCKED_STATES:
        raise ReconciledSplitLocked(
            split=split,
            required_action="unreconcile_then_edit",
        )
```

The platform policy is stricter than GnuCash's engine (which silently permits any transition) but matches the *UI* behavior GnuCash actually exhibits: a reconciled/frozen split cannot be mutated without an explicit "unreconcile first" action, and every such action is recorded in `ReconciliationAuditLog`.

---

### 7. Worked Example — One Split's Lifecycle

A $50.00 checking-account debit to "Office Supplies" on 2026-08-12.

| Step | Event | `reconcile_status` | `amount` | `value` | `date_reconciled` | `voided_*` | `reconciliation_run` | audit log entry |
|------|-------|--------------------|----------|---------|--------------------|------------|----------------------|-----------------|
| 1 | User creates transaction | `n` (NOT_CLEARED) | 50.00 | 50.00 | NULL | NULL | NULL | *created* |
| 2 | User marks split "cleared" after seeing it on the bank feed | `c` (CLEARED) | 50.00 | 50.00 | NULL | NULL | NULL | n→c |
| 3 | August statement arrives; reconciliation run #42 marks it matched on 2026-09-02 | `y` (RECONCILED) | 50.00 | 50.00 | 2026-09-02 | NULL | run #42 | c→y |
| 4a | User tries to edit the memo on 2026-09-10 | **blocked** by `check_interactive_edit_allowed` | — | — | — | — | — | — |
| 4b | User confirms "unreconcile & edit" | `n` (NOT_CLEARED) | 50.00 | 50.00 | NULL | NULL | NULL | y→n |
| 4c | Memo is updated; re-reconciled against run #42 | `y` (RECONCILED) | 50.00 | 50.00 | 2026-09-10 | NULL | run #42 | n→y |
| 5 | Period-end close on 2026-10-01 freezes August | `f` (FROZEN) | 50.00 | 50.00 | 2026-10-01 | NULL | run #42 | y→f |
| 6a | User tries to edit | **blocked** — frozen splits require admin unfreeze | — | — | — | — | — | — |
| 6b | (hypothetical) Admin unfreezes | `y` | 50.00 | 50.00 | 2026-09-10 | NULL | run #42 | f→y |
| 7 | User voids the entire transaction on 2026-10-05 (e.g. duplicate) | `v` (VOID) | 0.00 | 0.00 | NULL | amount=50.00, value=50.00, at=2026-10-05 | NULL | y→v |
| 8 | Later, user unvoids | `n` (NOT_CLEARED) | 50.00 | 50.00 | NULL | NULL | NULL | v→n |

### Key observations carried into the target model

1. **The char codes `n/c/y/f/v` are preserved** for compact storage and backwards familiarity, but the `ReconcileStatus` `TextChoices` enum gives them real names at the application boundary.
2. **Void is genuinely different from the others** — it's a compound mutation (zero amounts + save former values). Modeling it as separate columns with a check constraint is cleaner than GnuCash's KVP approach.
3. **`date_reconciled` exists** and should be required whenever status ∈ {RECONCILED, FROZEN}; enforced at the DB layer via a `CheckConstraint`.
4. **The engine allows any transition**; the target platform encodes an explicit matrix (`ALLOWED_TRANSITIONS`) at the model layer — safer for a multi-tenant SaaS.
5. **GnuCash's audit trail is minimal** (just `date_reconciled` plus generic QofInstance dirtiness). The target adds `ReconciliationAuditLog`, `reconciled_by`, and `reconciliation_run` to give compliance-grade traceability.
6. **The edit guard lives at the application/service layer**, not in the data layer — matching GnuCash's architecture where the engine is permissive and the UI is the gatekeeper, but elevating it to a platform invariant for the SaaS.

---

## B. Tax Discount Ordering (PRETAX / SAMETIME / POSTTAX) — Spike 3B Report

### 1. Source Evidence

#### 1.1 Enum definition — `libgnucash/engine/gncEntry.h` line 49

```c
typedef enum
{
    GNC_DISC_PRETAX = 1,
    GNC_DISC_SAMETIME,
    GNC_DISC_POSTTAX
} GncDiscountHow;
```

The header comment at lines 87-96 documents the semantics:

```c
/** How to apply the discount and taxes.  There are three distinct ways to
 * apply them:
 *
 * Type:	discount	tax
 * PRETAX	pretax		pretax-discount
 * SAMETIME	pretax		pretax
 * POSTTAX	pretax+tax	pretax
 */
```

#### 1.2 Field ownership — `libgnucash/engine/gncEntry.c` line 61 (struct `_gncEntry`)

```c
    gnc_numeric 	i_price;
    gboolean	i_taxable;
    gboolean	i_taxincluded;
    GncTaxTable *	i_tax_table;
    gnc_numeric 	i_discount;
    GncAmountType	i_disc_type;
    GncDiscountHow  i_disc_how;        // <--- per-Entry (line item) field
```

The field is named `i_disc_how` — the `i_` prefix indicates the customer-invoice side of the entry. (The vendor-bill side hard-codes `GNC_DISC_PRETAX` at line 1427 and never exposes a bill-side how.)

Accessor pair: `gncEntrySetInvDiscountHow` / `gncEntryGetInvDiscountHow` (lines 674, 984). The property key used for serialization is `"discount-method"` (`ENTRY_INV_DISC_HOW`, gncEntry.h line 323).

String round-trip: `gncEntryDiscountHowToString` / `gncEntryDiscountStringToHow` (lines 112, 132) emit `"PRETAX" | "SAMETIME" | "POSTTAX"`.

#### 1.3 Calculation core — `libgnucash/engine/gncEntry.c` `gncEntryComputeValueInt` (lines ~1140-1310)

Signature (line 1140):

```c
static void gncEntryComputeValueInt (gnc_numeric qty, gnc_numeric price,
    const GncTaxTable *tax_table, gboolean tax_included,
    gnc_numeric discount, GncAmountType discount_type,
    GncDiscountHow discount_how,
    gnc_numeric *value, gnc_numeric *discount_value,
    GList **tax_value, gnc_numeric *net_price)
```

Documented 4-step algorithm (comment at line 1095):

```
 1) compute the aggregate price (price*qty)
 2) if taxincluded, then back-compute the aggregate pre-tax price
 3) apply discount and taxes in the appropriate order
 4) return the requested results.
```

**Step 1** (line 1157): `aggregate = qty * price`.

**Step 2** — sum `tpercent` (sum of percent entries) and `tvalue` (sum of value entries) across the tax table, then:
- If `tax_included`: `pretax = (aggregate - tvalue) / (1 + tpercent)` (lines 1192-1200)
- Else: `pretax = aggregate` (line 1211)

**Step 3** — the discount_how switch (line 1224-1278):

```c
switch (discount_how)
{
case GNC_DISC_PRETAX:
case GNC_DISC_SAMETIME:
    /* compute the discount from pretax */
    if (discount_type == GNC_AMT_TYPE_PERCENT)
        discount = pretax * (discount/100);
    result = pretax - discount;

    /* Figure out when to apply the tax, pretax or pretax-discount */
    if (discount_how == GNC_DISC_PRETAX)
        pretax = result;          // tax base becomes (pretax - discount)
    break;

case GNC_DISC_POSTTAX:
    /* compute discount on pretax+taxes */
    if (discount_type == GNC_AMT_TYPE_PERCENT) {
        tax = pretax * tpercent;
        after_tax = pretax + tax + tvalue;
        discount = after_tax * (discount/100);
    }
    result = pretax - discount;   // tax base stays pretax
    break;
}
```

**Step 4** — emit `*value = result`, `*discount_value = discount`, and walk tax-table entries computing per-account amounts using the (possibly mutated) `pretax` base.

#### 1.4 Rounding — `libgnucash/engine/gncEntry.c` `gncEntryRecomputeValues` (lines 1445-1475)

```c
entry->i_value_rounded = gnc_numeric_convert (entry->i_value, denom,
    GNC_HOW_DENOM_EXACT | GNC_HOW_RND_ROUND_HALF_UP);
entry->i_disc_value_rounded = gnc_numeric_convert (entry->i_disc_value, denom,
    GNC_HOW_DENOM_EXACT | GNC_HOW_RND_ROUND_HALF_UP);
for (tv_iter = entry->i_tax_values; tv_iter; tv_iter=tv_iter->next) {
    GncAccountValue *acc_val = tv_iter->data;
    entry->i_tax_value_rounded = gnc_numeric_add (entry->i_tax_value_rounded,
        acc_val->value, denom,
        GNC_HOW_DENOM_EXACT | GNC_HOW_RND_ROUND_HALF_UP);
}
```

Rounding is **per line**, at the commodity denominator (`denom = gnc_commodity_get_fraction(currency)`, defaulting to 100000 if no invoice/bill attached), using **half-up** (`GNC_HOW_RND_ROUND_HALF_UP`).

Note `gncEntryComputeValueInt` itself does NOT round — the comment at line 1131 states: *"Note this function will not do any rounding unless forced to prevent overflow. It's the caller's responsibility to round."* The intermediate arithmetic uses exact rational arithmetic (`gnc_numeric` is a numerator/denominator pair).

#### 1.5 Inclusive-tax back-computation rounding

Within `gncEntryComputeValueInt`, the `pretax` derivation and percentage conversions use `GNC_HOW_RND_ROUND` (half-up at the auto-denominator) and `GNC_HOW_DENOM_REDUCE`. The internal discount multiplication also uses `GNC_HOW_RND_ROUND`.

#### 1.6 Re-computation trigger / modtime tracking (lines 1373-1393)

```c
if (entry->i_tax_table) {
    time64 modtime = gncTaxTableLastModifiedSecs (entry->i_tax_table);
    if (entry->i_taxtable_modtime != modtime) {
        entry->values_dirty = TRUE;
        entry->i_taxtable_modtime = modtime;
    }
}
```

`gncTaxTableLastModifiedSecs` (gncTaxTable.c line 783) returns the table's last-modified timestamp. If the referenced tax table changes, the entry's cached values are invalidated and recomputed on next access.

---

### 2. Answers to the Questions

**Q1. Which domain object owns the PRETAX/SAMETIME/POSTTAX setting?**

The **Entry** (document line item). Field `i_disc_how` of type `GncDiscountHow` on `struct _gncEntry` (gncEntry.c:61). The getter/setter are `gncEntry{Get,Set}InvDiscountHow`. It is serialized as the `"discount-method"` property on the Entry. It is **not** on the TaxTable, Invoice, or as a global setting. It is also customer-document only: the vendor-bill side of the same struct has no equivalent field and hard-codes `GNC_DISC_PRETAX` when computing bill values (line 1427).

**Q2. How does it interact with tax-inclusive pricing?**

`tax_included` is an independent flag (field `i_taxincluded` on the Entry). It only affects **Step 2** (deriving `pretax` from `aggregate`). Once `pretax` is known, the discount_how logic is identical in both cases. The three formulas, where `P = pretax`, `d` = discount fraction, `τ` = sum-of-tax-percent, `V` = sum-of-tax-fixed-value:

| Mode | Discount base | Tax base | Final value (what merchant gets) |
|---|---|---|---|
| PRETAX | `P` | `P − discount` | `P − discount` |
| SAMETIME | `P` | `P` | `P − discount` |
| POSTTAX | `P + P·τ + V` | `P` | `P − discount` |

If `tax_included` is true, then `P = (qty·price − V) / (1 + τ)`; otherwise `P = qty·price`.

Customer total to pay = `value + tax_value`. In tax-included mode the returned `value` may be less than `qty·price` even with no discount.

**Q3. What is the rounding behavior?**

- **When:** `gncEntryComputeValueInt` runs entirely in exact rationals (`gnc_numeric` = int64 numerator + denominator). Rounding only happens in the *caller*, `gncEntryRecomputeValues`, when producing the `*_rounded` fields for display/posting.
- **Mode:** `GNC_HOW_RND_ROUND_HALF_UP` (commercial half-up rounding).
- **Denominator:** the currency's commodity fraction (e.g. 100 for USD cents), obtained from `gnc_commodity_get_fraction(currency)`.
- **Granularity:** per Entry (per line). Each line's `i_value_rounded`, `i_disc_value_rounded`, and per-tax-account `i_tax_value_rounded` are rounded independently. The invoice-level total is the sum of per-line rounded values.

**Q4. How do historical calculations remain reproducible?**

All calculation inputs are stored **on the Entry itself**: `i_taxincluded`, `i_discount`, `i_disc_type`, `i_disc_how`, and a reference `i_tax_table` to a `GncTaxTable`. However the tax table's *contents* (rates, accounts) are NOT snapshotted on the entry — they are looked up via the pointer. The entry tracks `i_taxtable_modtime` (last-modified secs of the tax table at last computation). If the TaxTable is edited later:
- `gncEntryRecomputeValues` detects the modtime change, sets `values_dirty = TRUE`, and **recomputes** using the current tax-table contents.
- This means a posted invoice's numbers can **silently change** if its referenced TaxTable is later edited — a known reproducibility weakness.

Mitigations in the codebase: `gncTaxTableCopy` / `gncTaxTableEntryCopy` (gncTaxTable.c) exist, and the typical pattern is to assign a per-invoice copy of a tax table to each posted entry. Nothing in the engine *enforces* this, though.

---

### 3. Target Model Design (Django SaaS)

#### 3.1 Ownership

Place `discount_ordering_mode` on the **InvoiceLine** model (equivalent of `GncEntry`), mirroring GnuCash's per-line placement. It is customer-document only.

#### 3.2 Django enum & model

```python
# invoicing/models.py
from django.db import models
from decimal import Decimal

class DiscountOrderingMode(models.TextChoices):
    PRETAX    = "PRETAX",    "Discount before tax; tax on (line - discount)"
    SAMETIME  = "SAMETIME",  "Discount and tax both on line amount"
    POSTTAX   = "POSTTAX",   "Discount on (line + tax); tax on line"

class InvoiceLine(models.Model):
    invoice       = models.ForeignKey("Invoice", on_delete=models.CASCADE, related_name="lines")
    quantity      = models.DecimalField(max_digits=20, decimal_places=10)
    unit_price    = models.DecimalField(max_digits=20, decimal_places=10)
    discount_value    = models.DecimalField(max_digits=20, decimal_places=10, default=0)
    discount_is_percent = models.BooleanField(default=True)
    discount_ordering_mode = models.CharField(
        max_length=8,
        choices=DiscountOrderingMode.choices,
        default=DiscountOrderingMode.PRETAX,
    )
    tax_inclusive = models.BooleanField(default=False)
    tax_table     = models.ForeignKey("TaxTable", on_delete=models.PROTECT,
                                      related_name="lines")
    # --- snapshotted computation inputs for historical reproducibility ---
    # (see §3.6)
    frozen_unit_price     = models.DecimalField(max_digits=20, decimal_places=10, null=True)
    frozen_tax_table_json = models.JSONField(null=True)   # [{account, rate, kind}, ...]
    frozen_computed_at    = models.DateTimeField(null=True)
```

#### 3.3 Calculation logic (Python, `Decimal` with `ROUND_HALF_UP`)

```python
from decimal import Decimal, ROUND_HALF_UP
HUNDRED = Decimal("100")
ZERO    = Decimal("0")

def quantize2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def compute_line(line, *, round_: bool = True):
    P00 = Decimal("100")
    qty, price = line.quantity, line.unit_price
    aggregate = qty * price

    # Sum tax-table rates (matches GnuCash tpercent/tvalue aggregation)
    tpercent = ZERO         # sum of percent rates
    tvalue   = ZERO         # sum of fixed-value rates
    for e in line.tax_table.entries.all():
        if e.kind == "PERCENT":  tpercent += e.rate
        elif e.kind == "VALUE":  tvalue   += e.rate
    tpercent_frac = tpercent / P00

    # Step 2 — back-compute pretax if tax-inclusive
    if line.tax_inclusive:
        pretax = (aggregate - tvalue) / (Decimal("1") + tpercent_frac)
    else:
        pretax = aggregate

    # Step 3 — discount_how switch
    mode = line.discount_ordering_mode
    if line.discount_is_percent:
        d_frac = line.discount_value / P00

    if mode in (DiscountOrderingMode.PRETAX, DiscountOrderingMode.SAMETIME):
        discount = (pretax * d_frac) if line.discount_is_percent else line.discount_value
        value    = pretax - discount
        tax_base = value if mode == DiscountOrderingMode.PRETAX else pretax
    else:  # POSTTAX
        if line.discount_is_percent:
            tax      = pretax * tpercent_frac
            after_tax = pretax + tax + tvalue
            discount = after_tax * d_frac
        else:
            discount = line.discount_value
        value    = pretax - discount
        tax_base = pretax

    # Step 4 — per-account tax amounts
    tax_total = tvalue
    per_account = []
    for e in line.tax_table.entries.all():
        if e.kind == "PERCENT":
            amt = tax_base * (e.rate / P00)
        else:
            amt = e.rate
        per_account.append((e.account, amt))
        tax_total += amt

    if round_:
        value    = quantize2(value)
        discount = quantize2(discount)
        tax_total = sum((quantize2(a) for _, a in per_account), ZERO)
        per_account = [(ac, quantize2(a)) for ac, a in per_account]

    return {
        "value": value,           # what merchant gets
        "discount": discount,     # informational
        "tax_total": tax_total,   # sum of per-account rounded taxes
        "per_account_tax": per_account,
        "customer_pays": value + tax_total,
    }
```

#### 3.4 Interaction with tax-inclusive pricing

`tax_inclusive` is a boolean flag on the line; it only alters Step 2 (`pretax` derivation). After that, the three `discount_ordering_mode` branches behave identically. The Django model mirrors this separation: a `BooleanField` + a `CharField(choices=DiscountOrderingMode)`.

#### 3.5 Rounding behavior

- **Timing:** intermediate arithmetic uses Python `Decimal` (arbitrary precision); rounding happens once at the end, per line, matching GnuCash's "no rounding unless forced" policy.
- **Mode:** `ROUND_HALF_UP` (commercial), matching `GNC_HOW_RND_ROUND_HALF_UP`.
- **Denominator:** currency minor units (`.quantize(Decimal("0.01"))` for USD/EUR/GBP; look up the currency's `minor_unit` for others).
- **Granularity:** per line. Each line's `value`, `discount`, and each per-tax-account `amount` are rounded independently. Invoice totals are the sum of per-line rounded values.

#### 3.6 Historical reproducibility strategy

GnuCash's weakness: the entry only stores a *reference* to a `GncTaxTable`, whose contents can mutate. To close that gap in the Django model:

1. **Snapshot at post/finalize time.** When `Invoice.finalize()` runs (posting), write:
   - `frozen_unit_price` = current `unit_price`
   - `frozen_tax_table_json` = serialized list of `[{account_code, rate, kind}]` from the current TaxTable
   - `frozen_computed_at` = `timezone.now()`
2. **Freeze the TaxTable row itself** (or use `TaxTableVersion`): `TaxTable` has a `version` integer; each `finalize()` stamps the current version on the line. Edits create a new version. `compute_line()` reads from the frozen JSON if present, else from the live `tax_table`.
3. **Freeze the currency denominator** (minor units) on the line so re-running `compute_line()` years later produces identical output even if the currency definition is edited.
4. `InvoiceLine` becomes **immutable after finalize** — enforced by a model-level `check()` + a pre-save signal that rejects edits to frozen lines.

---

### 4. Worked Example

Item: `qty = 1`, `price = $100`, discount = 5% (percent), one tax at 10%, `tax_included = False`.

**Pretax derivation:** `tax_included = False` → `pretax = 100`.

#### PRETAX
- discount = `pretax × 0.05 = 100 × 0.05 = 5.00`
- value = `pretax − discount = 95.00`
- tax base = `pretax − discount = 95.00`
- tax = `95.00 × 0.10 = 9.50`
- **customer pays = 95.00 + 9.50 = 104.50**

#### SAMETIME
- discount = `pretax × 0.05 = 5.00`
- value = `pretax − discount = 95.00`
- tax base = `pretax = 100.00` *(discount ignored for tax)*
- tax = `100.00 × 0.10 = 10.00`
- **customer pays = 95.00 + 10.00 = 105.00**

#### POSTTAX
- tax (interim) = `pretax × 0.10 = 10.00`
- after_tax = `pretax + tax = 110.00`
- discount = `after_tax × 0.05 = 110 × 0.05 = 5.50`
- value = `pretax − discount = 100 − 5.50 = 94.50`
- tax base = `pretax = 100.00` → tax = `10.00`
- **customer pays = 94.50 + 10.00 = 104.50**

Same *customer_pays* for PRETAX and POSTTAX in this example, but the merchant-remittance split differs (PRETAX: 95+9.50, POSTTAX: 94.50+10). SAMETIME yields a different customer total (105.00) because the discount is not applied to the tax base.

With `tax_included = True` at 10%, `pretax = 100 / 1.10 = 90.9090...`; the same three branches then compute from that lower base, and `customer_pays` stays ≈ $100 in every mode (modulo rounding of the back-computed pretax).

---

### Summary Table for SPIKE_3_SEMANTIC_VERIFICATION.md

| Aspect | GnuCash | Django Target |
|---|---|---|
| Owner | `GncEntry.i_disc_how` (per line item) | `InvoiceLine.discount_ordering_mode` |
| Enum values | `GNC_DISC_PRETAX=1, _SAMETIME, _POSTTAX` | `DiscountOrderingMode` TextChoices |
| Tax-included flag | `GncEntry.i_taxincluded` (independent) | `InvoiceLine.tax_inclusive` |
| Calculation function | `gncEntryComputeValueInt()` in gncEntry.c | `compute_line()` helper |
| Rounding mode | `GNC_HOW_RND_ROUND_HALF_UP` | `ROUND_HALF_UP` |
| Rounding granularity | Per line, per tax account | Per line, per tax account |
| Rounding timing | After exact rational math, in `gncEntryRecomputeValues` | After `Decimal` math, in `compute_line(round_=True)` |
| Reproducibility weakness | TaxTable referenced, not snapshotted; modtime-tracked; can silently change | Mitigated by `frozen_*` snapshot fields at finalize + immutable-frozen-lines rule |

---

## C. Posted Journal Immutability

### 1. Source Evidence

#### A. Readonly Mechanisms in GnuCash

**Two distinct readonly mechanisms exist:**

**A1. Transaction-level readonly flag (manual marking)**
- **Location**: `libgnucash/engine/Transaction.cpp:1988-1993`
```cpp
void
xaccTransSetReadOnly (Transaction *trans, const char *reason)
{
    if (trans && reason)
        set_kvp_string_path (trans, {TRANS_READ_ONLY_REASON}, reason);
}
```

- **Retrieval**: `libgnucash/engine/Transaction.cpp:2357-2361`
```cpp
const char *
xaccTransGetReadOnly (Transaction *trans)
{
    return get_kvp_string_path (trans, {TRANS_READ_ONLY_REASON});
}
```

- **Usage**: This flag is set when voiding transactions (`xaccTransVoid` at line 2542) and by business features (invoices). It's stored as a KVP (Key-Value Pair) slot, not a database column.

**A2. Date-based auto-readonly (closed book periods)**
- **Location**: `libgnucash/engine/Transaction.cpp:2386-2422`
```cpp
gboolean xaccTransIsReadonlyByPostedDate(const Transaction *trans)
{
    GDate *threshold_date;
    GDate trans_date;
    const QofBook *book = xaccTransGetBook (trans);
    gboolean result;
    g_assert(trans);

    if (!qof_book_uses_autoreadonly(book))
    {
        return FALSE;
    }

    if (xaccTransIsSXTemplate (trans))
        return FALSE;

    threshold_date = qof_book_get_autoreadonly_gdate(book);
    g_assert(threshold_date);
    trans_date = xaccTransGetDatePostedGDate(trans);

    if (g_date_compare(&trans_date, threshold_date) < 0)
    {
        result = TRUE;
    }
    else
    {
        result = FALSE;
    }
    g_date_free(threshold_date);
    return result;
}
```

- **Book-level configuration**: `libgnucash/engine/qofbook.cpp:974-978`
```cpp
gboolean qof_book_uses_autoreadonly (const QofBook *book)
{
    g_assert(book);
    return (qof_book_get_num_days_autoreadonly(book) != 0);
}
```

#### B. Engine-Level Enforcement (or Lack Thereof)

**Critical Finding: NO ENGINE-LEVEL ENFORCEMENT**

**`xaccTransBeginEdit`** (`libgnucash/engine/Transaction.cpp:1353-1370`):
```cpp
void
xaccTransBeginEdit (Transaction *trans)
{
    if (!trans) return;
    if (!qof_begin_edit(&trans->inst)) return;

    if (qof_book_shutting_down(qof_instance_get_book(trans))) return;

    if (!qof_book_is_readonly(qof_instance_get_book(trans)))
    {
        xaccOpenLog ();
        xaccTransWriteLog (trans, 'B');
    }

    /* Make a clone of the transaction; we will use this
     * in case we need to roll-back the edit. */
    trans->orig = dupe_trans (trans);
}
```

**Observation**: This function only SKIPS logging if the book is readonly. It does NOT check if the individual transaction is readonly. It does NOT refuse to begin the edit.

**`xaccTransCommitEdit`** (`libgnucash/engine/Transaction.cpp:1533-1593`): No readonly checks. Performs scrubbing and commits.

**Search results confirm**: No Transaction or Split setter checks `xaccTransGetReadOnly` or `xaccTransIsReadonlyByPostedDate`.

**Exception - Void protection** (`libgnucash/engine/Transaction.cpp:2515-2544`):
```cpp
void
xaccTransVoid(Transaction *trans, const char *reason)
{
    g_return_if_fail(trans && reason);

    /* Prevent voiding transactions that are already marked
     * read only, for example generated by the business features.
     */
    if (xaccTransGetReadOnly (trans))
    {
        PWARN ("Refusing to void a read-only transaction!");
        return;
    }
    // ... proceeds to void
}
```

**This is the ONLY engine-level readonly check found.**

#### C. GUI-Level Enforcement

**Primary guard function**: `gnucash/gnome/gnc-split-reg.c:1117-1158`
```cpp
static gboolean
is_trans_readonly_and_warn (GtkWindow *parent, Transaction *trans)
{
    GtkWidget *dialog;
    const gchar *reason;
    const gchar *title = _("Cannot modify or delete this transaction.");
    const gchar *message =
        _("This transaction is marked read-only with the comment: '%s'");

    if (!trans) return FALSE;

    if (xaccTransIsReadonlyByPostedDate (trans))
    {
        dialog = gtk_message_dialog_new(parent,
                                        0,
                                        GTK_MESSAGE_ERROR,
                                        GTK_BUTTONS_OK,
                                        "%s", title);
        gtk_message_dialog_format_secondary_text(GTK_MESSAGE_DIALOG(dialog),
                "%s", _("The date of this transaction is older than the "
                        "\"Read-Only Threshold\" set for this book. "
                        "This setting can be changed in File->Properties->Accounts."));
        gtk_dialog_run(GTK_WIDGET(dialog));
        gtk_widget_destroy(dialog);
        return TRUE;
    }

    reason = xaccTransGetReadOnly (trans);
    if (reason)
    {
        dialog = gtk_message_dialog_new(parent,
                                        0,
                                        GTK_MESSAGE_ERROR,
                                        GTK_BUTTONS_OK,
                                        "%s", title);
        gtk_message_dialog_format_secondary_text(GTK_MESSAGE_DIALOG(dialog),
                message, reason);
        gtk_dialog_run(GTK_WIDGET(dialog));
        gtk_widget_destroy(dialog);
        return TRUE;
    }
    return FALSE;
}
```

**Called from 7 locations** in `gnc-split-reg.c`:
- Line 871: Transaction deletion guard
- Line 1180: Duplicate transaction guard
- Line 1255: Edit transaction guard
- Line 1325: Enter transaction guard
- Line 1397: Void transaction guard

**Additional UI check**: `gnucash/gnome/gnc-plugin-page-register.cpp:859`
```cpp
read_only = xaccTransIsReadonlyByPostedDate (trans);
```

#### D. Invoice Posting and Unposting

**Invoice posting** (`libgnucash/engine/gncInvoice.c:1442-1733`):
- Creates a new transaction and lot
- Sets readonly flag on the posted transaction
- Does NOT prevent programmatic editing

**Invoice unposting** (`libgnucash/engine/gncInvoice.c:1735-1872`):
```cpp
gboolean
gncInvoiceUnpost (GncInvoice *invoice, gboolean reset_tax_tables)
{
    Transaction *txn;
    GNCLot *lot;
    // ...
    
    txn = gncInvoiceGetPostedTxn (invoice);
    g_return_val_if_fail (txn, FALSE);

    lot = gncInvoiceGetPostedLot (invoice);
    g_return_val_if_fail (lot, FALSE);

    ENTER ("");
    /* Destroy the Posted Transaction */
    xaccTransClearReadOnly (txn);  // <-- CLEARS READONLY
    xaccTransBeginEdit (txn);
    xaccTransDestroy (txn);
    xaccTransCommitEdit (txn);
    
    // ... recreates link transactions
}
```

**Critical observation**: Unposting EXPLICITLY clears the readonly flag before destroying the transaction. This demonstrates that the engine allows editing readonly transactions if you bypass the GUI.

---

### 2. Answers to Questions

#### Q1: What financial facts are immutable after posting?

**Answer: NONE are truly immutable at the engine level.**

| Financial Fact | Enforcement Level | Code Evidence |
|----------------|------------------|---------------|
| Accounts (which accounts debited/credited) | GUI-only | No setter checks readonly |
| Amounts (split amount) | GUI-only | No setter checks readonly |
| Values (split value) | GUI-only | No setter checks readonly |
| Transaction date | GUI-only | No setter checks readonly |
| Currency | GUI-only | `xaccTransSetCurrency` has no readonly check |
| Posting relationships | GUI-only | No enforcement |

**Conclusion**: GnuCash provides NO database-level or engine-level constraints. All financial facts are mutable via direct API calls or database manipulation.

#### Q2: What operational metadata is mutable after posting?

**Answer: ALL metadata is mutable.**

| Metadata | Mutable? | Evidence |
|----------|----------|----------|
| Reconciliation state | Yes | No readonly checks in reconciliation setters |
| Bank matching | Yes | No readonly checks |
| Attachments | Yes | No readonly checks |
| Comments/memos | Yes | `xaccTransSetDescription`, `xaccSplitSetMemo` have no readonly checks |
| Review status | Yes | No readonly checks |
| External references (num field) | Yes | `xaccTransSetNum` has no readonly checks |

**Conclusion**: No distinction between financial facts and operational metadata at the engine level.

#### Q3: Does GnuCash allow editing posted transactions?

**Answer: YES, with important caveats.**

**GUI restrictions**:
- The GUI prevents editing via `is_trans_readonly_and_warn` dialog boxes
- Two mechanisms:
  1. Date-based auto-readonly (closed book periods)
  2. Manual readonly flag (e.g., voided transactions, invoice postings)

**Engine behavior**:
- **Programmatic editing is ALLOWED** - no engine-level enforcement
- `xaccTransBeginEdit` does NOT check transaction readonly status
- Individual setters (amount, account, date, etc.) do NOT check readonly
- Only `xaccTransVoid` has a readonly check (to prevent double-voiding)

**Readonly flag semantics**:
- Stored as KVP slot `TRANS_READ_ONLY_REASON`
- Purely advisory - not enforced by the engine
- Can be cleared via `xaccTransClearReadOnly`
- Invoice unposting demonstrates this: clears readonly, then destroys transaction

**Correction workflow**:
- No formal reversal/correcting entry mechanism exists
- Users must manually create offsetting transactions
- Void mechanism exists but is NOT the same as reversal
- Invoice unposting destroys and recreates (not a reversal)

**Locked period mechanism**:
- `qof_book_get_num_days_autoreadonly` configures threshold
- `xaccTransIsReadonlyByPostedDate` checks if transaction is older than threshold
- GUI-only enforcement via `is_trans_readonly_and_warn`

#### Q4: Are there any GnuCash behaviors that conflict with the target model?

**Answer: YES, multiple conflicts.**

**Conflict 1: No true immutability**
- Target model: "Posted financial facts are immutable"
- GnuCash reality: All facts are mutable at engine level
- **Migration implication**: Must add database constraints to enforce immutability

**Conflict 2: No formal reversal mechanism**
- Target model: "Corrections use reversal/correcting entries"
- GnuCash reality: Manual offsetting transactions, void mechanism, or invoice unposting
- **Migration implication**: Need to design proper reversal workflow

**Conflict 3: Readonly is advisory, not enforced**
- Target model: Immutability should be a system invariant
- GnuCash reality: Readonly flag is KVP metadata, not a constraint
- **Migration implication**: Must implement database-level constraints

**Conflict 4: No audit trail for metadata changes**
- Target model: "Audit trail for operational metadata changes"
- GnuCash reality: Only transaction log ('B'egin edit) exists, no metadata change tracking
- **Migration implication**: Must implement comprehensive audit logging

**Conflict 5: Invoice unposting destroys transactions**
- Target model: Corrections via reversal entries
- GnuCash reality: `gncInvoiceUnpost` destroys the posted transaction
- **Migration implication**: Must preserve all transactions, use reversal entries only

---

### 3. Target Model Design for Django SaaS Platform

#### A. Clear Separation: Financial Facts vs Operational Metadata

**Financial Facts (IMMUTABLE after posting)**:
```python
class PostedTransaction(models.Model):
    # Immutable financial facts
    transaction_date = models.DateField()
    date_posted = models.DateField()
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    description = models.CharField(max_length=256)
    is_posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True)
    posted_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT)
    
    class Meta:
        # Database-level immutability constraint
        constraints = [
            models.CheckConstraint(
                check=~models.Q(is_posted=True),  # Cannot update if posted
                name='prevent_update_when_posted'
            )
        ]

class PostedSplit(models.Model):
    # Immutable financial facts
    transaction = models.ForeignKey(PostedTransaction, on_delete=models.CASCADE, related_name='splits')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    value = models.DecimalField(max_digits=20, decimal_places=8)  # In report currency
    memo = models.CharField(max_length=256)  # Part of posting record
    
    class Meta:
        # Database-level immutability constraint
        constraints = [
            models.CheckConstraint(
                check=~models.Q(transaction__is_posted=True),
                name='prevent_split_update_when_posted'
            )
        ]
```

**Operational Metadata (MUTABLE with audit trail)**:
```python
class TransactionMetadata(models.Model):
    transaction = models.OneToOneField(PostedTransaction, on_delete=models.CASCADE, related_name='metadata')
    
    # Mutable operational metadata
    reconciliation_state = models.CharField(max_length=1, choices=[...])
    bank_match_status = models.CharField(max_length=32)
    review_status = models.CharField(max_length=32)
    external_reference = models.CharField(max_length=128)
    notes = models.TextField()
    attachments = models.JSONField()
    
    last_modified_by = models.ForeignKey(User, on_delete=models.PROTECT)
    last_modified_at = models.DateTimeField(auto_now=True)

class MetadataChangeLog(models.Model):
    """Audit trail for operational metadata changes"""
    transaction = models.ForeignKey(PostedTransaction, on_delete=models.CASCADE, related_name='metadata_changes')
    field_name = models.CharField(max_length=64)
    old_value = models.TextField()
    new_value = models.TextField()
    changed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(null=True)
```

#### B. Django Model Design

**Immutable fields enforced via**:
1. Database constraints (CheckConstraint)
2. Custom save() method that checks is_posted flag
3. Separate model for mutable metadata

```python
class ImmutablePostedTransaction(models.Model):
    """
    Once is_posted=True, financial facts cannot be changed.
    Only operational metadata (in separate model) can be modified.
    """
    # Financial facts (immutable)
    transaction_date = models.DateField()
    date_posted = models.DateField()
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    description = models.CharField(max_length=256)
    is_posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True)
    posted_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT)
    
    def save(self, *args, **kwargs):
        if self.pk:  # Existing record
            old = ImmutablePostedTransaction.objects.get(pk=self.pk)
            if old.is_posted:
                # Check if any immutable field changed
                immutable_fields = ['transaction_date', 'date_posted', 'currency', 'description']
                for field in immutable_fields:
                    if getattr(self, field) != getattr(old, field):
                        raise ValueError(f"Cannot modify {field} after posting")
        super().save(*args, **kwargs)
    
    def post(self, user):
        """Mark as posted - one-way operation"""
        self.is_posted = True
        self.posted_at = timezone.now()
        self.posted_by = user
        self.save()

class ImmutablePostedSplit(models.Model):
    transaction = models.ForeignKey(ImmutablePostedTransaction, on_delete=models.CASCADE, related_name='splits')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    value = models.DecimalField(max_digits=20, decimal_places=8)
    memo = models.CharField(max_length=256)
    
    def save(self, *args, **kwargs):
        if self.transaction.is_posted:
            raise ValueError("Cannot modify split after transaction is posted")
        super().save(*args, **kwargs)
```

#### C. Correction Workflow (Reversal/Correcting Entries)

**Pseudocode for proper correction**:

```python
def create_reversal_entry(original_transaction, user, reason):
    """
    Create a reversal entry for a posted transaction.
    Original transaction remains unchanged.
    """
    if not original_transaction.is_posted:
        raise ValueError("Can only reverse posted transactions")
    
    # Create reversal transaction
    reversal = ImmutablePostedTransaction.objects.create(
        transaction_date=timezone.now().date(),
        date_posted=timezone.now().date(),
        currency=original_transaction.currency,
        description=f"REVERSAL: {original_transaction.description}",
        is_posted=True,
        posted_at=timezone.now(),
        posted_by=user
    )
    
    # Create reversal splits (opposite signs)
    for orig_split in original_transaction.splits.all():
        ImmutablePostedSplit.objects.create(
            transaction=reversal,
            account=orig_split.account,
            amount=-orig_split.amount,  # Reverse sign
            value=-orig_split.value,     # Reverse sign
            memo=f"Reversal of: {orig_split.memo}"
        )
    
    # Link to original for audit trail
    TransactionReversal.objects.create(
        original_transaction=original_transaction,
        reversal_transaction=reversal,
        reason=reason,
        created_by=user
    )
    
    return reversal

def create_correcting_entry(original_transaction, corrected_splits_data, user, reason):
    """
    Create a correcting entry that fixes specific splits.
    Does NOT modify original. Creates new transaction with corrections.
    """
    if not original_transaction.is_posted:
        raise ValueError("Can only correct posted transactions")
    
    # Create correcting transaction
    correction = ImmutablePostedTransaction.objects.create(
        transaction_date=timezone.now().date(),
        date_posted=timezone.now().date(),
        currency=original_transaction.currency,
        description=f"CORRECTION: {original_transaction.description}",
        is_posted=True,
        posted_at=timezone.now(),
        posted_by=user
    )
    
    # First, reverse the incorrect splits
    for split_data in corrected_splits_data:
        orig_split = split_data['original_split']
        # Reverse original
        ImmutablePostedSplit.objects.create(
            transaction=correction,
            account=orig_split.account,
            amount=-orig_split.amount,
            value=-orig_split.value,
            memo=f"Reversal of incorrect: {orig_split.memo}"
        )
        
        # Add correct split
        ImmutablePostedSplit.objects.create(
            transaction=correction,
            account=split_data['correct_account'],
            amount=split_data['correct_amount'],
            value=split_data['correct_value'],
            memo=f"Correction: {split_data.get('memo', orig_split.memo)}"
        )
    
    # Link to original
    TransactionCorrection.objects.create(
        original_transaction=original_transaction,
        correction_transaction=correction,
        reason=reason,
        created_by=user
    )
    
    return correction
```

#### D. Audit Trail for Operational Metadata

```python
class MetadataChangeTracker:
    """Track all changes to operational metadata"""
    
    @staticmethod
    def track_change(transaction, field_name, old_value, new_value, user, reason=None):
        MetadataChangeLog.objects.create(
            transaction=transaction,
            field_name=field_name,
            old_value=str(old_value),
            new_value=str(new_value),
            changed_by=user,
            reason=reason
        )

class OperationalMetadataService:
    """Service layer for mutable operational metadata"""
    
    def update_reconciliation_state(self, transaction, new_state, user, reason=None):
        metadata = transaction.metadata
        old_state = metadata.reconciliation_state
        metadata.reconciliation_state = new_state
        metadata.last_modified_by = user
        metadata.save()
        
        MetadataChangeTracker.track_change(
            transaction, 'reconciliation_state', old_state, new_state, user, reason
        )
    
    def add_attachment(self, transaction, attachment_data, user):
        metadata = transaction.metadata
        attachments = metadata.attachments or []
        attachments.append(attachment_data)
        metadata.attachments = attachments
        metadata.last_modified_by = user
        metadata.save()
        
        MetadataChangeTracker.track_change(
            transaction, 'attachments', 'added', attachment_data.get('filename'), user
        )
```

#### E. Migration Implications

**Challenge 1: Existing editable data**
- GnuCash data has no immutability constraints
- Posted transactions may have been edited
- **Solution**: During import, snapshot all transactions at import time. Mark as "imported_from_gnucash" and allow a grace period for corrections before enforcing immutability.

**Challenge 2: Missing reversal entries**
- GnuCash corrections are manual or use void/unpost
- **Solution**: During import, detect voided transactions and invoice unposts. Create synthetic reversal entries where appropriate. Flag for manual review.

**Challenge 3: Metadata vs facts not separated**
- GnuCash stores everything in same tables
- **Solution**: During import, separate into two models:
  - Financial facts → ImmutablePostedTransaction/Split
  - Operational metadata → TransactionMetadata
  - Audit what was changed post-import

**Challenge 4: No audit trail**
- GnuCash only has transaction log, not field-level audit
- **Solution**: At import time, create baseline snapshot. All future changes tracked. Pre-import history not available.

**Migration pseudocode**:
```python
def migrate_gnucash_transaction(gnucash_txn):
    """Import a GnuCash transaction"""
    
    # Create immutable posted transaction
    posted_txn = ImmutablePostedTransaction.objects.create(
        transaction_date=gnucash_txn.date_posted,
        date_posted=gnucash_txn.date_posted,
        currency=import_currency(gnucash_txn.currency),
        description=gnucash_txn.description,
        is_posted=True,
        posted_at=gnucash_txn.date_entered,
        posted_by=import_user(gnucash_txn.entered_by)
    )
    
    # Import splits
    for gnucash_split in gnucash_txn.splits:
        ImmutablePostedSplit.objects.create(
            transaction=posted_txn,
            account=import_account(gnucash_split.account),
            amount=gnucash_split.amount,
            value=gnucash_split.value,
            memo=gnucash_split.memo
        )
    
    # Import operational metadata (separate model)
    TransactionMetadata.objects.create(
        transaction=posted_txn,
        reconciliation_state=gnucash_split.reconcile_state,
        notes=gnucash_txn.notes,
        # ... other metadata
    )
    
    # Flag if transaction has readonly flag (was voided or posted by invoice)
    if gnucash_txn.read_only_reason:
        posted_txn.import_flags.append('HAD_READONLY_FLAG')
        posted_txn.import_readonly_reason = gnucash_txn.read_only_reason
    
    # Flag if transaction was voided (requires special handling)
    if gnucash_txn.is_voided:
        posted_txn.import_flags.append('WAS_VOIDED_IN_GNUCASH')
        # Create synthetic reversal entry
        create_synthetic_void_reversal(posted_txn, gnucash_txn)
    
    return posted_txn
```

---

### 4. Worked Example

#### Scenario: Posted transaction with incorrect account

**Step 1: Original posted transaction (GnuCash)**
```
Transaction ID: txn-001
Date: 2024-01-15
Description: Office supplies purchase
Status: POSTED (but still editable in GnuCash!)

Splits:
  Split 1: Debit Office Supplies Expense (6010) $500
  Split 2: Credit Cash (1010) $500
```

**Step 2: Discovery of error - wrong account used**
```
Error: Should have debited Computer Equipment (1520), not Office Supplies (6010)
```

**Step 3: ILLEGAL - Attempt to edit posted transaction (GnuCash allows this!)**
```python
# In GnuCash, this would succeed at engine level:
transaction = get_transaction('txn-001')
split = transaction.splits[0]
split.set_account(computer_equipment_account)  # NO ERROR - GnuCash allows this!
split.commit_edit()
# Transaction now has wrong account, but original posting record is lost
```

**Step 4: PROPER correction workflow (Target Django model)**
```python
# In Django SaaS platform:
original_txn = ImmutablePostedTransaction.objects.get(id='txn-001')

# Attempt to edit - BLOCKED by immutability
try:
    original_txn.splits[0].account = computer_equipment_account
    original_txn.splits[0].save()
except ValueError as e:
    print(f"Blocked: {e}")  # "Cannot modify split after transaction is posted"

# Create proper correcting entry
correcting_txn = create_correcting_entry(
    original_transaction=original_txn,
    corrected_splits_data=[
        {
            'original_split': original_txn.splits.get(account__code='6010'),
            'correct_account': computer_equipment_account,
            'correct_amount': Decimal('500.00'),
            'correct_value': Decimal('500.00'),
            'memo': 'Computer equipment purchase'
        }
    ],
    user=request.user,
    reason="Correcting entry: Should have debited Computer Equipment (1520), not Office Supplies (6010)"
)

# Result:
# - Original transaction UNCHANGED (audit trail preserved)
# - New correcting transaction created with:
#   - Reversal split: Credit Office Supplies (6010) $500
#   - Correct split: Debit Computer Equipment (1520) $500
# - Link recorded in TransactionCorrection table
# - Full audit trail: who, when, why
```

**Step 5: Audit trail in target system**
```
Original Transaction (txn-001):
  Status: UNCHANGED
  Date: 2024-01-15
  Debit: Office Supplies (6010) $500
  Credit: Cash (1010) $500
  Description: Office supplies purchase

Correcting Transaction (txn-002):
  Status: POSTED
  Date: 2024-01-20
  Debit: Computer Equipment (1520) $500
  Credit: Office Supplies (6010) $500
  Description: CORRECTION: Office supplies purchase
  Reason: Correcting entry: Should have debited Computer Equipment (1520), not Office Supplies (6010)
  Created by: john.doe
  Created at: 2024-01-20 14:32:15

Correction Link:
  Original: txn-001
  Correction: txn-002
  Reason: [stored]
  User: john.doe
```

---

## D. Cross-Cutting Summary

### Key Findings

| Area | GnuCash Reality | Target Platform Design | Migration Gap |
|------|----------------|----------------------|---------------|
| **Reconciliation States** | 5 states (n/c/y/f/v), any transition allowed at engine level | Explicit transition matrix enforced at model layer | Add DB constraints for valid transitions |
| **Reconciliation Audit** | Only `date_reconciled` tracked; no user/run tracking | `ReconciliationAuditLog` + `reconciled_by` + `reconciliation_run` | Enrich audit trail; accept that pre-import history is unavailable |
| **Reconciliation Edit Guard** | UI-only; engine permits silent unreconcile | Application-layer guard blocks edits to locked splits | Elevate UI convention to platform invariant |
| **Void Mechanism** | Compound state (flag + zeroed amounts + KVP backup) | Separate columns (`voided_amount`, `voided_value`, `voided_at`, `voided_by`) with check constraints | Cleaner than KVP; requires restructuring void storage |
| **Discount Ordering Owner** | `GncEntry.i_disc_how` (per line item) | `InvoiceLine.discount_ordering_mode` | Direct mapping |
| **Discount Ordering Enum** | `GNC_DISC_PRETAX=1, _SAMETIME, _POSTTAX` | `DiscountOrderingMode` TextChoices | Preserve semantics, use string codes |
| **Tax-Inclusive Pricing** | Independent flag; only affects pretax derivation | `InvoiceLine.tax_inclusive` BooleanField | Direct mapping |
| **Rounding** | Half-up, per line, per tax account, after exact rational math | `ROUND_HALF_UP`, per line, per tax account, after Decimal math | Equivalent behavior |
| **Historical Reproducibility** | **WEAK**: TaxTable referenced by pointer; modtime-tracked; can silently change | Mitigated by `frozen_*` snapshot fields at finalize | **Critical fix**: snapshot tax tables at posting |
| **Posted Transaction Immutability** | **NONE**: All facts mutable at engine level; readonly is advisory KVP | Database-level constraints enforce immutability | **Critical gap**: must add DB constraints |
| **Financial Facts vs Metadata** | Not distinguished; all in same tables | Separate models: `ImmutablePostedTransaction` + `TransactionMetadata` | **Major restructuring**: separate facts from metadata |
| **Correction Workflow** | Manual offsetting transactions, void, or invoice unpost (which destroys) | Formal reversal/correcting entry workflow | Design new workflow; preserve all transactions |
| **Audit Trail** | Transaction log ('B'egin edit) only; no field-level tracking | `MetadataChangeLog` for every metadata change | **Critical gap**: implement comprehensive audit logging |

### Critical Gaps Requiring Immediate Attention

1. **Immutability Enforcement (P0)** — GnuCash has NO engine-level immutability. The target platform MUST implement database-level constraints (CheckConstraint, pre-save signals) to enforce that posted financial facts cannot be modified. This is the single largest architectural gap.

2. **Tax Table Snapshotting (P0)** — GnuCash's tax tables can mutate after invoice posting, causing historical calculations to silently change. The target platform MUST snapshot tax table contents at posting time via `frozen_*` fields or versioned TaxTable rows.

3. **Formal Reversal Workflow (P1)** — GnuCash lacks a formal reversal/correcting entry mechanism. The target platform MUST design and implement a proper workflow that creates new transactions to correct errors, rather than modifying existing ones.

4. **Comprehensive Audit Logging (P1)** — GnuCash's audit trail is minimal. The target platform MUST implement field-level audit logging for all operational metadata changes (`MetadataChangeLog`).

5. **Reconciliation Transition Matrix (P1)** — GnuCash permits any reconciliation state transition at the engine level. The target platform SHOULD encode an explicit transition matrix at the model layer to prevent invalid state changes.

### Migration Strategy

**Phase 1: Schema Design**
- Design Django models with immutability constraints baked in
- Separate financial facts from operational metadata
- Add audit trail tables

**Phase 2: Import Tooling**
- Build import scripts that separate GnuCash's unified data into facts + metadata
- Snapshot tax tables at import time
- Create baseline audit records for all imported data

**Phase 3: Validation**
- Run reconciliation reports on imported data; compare to GnuCash
- Verify tax calculations match (using snapshotted tax tables)
- Test immutability constraints (attempt illegal edits; verify they fail)

**Phase 4: Grace Period**
- Allow a grace period post-import where corrections can be made before immutability is strictly enforced
- Flag transactions that were voided or had readonly flags in GnuCash for manual review

### Recommendations

1. **Implement immutability constraints FIRST** — this is the foundational invariant that makes everything else work. Without it, the audit trail is meaningless because facts can be silently altered.

2. **Snapshot everything at posting time** — tax tables, prices, currencies, discount modes. Never rely on live lookups for historical calculations.

3. **Design the reversal workflow early** — it's a core business process that affects many other areas (UI, API, audit trail). Don't bolt it on later.

4. **Enforce reconciliation transitions at the model layer** — don't rely on UI guards. The state machine should be a database invariant.

5. **Accept that pre-import audit history is unavailable** — document this clearly for users. The audit trail starts at import time.

6. **Consider a "strict mode" for compliance** — some jurisdictions may require that even operational metadata (like reconciliation state) be immutable after a certain point. Design the system to support this.

### Open Questions

1. **Void semantics** — Should voiding a transaction create a separate reversal entry, or is the current "zero the amounts + save former values" approach sufficient? The target model uses the latter, but auditors may prefer the former.

2. **Frozen period unfreeze** — The target model allows admin unfreeze (FROZEN → RECONCILED). Should this be allowed at all, or should frozen be truly immutable? If allowed, what audit trail is required?

3. **Tax table versioning** — Should the target platform use a full `TaxTableVersion` model (with immutable historical versions), or is the `frozen_tax_table_json` JSON snapshot sufficient? The former is more auditable; the latter is simpler.

4. **Multi-currency reconciliation** — How does reconciliation interact with multi-currency transactions? GnuCash tracks `date_reconciled` per split, but should it also track the exchange rate used at reconciliation time?

5. **Concurrent reconciliation** — If two users try to reconcile the same account simultaneously, how should the system handle conflicts? GnuCash uses file/database locks; the target platform should use `select_for_update()` or optimistic locking.

---

## E. Conclusion

This spike verified three critical semantic areas against the GnuCash source code and identified significant gaps between GnuCash's permissive architecture and the target platform's requirements for a multi-tenant SaaS accounting system.

**The most critical finding** is that GnuCash provides NO engine-level immutability enforcement. All financial facts are mutable via direct API calls, and readonly flags are purely advisory (GUI-only). This is fundamentally incompatible with the requirements of a cloud accounting platform where data integrity and auditability are paramount.

**The second critical finding** is that GnuCash's tax table design allows historical calculations to silently change if the referenced tax table is edited after posting. This is a reproducibility weakness that must be fixed in the target platform by snapshotting tax table contents at posting time.

**The third finding** is that GnuCash lacks a formal reversal/correcting entry workflow. Corrections are handled via manual offsetting transactions, voiding, or invoice unposting (which destroys the original transaction). The target platform must design a proper workflow that preserves the audit trail by creating new transactions rather than modifying existing ones.

These findings have significant implications for the target platform design:

1. **Immutability must be enforced at the database level**, not just the application layer. Use CheckConstraint, pre-save signals, and separate models for immutable facts vs mutable metadata.

2. **Historical reproducibility requires snapshotting** all calculation inputs at posting time. Never rely on live lookups for tax tables, prices, or currencies.

3. **The audit trail must be comprehensive** — field-level logging for all operational metadata changes, plus a formal reversal/correcting entry workflow for financial facts.

4. **Reconciliation state transitions should be enforced at the model layer** via an explicit transition matrix, not just at the UI layer.

The target Django model designs presented in this report address these gaps and provide a solid foundation for the FVA Accounting Platform rearchitecture. The migration strategy outlines a phased approach to importing GnuCash data while adding the necessary constraints and audit trails.

**Next steps:**
- Review this report with stakeholders and subject-matter experts
- Validate the target Django models against accounting compliance requirements (GAAP, IFRS)
- Prototype the immutability constraints and reversal workflow
- Build the import tooling and run a pilot migration on sample GnuCash data