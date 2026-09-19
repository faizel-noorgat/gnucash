# GnuCash Same-Stack Uplift Delta Catalog

**Current Stack:**
- C/C++ (mixed C and C++11/14) → **Target:** C++17/20
- CMake 3.14.5+ → **Target:** CMake 3.20+
- Boost 1.70+ → **Target:** Boost 1.80+
- GTK3 3.22+ → **Target:** GTK4 (major version bump)
- Guile 2.2 → **Target:** Guile 3.0 (major version bump)
- Latest libdbi, libOFX, aqbanking

**Analysis Date:** 2026-09-19

---

## Executive Summary

This catalog identifies **concrete breaking changes** that will impact the GnuCash codebase during the same-stack uplift. The analysis focuses on what actually breaks, not theoretical improvements. Each delta includes severity, affected files, and migration guidance.

**Key Findings:**
- **GTK3 → GTK4** is the **most disruptive change** with widespread API breaks
- **Guile 2.2 → 3.0** requires careful migration of Scheme bindings
- **C++17/20** is already partially adopted (codebase uses C++17 standard)
- **Boost 1.70 → 1.80** has minimal breaking changes for current usage
- **CMake 3.14.5 → 3.20+** requires policy updates but is largely mechanical

---

## Delta Cards

### DELTA-001: GTK3 → GTK4 Widget Container API Changes
**Category:** Framework (GTK4 breaking change)
**Severity:** BLOCKING
**Where this code hits it:** 
- `gnucash/gnome/*.cpp` - 71 sites using `gtk_container_add`, `gtk_box_pack_start`, `gtk_box_pack_end`
- All UI construction code in gnome/ directory

**Source → Target:** 
- GTK3: `gtk_container_add(container, child)`, `gtk_box_pack_start(box, child, ...)`
- GTK4: `gtk_box_append(box, child)`, removed `gtk_container_add` (replaced with type-specific methods)

**Migration Path:**
1. Replace `gtk_box_pack_start(box, child, expand, fill, padding)` with `gtk_box_append(box, child)`
2. Replace `gtk_box_pack_end(box, child, ...)` with `gtk_box_prepend(box, child)`
3. Replace `gtk_container_add(container, child)` with appropriate child-adding method
4. Set expand/fill properties via `gtk_widget_set_hexpand()`, `gtk_widget_set_vexpand()`

**Test Impact:** 
- All GUI tests need review
- Manual testing required for visual layout correctness
- No automated migration tool available

**Confidence:** HIGH - Well-documented GTK4 migration path

---

### DELTA-002: GTK3 → GTK4 Dialog API Removal
**Category:** Framework (GTK4 breaking change)
**Severity:** BLOCKING
**Where this code hits it:**
- `gnucash/gnome/*.cpp` - 21 sites using `gtk_dialog_run()`
- `gnucash/gnome/dialog-*.cpp` files

**Source → Target:**
- GTK3: `gtk_dialog_run(GTK_DIALOG(dialog))` - blocking modal dialog
- GTK4: `gtk_dialog_run()` removed entirely; must use async pattern with `gtk_dialog_show()` + signal handlers

**Migration Path:**
1. Replace modal `gtk_dialog_run()` loop with async callback pattern
2. Use `g_signal_connect(dialog, "response", callback, user_data)` 
3. Refactor calling code to handle async responses
4. Consider using `GtkAlertDialog` for simple message dialogs (GTK4.10+)

**Test Impact:**
- Dialog flow tests need complete rewrite
- Async testing framework may be needed
- User interaction tests require async handling

**Confidence:** HIGH - Documented GTK4 breaking change with no backward compatibility

---

### DELTA-003: GTK3 → GTK4 Event Handling Namespace Changes
**Category:** Framework (GTK4 breaking change)
**Severity:** NEEDS-REFACTOR
**Where this code hits it:**
- `gnucash/gnome/*.cpp` - 145 sites using `g_signal_connect`
- Key event handling: `GDK_KEY_*` constants
- Event types: `GDK_BUTTON_PRESS`, `GDK_2BUTTON_PRESS`, etc.

**Source → Target:**
- GTK3: `GDK_KEY_Escape`, `GDK_BUTTON_PRESS`
- GTK4: `GDK_KEY_Escape` (unchanged), but event types moved to `GDK_BUTTON_PRESS` → use event controllers
- GTK4: Event handling moved to `GtkEventController` model

**Migration Path:**
1. Replace direct event signal connections with `GtkEventController` subclasses
2. Use `gtk_widget_add_controller(widget, controller)`
3. Key events: `GtkEventControllerKey`
4. Mouse events: `GtkGestureClick`, `GtkEventControllerMotion`
5. Update event structure access patterns

**Test Impact:**
- Event handling tests need update
- Input method handling may change
- Touch/gesture support improved but API changed

**Confidence:** HIGH - Major GTK4 architectural change

---

### DELTA-004: GTK3 → GTK4 Widget Margin API Deprecation
**Category:** Framework (GTK4 breaking change)
**Severity:** NEEDS-REFACTOR
**Where this code hits it:**
- `gnucash/gnome/*.cpp` - margin setting code
- Note: Initial scan found 0 direct margin API calls (may use CSS or other methods)

**Source → Target:**
- GTK3: `gtk_widget_set_margin_left/right/top/bottom(widget, margin)`
- GTK4: Replaced with `gtk_widget_set_margin_start/end/top/bottom(widget, margin)` (RTL-aware)

**Migration Path:**
1. Replace `set_margin_left` → `set_margin_start`
2. Replace `set_margin_right` → `set_margin_end`
3. Update CSS if using margin properties

**Test Impact:**
- Visual layout testing required
- RTL (right-to-left) language support may improve

**Confidence:** MEDIUM - Need to verify actual usage patterns in codebase

---

### DELTA-005: GTK3 → GTK4 Drawing Model Changes
**Category:** Framework (GTK4 breaking change)
**Severity:** NEEDS-REFACTOR
**Where this code hits it:**
- Custom drawing code in `gnucash/gnome/`
- Any code using `gtk_widget_draw()` or `GtkDrawingArea`

**Source → Target:**
- GTK3: `gtk_widget_queue_draw()`, expose-event handlers
- GTK4: Snapshot-based drawing with `GtkSnapshot`, `gtk_widget_snapshot()`
- Removed: Direct Cairo context access in draw handlers

**Migration Path:**
1. Replace `GtkDrawingArea` draw callbacks with snapshot functions
2. Use `gtk_snapshot_append_*` methods instead of Cairo calls
3. Refactor custom widgets to use snapshot API

**Test Impact:**
- Custom widget rendering tests need update
- Visual regression testing recommended

**Confidence:** MEDIUM - Depends on custom widget usage

---

### DELTA-006: Guile 2.2 → 3.0 SMOB and Foreign Object API
**Category:** Language (Guile breaking change)
**Severity:** NEEDS-REFACTOR
**Where this code hits it:**
- `bindings/guile/*.cpp` - C interface to Scheme
- `bindings/guile/*.scm` - Scheme bindings
- 15 sites using string conversion APIs

**Source → Target:**
- Guile 2.2: SMOB API, `scm_from_locale_string()`, `scm_to_locale_string()`
- Guile 3.0: Same APIs but with performance improvements; some deprecated patterns
- Guile 3.0: JIT compilation may expose undefined behavior

**Migration Path:**
1. Review SMOB usage patterns (initial scan found minimal usage)
2. Test string encoding/decoding with UTF-8 locale
3. Verify foreign function interface compatibility
4. Test with Guile 3.0 JIT enabled

**Test Impact:**
- Scheme binding tests need execution under Guile 3.0
- Performance characteristics may change (faster but different)
- Memory management patterns should be validated

**Confidence:** MEDIUM - Guile maintains good backward compatibility but JIT may expose issues

---

### DELTA-007: Guile 2.2 → 3.0 Module System and Syntax
**Category:** Language (Guile breaking change)
**Severity:** COSMETIC
**Where this code hits it:**
- `bindings/guile/*.scm` - 57 `define-public` patterns
- `define-syntax` usage for macros

**Source → Target:**
- Guile 2.2: Module system, syntax-rules, define-syntax
- Guile 3.0: Same syntax but improved expansion; some edge cases may differ

**Migration Path:**
1. Test all Scheme modules under Guile 3.0
2. Verify macro expansion behavior
3. Check for deprecated module imports
4. Update any uses of removed procedures

**Test Impact:**
- Run full Scheme test suite under Guile 3.0
- Verify option handling (gnc-optiondb.i is large)
- Test report generation (uses Scheme heavily)

**Confidence:** HIGH - Guile 3.0 designed for backward compatibility

---

### DELTA-008: C++17/20 Standard Library Changes
**Category:** Language (C++ standard evolution)
**Severity:** COSMETIC
**Where this code hits it:**
- Already using C++17 (`set(CMAKE_CXX_STANDARD 17)`)
- All `.cpp` files in libgnucash/ and gnucash/

**Source → Target:**
- Current: C++17 standard
- Target: C++20 (optional, C++17 is acceptable)

**Key Changes:**
- C++17: `std::auto_ptr` removed (not used in codebase - good)
- C++17: `register` keyword removed (not used as keyword - good)
- C++20: `std::random_shuffle` removed (check usage)
- C++20: Three-way comparison operator `<=>` available
- C++20: Concepts, ranges, coroutines (optional features)

**Migration Path:**
1. Code already uses C++17 - minimal changes needed
2. For C++20: Review use of removed features
3. Consider adopting `std::optional`, `std::variant`, `std::string_view`
4. Update smart pointer usage (already using modern patterns)

**Test Impact:**
- Compile with `-std=c++20` to identify issues
- Run existing test suite
- No major breakage expected

**Confidence:** HIGH - Codebase already modernized to C++17

---

### DELTA-009: Boost 1.70 → 1.80 API Changes
**Category:** Library (Boost version bump)
**Severity:** COSMETIC
**Where this code hits it:**
- `libgnucash/engine/gnc-date.cpp` - Boost.DateTime
- `libgnucash/core-utils/gnc-locale-utils.cpp` - Boost.Locale
- `libgnucash/engine/guid.cpp` - Boost.UUID
- `libgnucash/engine/kvp-value.cpp` - Boost.Variant
- CMake requires Boost 1.67.0+

**Source → Target:**
- Boost 1.70 → 1.80: Minimal breaking changes
- Boost.DateTime: Stable API
- Boost.Locale: Some deprecations
- Boost.UUID: Stable
- Boost.Variant → Boost.Variant2 (optional migration)

**Migration Path:**
1. Update CMake: `find_package(Boost 1.80 REQUIRED)`
2. Review Boost.Locale usage for deprecations
3. Test date/time handling (critical for financial app)
4. Consider migrating `boost::variant` → `std::variant` (C++17)

**Test Impact:**
- Date/time calculations need validation
- Locale handling tests required
- UUID generation tests
- Performance testing (Boost 1.80 has improvements)

**Confidence:** HIGH - Boost maintains strong backward compatibility

---

### DELTA-010: CMake 3.14.5 → 3.20+ Policy Changes
**Category:** Build System (CMake evolution)
**Severity:** NEEDS-REFACTOR
**Where this code hits it:**
- `/projects/gnucash/CMakeLists.txt`
- All `CMakeLists.txt` files in subdirectories
- `cmake/*.cmake` modules

**Source → Target:**
- CMake 3.14.5 → 3.20+: Multiple policy changes
- New policies: CMP0097, CMP0099, CMP0100, etc.
- Deprecated: Some old Find modules
- Improved: Package discovery, target-based approach

**Migration Path:**
1. Update `cmake_minimum_required(VERSION 3.20)`
2. Set policy versions: `cmake_policy(VERSION 3.20)`
3. Update `find_package()` calls to use modern targets
4. Replace deprecated Find modules with Config packages
5. Use `target_link_libraries()` with imported targets

**Specific Changes Needed:**
- GTK: Already using `pkg_check_modules` with `IMPORTED_TARGET` (good)
- Boost: Using `find_package(Boost ...)` - update to use targets
- Guile: Using `pkg_check_modules` - already modern

**Test Impact:**
- Clean build from scratch required
- Test all platforms (Linux, macOS, Windows)
- Verify package discovery on clean systems

**Confidence:** HIGH - Well-documented CMake migration path

---

### DELTA-011: GTK4 → GLib 2.68+ API Requirements
**Category:** Framework (GTK4 dependency)
**Severity:** BLOCKING
**Where this code hits it:**
- All GLib usage throughout codebase
- `g_type_init()` usage (deprecated in GLib 2.36, removed later)

**Source → Target:**
- GTK4 requires GLib 2.68+
- Current: GLib 2.x (version tied to GTK3)
- Removed: `g_type_init()` (no longer needed)

**Migration Path:**
1. Remove `g_type_init()` calls (found 1 site)
2. Update GLib version requirements in CMake
3. Review deprecated GLib functions
4. Test with GLib 2.68+

**Test Impact:**
- Type system initialization tests
- Main loop handling
- Threading model (improved in newer GLib)

**Confidence:** HIGH - Documented GTK4 requirement

---

### DELTA-012: GTK4 → GDK Namespace Reorganization
**Category:** Framework (GTK4 breaking change)
**Severity:** NEEDS-REFACTOR
**Where this code hits it:**
- `gnucash/gnome/*.cpp` - 10+ sites using GDK constants
- Event handling code

**Source → Target:**
- GTK3: `GDK_KEY_*`, `GDK_BUTTON_PRESS`, etc.
- GTK4: Reorganized namespace; some moved to `GDK_*` from `GDK_*`
- Event types: More consistent naming

**Migration Path:**
1. Update GDK constant names (mostly compatible)
2. Review event structure access
3. Update display/screen API calls
4. Test multi-monitor support

**Test Impact:**
- Keyboard shortcut tests
- Mouse event tests
- Display configuration tests

**Confidence:** HIGH - Documented namespace changes

---

### DELTA-013: GTK3 → GTK4 Window and Application Model
**Category:** Framework (GTK4 breaking change)
**Severity:** NEEDS-REFACTOR
**Where this code hits it:**
- `gnucash/gnucash-core-app.cpp`
- `gnucash/gnucash.cpp`
- Main application setup

**Source → Target:**
- GTK3: `GtkApplication`, `GtkWindow` hierarchy
- GTK4: Same model but with changes to window management
- Removed: Some window positioning APIs
- Changed: Default window behavior

**Migration Path:**
1. Review `GtkApplication` setup
2. Update window creation code
3. Test window positioning and sizing
4. Verify modal dialog behavior

**Test Impact:**
- Application startup tests
- Window management tests
- Multi-window scenarios

**Confidence:** MEDIUM - Core application structure

---

### DELTA-014: libdbi, libOFX, aqbanking Version Updates
**Category:** Library (Dependency updates)
**Severity:** COSMETIC
**Where this code hits it:**
- `libgnucash/backend/dbi/` - libdbi usage
- `gnucash/import-export/ofx/` - libOFX usage
- AqBanking integration

**Source → Target:**
- Latest versions of each library
- API compatibility generally maintained
- Some function deprecations

**Migration Path:**
1. Update CMake version requirements
2. Review deprecated function usage
3. Test import/export functionality
4. Verify online banking features

**Test Impact:**
- OFX import tests
- Database backend tests
- AqBanking transaction tests
- Online banking feature tests

**Confidence:** MEDIUM - Library-specific changes need review

---

## Summary Table

| Delta | Category | Severity | Sites | Migration Effort |
|-------|----------|----------|-------|------------------|
| GTK4 Container API | Framework | BLOCKING | 71 | High |
| GTK4 Dialog API | Framework | BLOCKING | 21 | High |
| GTK4 Event Handling | Framework | NEEDS-REFACTOR | 145 | Medium |
| GTK4 Margins | Framework | NEEDS-REFACTOR | ? | Low |
| GTK4 Drawing Model | Framework | NEEDS-REFACTOR | ? | Medium |
| Guile 3.0 SMOB | Language | NEEDS-REFACTOR | 15 | Low |
| Guile 3.0 Modules | Language | COSMETIC | 57 | Low |
| C++17/20 | Language | COSMETIC | All | Low |
| Boost 1.80 | Library | COSMETIC | 19+ | Low |
| CMake 3.20+ | Build | NEEDS-REFACTOR | All | Medium |
| GLib 2.68+ | Framework | BLOCKING | 1 | Low |
| GDK Namespace | Framework | NEEDS-REFACTOR | 10+ | Low |
| GTK4 Window Model | Framework | NEEDS-REFACTOR | Core | Medium |
| Library Updates | Library | COSMETIC | Various | Low |

---

## Recommended Migration Order

1. **Phase 1: Foundation (Low Risk)**
   - CMake 3.14.5 → 3.20+ (mechanical, test with clean build)
   - Boost 1.70 → 1.80 (test date/time, locale)
   - C++17/20 adoption (already partially done)

2. **Phase 2: Guile Migration (Medium Risk)**
   - Guile 2.2 → 3.0 (test all Scheme bindings)
   - Verify option handling, report generation

3. **Phase 3: GTK4 Migration (High Risk - Major Effort)**
   - Start with non-UI code using GLib
   - Migrate container APIs (DELTA-001)
   - Migrate dialog APIs (DELTA-002)
   - Migrate event handling (DELTA-003)
   - Update drawing code (DELTA-005)
   - Test thoroughly on all platforms

4. **Phase 4: Library Updates (Low Risk)**
   - libdbi, libOFX, aqbanking updates
   - Test import/export functionality

---

## Testing Strategy

**Pre-Migration:**
- Establish comprehensive test coverage baseline
- Run full test suite on current stack
- Document any existing test failures

**During Migration:**
- Compile after each delta implementation
- Run unit tests after each phase
- Manual GUI testing for GTK4 changes
- Performance testing for Guile 3.0

**Post-Migration:**
- Full regression test suite
- Platform-specific testing (Linux, macOS, Windows)
- User acceptance testing for UI changes
- Performance benchmarking

---

## References

- [GTK4 Migration Guide](https://docs.gtk.org/gtk4/migrating.html)
- [Guile 3.0 Manual](https://www.gnu.org/software/guile/manual/html_node/)
- [CMake Policy Documentation](https://cmake.org/cmake/help/latest/manual/cmake-policies.7.html)
- [Boost Version History](https://www.boost.org/users/history/)
- [C++17/20 Standard](https://en.cppreference.com/w/cpp/language)

---

**Report Generated:** 2026-09-19
**Analyzed By:** Migration Analysis Tool
**Status:** Ready for Review
