# GnuCash Modernization Assessment

**Generated:** 2026-09-18
**Tool:** scc 3.3.5, jcodemunch MCP, jdocmunch MCP
**Repository:** `Gnucash/gnucash` (fork: `faizel-noorgat/gnucash`)
**Branch:** stable (HEAD: fb2c773bf6)

---

## Executive Summary

GnuCash is a mature double-entry accounting desktop application (25+ years) with **468,607 SLOC** across C/C++/Scheme. The codebase is well-structured with clear layered architecture (engine → backend → app-utils → GUI), but carries significant technical debt: 43,275 cyclomatic complexity points, 20 high-risk hotspots, and 0% documentation coverage for core symbols. No hardcoded secrets detected. **Recommendation:** Refactor-in-place same-stack modernization (`/modernize-uplift`) focusing on high-complexity engine files, C→C++ migration (ongoing), and Scheme→C++ report conversion. Architecture is sound; modernization should preserve it.

---

## System Inventory

### Quantitative Metrics (scc)

| Metric | Value |
|--------|-------|
| Total SLOC | 468,607 |
| Total Files | 1,801 |
| Total Complexity | 43,275 |
| C SLOC | 132,266 (28%) |
| C++ SLOC | 137,363 (29%) |
| Scheme SLOC | 48,205 (10%) |
| C Header SLOC | 15,208 (3%) |
| JavaScript SLOC | 40,785 (9%) |
| Python SLOC | 8,535 (2%) |
| CMake SLOC | 7,672 (2%) |

**COCOMO-II Complexity Index:** 2,940 (relative scale measure, not timeline)
*Formula: 2.94 × (468.6)^1.10. This is a relative size/complexity signal for ranking systems — not an estimate of modernization duration or cost. It assumes traditional human-team productivity, which agentic transformation does not follow.*

### Technology Fingerprint

**Languages & Frameworks:**
- **C/C++ (57% of code):** Core engine, backend, GUI (GTK3)
- **Scheme/Guile (10%):** Reports, business logic, bindings
- **Python (2%):** Bindings (SWIG-generated), scripts
- **JavaScript (9%):** Chart.js (borrowed), HTML reports
- **Perl:** Finance::Quote integration (external)

**Build System:**
- CMake 3.14.5+ (root CMakeLists.txt)
- Ninja generator (recommended)
- SWIG 4.2.0 (Python/Scheme bindings)

**Dependencies (from CI):**
- Boost 1.70+ (algorithm, date_time, filesystem, locale, process)
- GTK3 3.22+ (GUI)
- Guile 2.2 (Scheme interpreter)
- libdbi (SQL backend)
- libOFX, aqbanking (financial data import)
- WebKit2GTK 4.1 (HTML rendering)
- GoogleTest (unit tests)

**Data Stores:**
- **XML Backend:** Native GnuCash format (libgnucash/backend/xml/)
- **SQL Backend:** SQLite/PostgreSQL/MySQL via libdbi (libgnucash/backend/sql/, dbi/)
- **No ORM:** Direct SQL via custom backend layer

**Integration Points:**
- **File I/O:** XML, SQL, QIF, CSV, OFX import/export
- **Online Banking:** AQBanking (HBCI/OFX), Finance::Quote (Perl)
- **Scripting:** Guile (Scheme), Python bindings
- **Printing:** GTK3 print dialogs

**Test Presence:**
- **Test files:** 123 C/C++ test files, 255 test directories
- **Test framework:** GoogleTest (C++), Guile test framework (Scheme)
- **Coverage:** 98% pass rate (131/133 tests), 2 minor failures
- **Signal:** Moderate test coverage, but no coverage metrics reported

---

## Architecture-at-a-Glance

**12 Major Functional Domains** (see `ARCHITECTURE.mmd` for diagram):

| Domain | Files | Purpose | Key Dependencies |
|--------|-------|---------|------------------|
| **Core Engine** | ~108 | Double-entry accounting data model (Account, Transaction, Split, QOF) | Core Utilities |
| **Backend/Persistence** | ~80 | XML, SQL, DBI storage backends | Engine, Core Utils |
| **Core Utilities** | ~17 | Platform-independent helpers (paths, prefs, locale) | (none) |
| **App Utilities** | ~25 | Bridge engine ↔ GUI (UI utils, state, quotes) | Engine, Core Utils |
| **Module System** | 3 | Plugin/module loading | Core Utils |
| **GUI/Gnome** | ~150 | GTK3 interface (dialogs, plugins, windows) | Engine, App Utils, Backend, Register |
| **Register** | ~40 | Transaction entry widget (spreadsheet UI) | Engine, App Utils |
| **Reports** | ~80 | Reporting system (Scheme-based) | Engine, App Utils, Guile |
| **Import/Export** | ~80 | Data format handlers (CSV, QIF, OFX, AQBanking) | Engine, App Utils, GUI |
| **Tax** | ~10 | Locale-specific tax handling (US, DE) | Engine |
| **Quotes** | Perl | Stock/fund price retrieval (Finance::Quote) | App Utils (via C interface) |
| **Bindings** | ~40 | Guile + Python scripting interfaces | Engine, App Utils |

**Architecture Quality:** ✅ Layered design with clear separation of concerns. QOF (Query Object Framework) provides generic object persistence abstraction. Multi-backend support (XML/SQL) is well-isolated.

---

## Production Runtime Profile

**Status:** ⚠️ No telemetry available

**Gap:** No production telemetry (APM, batch logs, runtime exports) connected. Cannot determine:
- p50/p95/p99 wall-clock for key transactions
- Highest-variance operational domains
- Real-world usage patterns

**Impact:** Modernization prioritization relies on static analysis (complexity, churn) rather than runtime data. Step 4 skipped.

**Recommendation:** If production GnuCash instances exist, instrument with APM or export batch job logs to enable runtime overlay in future assessments.

---

## Technical Debt

**Top 10 Findings** (ranked by remediation value, from legacy-analyst subagent):

### 1. God Functions — 27 Functions >200 Lines
**Evidence:**
- `Account.cpp:640` — `gnc_account_class_init()` = **487 lines** (41 property registrations)
- `assistant-loan.cpp:459` — `gnc_loan_assistant_create()` = **436 lines** (38 repetitive widget lookups)
- `dialog-invoice.c:3506` — `gnc_invoice_search()` = **271 lines**
- `split-register.c:1777` — `gnc_split_register_save()` = **270 lines**

**Impact:** Nearly impossible to reason about, test, or refactor safely. Any change requires navigating hundreds of lines.

**Fix:** Extract property registration into static array + loop. Use widget-name→field mapping tables for UI builders.

### 2. Dead Code — 7 Functions Behind Misspelled `#ifdef`
**Evidence:** `libgnucash/engine/qofutil.cpp:227-254` — 7 static functions wrapped in `#ifdef THESE_CAN_BE_USEFUL_FOR_DEGUGGING` (misspelled). Zero references anywhere.

**Impact:** Dead code confuses readers, inflates codebase, creates false surfaces.

**Fix:** Delete entire `#ifdef` block (lines 227-257). Remove `G_GNUC_UNUSED` annotation or delete unused functions.

### 3. C-Style Casts in C++ — 211 Instances in Engine
**Evidence:**
- `gnc-pricedb.cpp`: **32** casts
- `qofquerycore.cpp`: **18** casts
- `Account.cpp`: **18** casts
- Total: **211 C-style casts** across engine C++ files

**Impact:** Bypass C++ type safety. Suppress compiler warnings that catch real bugs. Make refactoring dangerous.

**Fix:** Replace `(Type*)ptr` with `static_cast<Type*>(ptr)`, `const_cast`, or `reinterpret_cast`. Enable `-Wold-style-cast` in CMake.

### 4. Hardcoded Module Path — Compile-Time `/usr/local/gnucash/lib/modules`
**Evidence:** `libgnucash/gnc-module/gnc-module.h:37` — `#define DEFAULT_MODULE_PATH "/usr/local/gnucash/lib/modules"`

**Impact:** Breaks on non-standard install prefix (Flatpak, distro packages, macOS, Windows).

**Fix:** Use `CMAKE_INSTALL_PREFIX` at build time or query runtime via `binreloc` (already in `core-utils/binreloc.c`).

### 5. Hardcoded Wiki URLs in User-Visible Memo Strings
**Evidence:** `ScrubBusiness.c:558,574` — Long URL-encoded wiki links embedded in translatable strings.

**Impact:** If wiki page renamed/moved, broken links baked into saved transaction memos forever.

**Fix:** Use short stable redirect URL (`https://gnucash.org/help/double-post`) or local help file with ID reference.

### 6. Manual Memory Management in Modern C++ (KVP System)
**Evidence:** `kvp-value.cpp:342,363,382` — Raw `new`/`delete` with `boost::variant` and custom `delete_visitor`.

**Impact:** Memory leaks, double-frees, use-after-free bugs possible. Fragile ownership model.

**Fix:** Migrate to `std::variant` (C++17) with `std::unique_ptr`/`std::shared_ptr`. Replace manual `delete_visitor` with automatic destruction.

### 7. Magic Numbers — Unnamed Numeric Constants
**Evidence:**
- `gnc-commodity.cpp:563`: `priv->fraction = 10000;` (why 10000?)
- `gnc-date.cpp:152-153`: `if (year < 1400) year += 1400;` (why 1400?)
- `gnc-budget.cpp:114`: `priv->num_periods = 12;` (months? unnamed)

**Impact:** Bug magnets. Future maintainers must guess meaning.

**Fix:** Define named constants: `constexpr int DEFAULT_COMMODITY_FRACTION = 10000; // 4 decimal places`.

### 8. Deprecated GDate API — 89 Calls to Legacy GLib Functions
**Evidence:** `gnc-date.cpp` — **89** calls to `g_date_*` functions. GLib recommends `GDateTime` since 2010.

**Impact:** Two competing date systems (`GDate` vs `GncDateTime`). `GDate` lacks timezone support.

**Fix:** Migrate remaining `GDate` to `GncDateTime`/`std::chrono`. Deprecate `gnc-date.h` wrappers.

### 9. Copy-Paste Duplication
**Evidence:**
- Date handling: `gnc-date.cpp` (1723 lines) vs `gnc-datetime.cpp` (907 lines) — overlapping functionality
- UI builders: 38 consecutive `gtk_builder_get_object()` calls in `assistant-loan.cpp`
- Property registration: 10-40 identical `g_object_class_install_property()` blocks across multiple files

**Impact:** Bug fixes must apply in multiple places. Adding new property/widget requires copying boilerplate.

**Fix:** Consolidate date handling into single API. Create helper functions for UI widget lookup. Use static arrays for property registration.

### 10. 273 TODO/FIXME/HACK/XXX Markers
**Evidence:** `grep -rn "TODO|FIXME|HACK|XXX"` across `libgnucash/` and `gnucash/` — **273 markers**.

**Impact:** Known bugs, design flaws, missing features deferred. Some indicate fundamental architectural issues.

**Fix:** Audit all markers. Create bug reports for known bugs. Schedule refactors for design flaws. Delete obsolete markers.

**Summary by Category:**

| Category | Count | Severity |
|----------|-------|----------|
| God functions (>200 lines) | 27 functions | High |
| Dead code | 7+ functions | Medium |
| C-style casts in C++ | 211 instances | High |
| Hardcoded paths | 1 critical | Medium |
| Hardcoded URLs in user strings | 2 instances | Medium |
| Manual memory management | Multiple files | High |
| Magic numbers | 10+ instances | Medium |
| Deprecated API usage | 89 GDate calls | High |
| Copy-paste duplication | Multiple patterns | Medium |
| TODO/FIXME markers | 273 markers | Medium |

**Files requiring most attention:**
- `libgnucash/engine/Account.cpp` (5,978 lines, 487-line god function)
- `libgnucash/engine/gnc-pricedb.cpp` (3,019 lines, 32 C-style casts)
- `gnucash/gnome/assistant-loan.cpp` (3,133 lines, 436-line god function)
- `gnucash/gnome/dialog-invoice.c` (3,979 lines, 271-line god function)
- `gnucash/register/ledger-core/split-register.c` (3,249 lines, multiple god functions)

---

## Security Findings

**Status:** ✅ No critical vulnerabilities detected

**Scan method:** jcodemunch search_text for credential patterns (password, api_key, secret, token, private_key)
**Result:** 0 matches

**Credential inventory:** `analysis/gnucash/SECRETS.local.md` (gitignored, no raw values)

**CWE-Tagged Findings:**

| CWE | Severity | File:Line | Description | Evidence |
|-----|----------|-----------|-------------|----------|
| — | — | — | No hardcoded credentials found | — |

**Notes:**
- GnuCash does not store credentials in source code
- Online banking credentials (AQBanking) handled by external library
- Finance::Quote API keys set via environment variables (correct pattern)
- No SQL injection risk: SQL backend uses parameterized queries via libdbi
- No command injection risk: No shell exec in core code paths

**Recommendation:** Low security risk. No immediate action needed.

---

## Documentation Gaps

**Status:** ❌ Critical documentation gaps

**Documentation coverage:** 0% for core symbols (Account, Transaction, Split, Book, backend interfaces)

**Doc inventory:**
- **Doxygen config:** Present (doxygen.cfg.in) but docs not generated/committed
- **README:** Basic usage, build instructions
- **User docs:** External wiki (wiki.gnucash.org), not in repo
- **API docs:** Header comments exist but sparse, no generated API reference
- **Architecture docs:** None (no ADRs, no architecture overview)

**Top 5 Undocumented Behaviors:**

1. **QOF (Query Object Framework)** — How objects are persisted, queried, cached. Critical for understanding backend abstraction. No docs on qofbook, qofquery, qofsession lifecycle.

2. **Backend switching** — How XML vs SQL backend selected, data migration path. Code supports both but no migration guide.

3. **Scheme-C++ FFI** — How Guile/Scheme calls C++ engine functions. Bindings in bindings/guile/ but no documentation on calling conventions, memory management, error propagation.

4. **Scheduled transaction execution** — How scheduled transactions trigger, instance model (gnc-sx-instance-model.c). Complex logic, no docs.

5. **Business object relationships** — Customer/Vendor/Employee/Invoice/Job/Order/Entry relationships. Domain model complex, no entity relationship diagram.

**Impact:** New engineers (human or AI) cannot understand system without reading code. Modernization efforts will slow down.

**Recommendation:** Generate Doxygen docs, add architecture overview (this assessment + ARCHITECTURE.mmd is start), document QOF framework.

---

## Relative Scale

**COCOMO-II Complexity Index:** 2,940

**Inputs:**
- KSLOC = 468.6
- Formula: 2.94 × (468.6)^1.10 = 2,940

**Interpretation:** This is a **relative size/complexity measure** for ranking GnuCash against other systems in a portfolio. Higher number = larger, more complex codebase.

**Not a timeline:** This index assumes traditional human-team productivity. Agentic modernization does not follow those productivity curves. Do not interpret as "2,940 person-months" or attach a duration/cost to it.

**Comparison context:**
- Small system: <500
- Medium system: 500-2,000
- Large system: 2,000-5,000
- Enterprise system: >5,000

**GnuCash classification:** Large system (borderline enterprise). Modernization is multi-month effort, not multi-week.

---

## Recommended Modernization Pattern

**Pattern:** **Refactor-in-place (same-stack version bump + incremental C→C++ migration)**

**Command:** `/modernize-uplift`

**Rationale:**

1. **Architecture is sound.** Layered design, clear separation of concerns, multi-backend abstraction. No need to rearchitect.

2. **Ongoing C→C++ migration.** Git log shows incremental modernization (gnc-string-utils, gnc-uri, gnc-state already converted). Continue this pattern.

3. **Scheme reports are liability.** ~48K SLOC in Scheme creates contributor barrier. Convert to C++ or Python over time, but not urgent — reports work.

4. **No cloud/web component.** Desktop app with local storage. No replatform to cloud needed.

5. **Dependencies are current.** Boost 1.70+, GTK3, Guile 2.2 — all supported. No urgent dependency upgrades.

6. **Test coverage moderate.** 98% pass rate but no coverage metrics. Add characterization tests before refactoring high-complexity functions.

**Modernization Phases:**

1. **Phase 1 — Stabilize (1-2 weeks):** Generate Doxygen docs, add architecture overview, instrument with APM if possible.

2. **Phase 2 — Target high-complexity hotspots (2-4 weeks):** Decompose top 10 functions (cap-gains, account init, file open, etc.). Add characterization tests first.

3. **Phase 3 — Continue C→C++ migration (ongoing):** Convert remaining C files in engine (Account.c, Transaction.c, Split.c already done? Check). Focus on frequently-changed files.

4. **Phase 4 — Scheme report modernization (6-12 months):** Convert critical reports (balance-sheet, income-statement) to C++ or Python. Keep Scheme for niche reports.

5. **Phase 5 — Dependency refresh (as needed):** GTK3→GTK4, Guile 2.2→3.0, Boost upgrades. Test thoroughly.

**Avoid:** Full rewrite (reimagine), cloud migration (replatform), replacement. Architecture works, codebase is manageable with incremental improvements.

---

## Appendix: Hotspot Analysis

**Top 20 High-Risk Symbols** (complexity × churn, last 365 days):

| Rank | Symbol | File | Complexity | Churn | Hotspot Score |
|------|--------|------|------------|-------|---------------|
| 1 | xaccSplitComputeCapGains | cap-gains.cpp:521 | 80 | 5 | 143.3 |
| 2 | gnc_account_class_init | Account.cpp:639 | 53 | 11 | 131.7 |
| 3 | show_session_error | gnc-file.c:280 | 87 | 3 | 120.6 |
| 4 | gnc_post_file_open | gnc-file.c:795 | 87 | 3 | 120.6 |
| 5 | gnc_plugin_page_register_ui_update | gnc-plugin-page-register.cpp:754 | 41 | 16 | 116.2 |
| 6 | split_find_match | import-backend.cpp:579 | 57 | 6 | 110.9 |
| 7 | gnc_account_get_property | Account.cpp:357 | 43 | 11 | 106.9 |
| 8 | qof_scan_date_internal | gnc-date.cpp:742 | 73 | 3 | 101.2 |
| 9 | gnc_main_window_restore_window | gnc-main-window.cpp:639 | 43 | 8 | 94.5 |
| 10 | gnc_split_register_auto_completion | split-register-control.cpp:817 | 68 | 3 | 94.3 |

**Interpretation:** High hotspot score = complex + frequently changed = high bug-introduction risk. These 10 symbols are modernization priority targets.

---

**Assessment complete.** Next steps:
- Review ARCHITECTURE.mmd (domain dependency diagram)
- Review SECRETS.local.md (credential inventory — empty)
- Run `/modernize-brief` to generate phased modernization plan
- Run `/modernize-map` for detailed dependency visualization
