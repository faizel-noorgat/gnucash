# Data Objects — GnuCash

**Extracted:** 58 data transfer objects / entities
**System:** gnucash

---

## Data Object Catalog

### 1. Transaction

**Type:** Unknown  
**Source:** `libgnucash/engine/TransactionP.hpp:74-119`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| id | const char* |  |
| description | const char* |  |
| num | const char* |  |
| date_entered | time64 |  |
| date_posted | time64 |  |
| common_currency | gnc_commodity* |  |
| splits | GList* |  |
| marker | unsigned char |  |
| orig | Transaction* |  |
| txn_type | char |  |

---

### 2. Split

**Type:** Unknown  
**Source:** `libgnucash/engine/SplitP.hpp:71-134`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| acc | Account* |  |
| orig_acc | Account* |  |
| lot | GNCLot* |  |
| parent | Transaction* |  |
| orig_parent | Transaction* |  |
| memo | const char* |  |
| action | const char* |  |
| date_reconciled | time64 |  |
| reconciled | char |  |
| gains | unsigned char |  |
| gains_split | Split* |  |
| value | gnc_numeric |  |
| amount | gnc_numeric |  |
| split_type | const char* |  |
| balance | gnc_numeric |  |
| noclosing_balance | gnc_numeric |  |
| cleared_balance | gnc_numeric |  |
| reconciled_balance | gnc_numeric |  |
| adjusted_amount | gnc_numeric |  |

---

### 3. Account

**Type:** Unknown  
**Source:** `libgnucash/engine/AccountP.hpp:58-139 (AccountPrivate)`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| accountName | const char* |  |
| accountCode | const char* |  |
| description | const char* |  |
| type | GNCAccountType |  |
| commodity | gnc_commodity* |  |
| commodity_scu | int |  |
| non_standard_scu | gboolean |  |
| parent | Account* |  |
| children | std::vector<Account*> |  |
| starting_balance | gnc_numeric |  |
| starting_noclosing_balance | gnc_numeric |  |
| starting_cleared_balance | gnc_numeric |  |
| starting_reconciled_balance | gnc_numeric |  |
| balance | gnc_numeric |  |
| noclosing_balance | gnc_numeric |  |
| cleared_balance | gnc_numeric |  |
| reconciled_balance | gnc_numeric |  |
| balanceDirty | gboolean |  |
| has_stock_split | gboolean |  |
| splits | std::vector<Split*> |  |
| splits_hash | GHashTable* |  |
| sort_dirty | gboolean |  |
| lots | LotList* |  |
| policy | GNCPolicy* |  |
| notes | char* |  |
| color | char* |  |
| tax_us_code | char* |  |
| tax_us_pns | char* |  |
| last_num | char* |  |
| sort_order | char* |  |
| filter | char* |  |
| mark | short |  |
| defer_bal_computation | gboolean |  |

---

### 4. GncInvoice

**Type:** Unknown  
**Source:** `libgnucash/engine/gncInvoice.c:49-75`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| id | const char* |  |
| notes | const char* |  |
| active | gboolean |  |
| billing_id | const char* |  |
| printname | char* |  |
| terms | GncBillTerm* |  |
| entries | GList* |  |
| prices | GList* |  |
| owner | GncOwner |  |
| billto | GncOwner |  |
| job | GncJob* |  |
| date_opened | time64 |  |
| date_posted | time64 |  |
| to_charge_amount | gnc_numeric |  |
| currency | gnc_commodity* |  |
| posted_acc | Account* |  |
| posted_txn | Transaction* |  |
| posted_lot | GNCLot* |  |

---

### 5. GncEntry

**Type:** Unknown  
**Source:** `libgnucash/engine/gncEntry.c:42-100`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| date | time64 |  |
| date_entered | time64 |  |
| desc | const char* |  |
| action | const char* |  |
| notes | const char* |  |
| quantity | gnc_numeric |  |
| i_account | Account* |  |
| i_price | gnc_numeric |  |
| i_taxable | gboolean |  |
| i_taxincluded | gboolean |  |
| i_tax_table | GncTaxTable* |  |
| i_discount | gnc_numeric |  |
| i_disc_type | GncAmountType |  |
| i_disc_how | GncDiscountHow |  |
| b_account | Account* |  |
| b_price | gnc_numeric |  |
| b_taxable | gboolean |  |
| b_taxincluded | gboolean |  |
| b_tax_table | GncTaxTable* |  |
| billable | gboolean |  |
| billto | GncOwner |  |
| b_payment | GncEntryPaymentType |  |
| order | GncOrder* |  |
| invoice | GncInvoice* |  |
| bill | GncInvoice* |  |
| values_dirty | gboolean |  |
| i_value | gnc_numeric |  |
| i_value_rounded | gnc_numeric |  |
| i_tax_values | GList* |  |
| i_tax_value | gnc_numeric |  |
| i_tax_value_rounded | gnc_numeric |  |
| i_disc_value | gnc_numeric |  |
| i_disc_value_rounded | gnc_numeric |  |
| i_taxtable_modtime | time64 |  |
| b_value | gnc_numeric |  |
| b_value_rounded | gnc_numeric |  |
| b_tax_values | GList* |  |
| b_tax_value | gnc_numeric |  |
| b_tax_value_rounded | gnc_numeric |  |
| b_taxtable_modtime | time64 |  |

---

### 6. GncCustomer

**Type:** Unknown  
**Source:** `libgnucash/engine/gncCustomer.c:51-73`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| id | const char* |  |
| name | const char* |  |
| notes | const char* |  |
| terms | GncBillTerm* |  |
| addr | GncAddress* |  |
| currency | gnc_commodity* |  |
| taxtable | GncTaxTable* |  |
| taxtable_override | gboolean |  |
| taxincluded | GncTaxIncluded |  |
| active | gboolean |  |
| jobs | GList* |  |
| balance | gnc_numeric* |  |
| credit | gnc_numeric |  |
| discount | gnc_numeric |  |
| shipaddr | GncAddress* |  |

---

### 7. GncVendor

**Type:** Unknown  
**Source:** `libgnucash/engine/gncVendor.c:51-67`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| id | const char* |  |
| name | const char* |  |
| notes | const char* |  |
| terms | GncBillTerm* |  |
| addr | GncAddress* |  |
| currency | gnc_commodity* |  |
| taxtable | GncTaxTable* |  |
| taxtable_override | gboolean |  |
| taxincluded | GncTaxIncluded |  |
| active | gboolean |  |
| jobs | GList* |  |
| balance | gnc_numeric* |  |

---

### 8. GncEmployee

**Type:** Unknown  
**Source:** `libgnucash/engine/gncEmployee.c:47-63`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| id | const char* |  |
| username | const char* |  |
| addr | GncAddress* |  |
| currency | gnc_commodity* |  |
| active | gboolean |  |
| balance | gnc_numeric* |  |
| language | const char* |  |
| acl | const char* |  |
| workday | gnc_numeric |  |
| rate | gnc_numeric |  |
| ccard_acc | Account* |  |

---

### 9. GncJob

**Type:** Unknown  
**Source:** `libgnucash/engine/gncJob.c:41-49`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| id | const char* |  |
| name | const char* |  |
| desc | const char* |  |
| owner | GncOwner |  |
| active | gboolean |  |

---

### 10. GncOwner

**Type:** Unknown  
**Source:** `libgnucash/engine/gncOwner.h:96-108`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| type | GncOwnerType |  |
| owner.undefined | gpointer |  |
| owner.customer | GncCustomer* |  |
| owner.job | GncJob* |  |
| owner.vendor | GncVendor* |  |
| owner.employee | GncEmployee* |  |
| qof_temp | gpointer |  |

---

### 11. GncOrder

**Type:** Unknown  
**Source:** `libgnucash/engine/gncOrder.c:42-56`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| id | const char* |  |
| notes | const char* |  |
| active | gboolean |  |
| reference | const char* |  |
| printname | char* |  |
| owner | GncOwner |  |
| entries | GList* |  |
| opened | time64 |  |
| closed | time64 |  |

---

### 12. GncTaxTable

**Type:** Unknown  
**Source:** `libgnucash/engine/gncTaxTable.c:37-51`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| name | const char* |  |
| entries | GncTaxTableEntryList* |  |
| modtime | time64 |  |
| refcount | gint64 |  |
| parent | GncTaxTable* |  |
| child | GncTaxTable* |  |
| invisible | gboolean |  |
| children | GList* |  |

---

### 13. GncTaxTableEntry

**Type:** Unknown  
**Source:** `libgnucash/engine/gncTaxTable.c:58-64`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| table | GncTaxTable* |  |
| account | Account* |  |
| type | GncAmountType |  |
| amount | gnc_numeric |  |

---

### 14. GncBillTerm

**Type:** Unknown  
**Source:** `libgnucash/engine/gncBillTerm.c:37-58`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| name | const char* |  |
| desc | const char* |  |
| type | GncBillTermType |  |
| due_days | gint |  |
| disc_days | gint |  |
| discount | gnc_numeric |  |
| cutoff | gint |  |
| refcount | gint64 |  |
| parent | GncBillTerm* |  |
| child | GncBillTerm* |  |
| invisible | gboolean |  |
| children | GList* |  |

---

### 15. GncAddress

**Type:** Unknown  
**Source:** `libgnucash/engine/gncAddress.c:38-53`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| book | QofBook* |  |
| parent | QofInstance* |  |
| dirty | gboolean |  |
| name | const char* |  |
| addr1 | const char* |  |
| addr2 | const char* |  |
| addr3 | const char* |  |
| addr4 | const char* |  |
| phone | const char* |  |
| fax | const char* |  |
| email | const char* |  |

---

### 16. GNCLot

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-lot.cpp:60-100`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| account | Account* |  |
| splits | SplitList* |  |
| title | char* |  |
| notes | char* |  |
| cached_invoice | GncInvoice* |  |
| is_closed | signed char |  |
| marker | unsigned char |  |

---

### 17. Recurrence

**Type:** Unknown  
**Source:** `libgnucash/engine/Recurrence.h:76-82`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| start | GDate |  |
| ptype | PeriodType |  |
| mult | guint16 |  |
| wadj | WeekendAdjust |  |

---

### 18. SchedXaction

**Type:** Unknown  
**Source:** `libgnucash/engine/SchedXaction.h:91-123`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| name | gchar* |  |
| schedule | GList* |  |
| last_date | GDate |  |
| start_date | GDate |  |
| end_date | GDate |  |
| num_occurances_total | gint |  |
| num_occurances_remain | gint |  |
| instance_num | gint |  |
| enabled | gboolean |  |
| autoCreateOption | gboolean |  |
| autoCreateNotify | gboolean |  |
| advanceCreateDays | gint |  |
| advanceRemindDays | gint |  |
| template_acct | Account* |  |
| deferredList | GList* |  |

---

### 19. SXTmpStateData

**Type:** Unknown  
**Source:** `libgnucash/engine/SchedXaction.h:131-136`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| last_date | GDate |  |
| num_occur_rem | gint |  |
| num_inst | gint |  |

---

### 20. SchedXactions

**Type:** Unknown  
**Source:** `libgnucash/engine/SX-book.h:54-59`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| sx_list | GList* |  |
| sx_notsaved | gboolean |  |

---

### 21. GncBudget

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-budget.cpp:75-90`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| name | const gchar* |  |
| description | const gchar* |  |
| recurrence | Recurrence |  |
| acct_map | AcctMap |  |
| num_periods | guint |  |

---

### 22. gnc_commodity

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-commodity.cpp:70-97`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| name_space | gnc_commodity_namespace* |  |
| fullname | const char* |  |
| mnemonic | const char* |  |
| printname | char* |  |
| cusip | const char* |  |
| fraction | int |  |
| unique_name | char* |  |
| user_symbol | char* |  |
| quote_flag | gboolean |  |
| quote_source | gnc_quote_source* |  |
| quote_tz | const char* |  |
| usage_count | int |  |
| default_symbol | const char* |  |

---

### 23. GNCPrice

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-pricedb-p.h:37-52`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| db | GNCPriceDB* |  |
| commodity | gnc_commodity* |  |
| currency | gnc_commodity* |  |
| tmspec | time64 |  |
| source | PriceSource |  |
| type | const char* |  |
| value | gnc_numeric |  |
| refcount | guint32 |  |

---

### 24. GNCPriceDB

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-pricedb-p.h:59-65`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| commodity_hash | GHashTable* |  |
| bulk_update | gboolean |  |
| reset_nth_price_cache | gboolean |  |

---

### 25. QofBook

**Type:** Unknown  
**Source:** `libgnucash/engine/qofbook-p.hpp:46-128`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| inst | QofInstance |  |
| session_dirty | gboolean |  |
| dirty_time | time64 |  |
| dirty_cb | QofBookDirtyCB |  |
| dirty_data | gpointer |  |
| hash_of_collections | GHashTable* |  |
| data_tables | GHashTable* |  |
| data_table_finalizers | GHashTable* |  |
| read_only | gboolean |  |
| book_open | char |  |
| shutting_down | gboolean |  |
| version | gint32 |  |
| backend | QofBackend* |  |
| cached_num_field_source | gboolean |  |
| cached_num_field_source_isvalid | gboolean |  |
| cached_num_days_autoreadonly | gint |  |
| cached_num_days_autoreadonly_isvalid | gboolean |  |

---

### 26. QofInstance

**Type:** Unknown  
**Source:** `libgnucash/engine/qofinstance.h:72-77`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| object | GObject |  |
| e_type | QofIdType |  |
| kvp_data | KvpFrame* |  |

---

### 27. gnc_numeric

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-numeric.h:58-62`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| num | gint64 |  |
| denom | gint64 |  |

---

### 28. gnc_commodity_namespace

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-commodity.cpp:110-118`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| name | const gchar* |  |
| iso4217 | gboolean |  |
| cm_table | GHashTable* |  |
| cm_list | GList* |  |

---

### 29. gnc_commodity_table

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-commodity.cpp:125-129`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| ns_table | GHashTable* |  |
| ns_list | GList* |  |

---

### 30. GNCPriceLookupHelper

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-pricedb-p.h:86-91`

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| return_list | GList** |  |
| key | gnc_commodity* |  |
| time | time64 |  |

---

### 31. gnc_numeric (cross-cutting value type)

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-numeric.h:58-62`

---

### 32. GncOwner (cross-cutting discriminator)

**Type:** Unknown  
**Source:** `libgnucash/engine/gncOwner.h:96-108`

---

### 33. Split.reconciled (state flag)

**Type:** Unknown  
**Source:** `libgnucash/engine/SplitP.hpp:97`

---

### 34. Transaction.txn_type

**Type:** Unknown  
**Source:** `libgnucash/engine/TransactionP.hpp:117`

---

### 35. GncDiscountHow (enum)

**Type:** Unknown  
**Source:** `libgnucash/engine/gncEntry.h:49-54`

---

### 36. GncAmountType (enum)

**Type:** Unknown  
**Source:** `libgnucash/engine/gncTaxTable.h:78-82`

---

### 37. GncBillTermType (enum)

**Type:** Unknown  
**Source:** `libgnucash/engine/gncBillTerm.h:122-127`

---

### 38. GncOwnerType (enum)

**Type:** Unknown  
**Source:** `libgnucash/engine/gncOwner.h:45-53`

---

### 39. GncInvoiceType (enum)

**Type:** Unknown  
**Source:** `libgnucash/engine/gncInvoice.h:59-72`

---

### 40. GNCAccountType (enum)

**Type:** Unknown  
**Source:** `libgnucash/engine/Account.h:99-178`

---

### 41. GNCPolicy (interface)

**Type:** Unknown  
**Source:** `libgnucash/engine/policy.cpp (AccountPrivate.policy field)`

---

### 42. PeriodType (enum)

**Type:** Unknown  
**Source:** `libgnucash/engine/Recurrence.h:51-63`

---

### 43. WeekendAdjust (enum)

**Type:** Unknown  
**Source:** `libgnucash/engine/Recurrence.h:65-72`

---

### 44. SchedXaction

**Type:** Unknown  
**Source:** `libgnucash/engine/SchedXaction.h:91-123`

---

### 45. time64 (POSIX timestamp)

**Type:** Unknown  
**Source:** `glib <glib.h> (64-bit time_t)`

---

### 46. GNCLot

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-lot.cpp:60-100`

---

### 47. GncTaxTable

**Type:** Unknown  
**Source:** `libgnucash/engine/gncTaxTable.c:37-51`

---

### 48. GncBillTerm

**Type:** Unknown  
**Source:** `libgnucash/engine/gncBillTerm.c:37-58`

---

### 49. GncCustomer/GncVendor/GncEmployee (business entities)

**Type:** Unknown  
**Source:** `libgnucash/engine/gncCustomer.c:51-73, gncVendor.c:51-67, gncEmployee.c:47-63`

---

### 50. GncOrder

**Type:** Unknown  
**Source:** `libgnucash/engine/gncOrder.c:42-56`

---

### 51. GncEntry

**Type:** Unknown  
**Source:** `libgnucash/engine/gncEntry.c:42-100`

---

### 52. gnc_commodity

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-commodity.cpp:70-97`

---

### 53. GNCPrice

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-pricedb-p.h:37-52`

---

### 54. QofBook

**Type:** Unknown  
**Source:** `libgnucash/engine/qofbook-p.hpp:46-128`

---

### 55. gnc_numeric error encoding

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-numeric.h:221-233`

---

### 56. GNCNumericErrorCode / rounding 'how' flags

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-numeric.h:91-233`

---

### 57. GncBudget

**Type:** Unknown  
**Source:** `libgnucash/engine/gnc-budget.cpp:75-90`

---

### 58. QofSession (session/book wrapper)

**Type:** Unknown  
**Source:** `libgnucash/engine/qofsession.h`

---

---

**Full data:** Workflow output at `/tmp/claude-1000/-projects-gnucash/4167734d-62b3-4401-8a66-a376364623af/tasks/w0yisof7f.output`
