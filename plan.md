# 3-CNF-SAT Phase Transition Experiment

## Project Overview

Demonstrate the phase transition in random 3-CNF-SAT problems. Difficulty depends on the clause-to-variable ratio (m), with a critical threshold around m ≈ 4.267 where problems transition from "almost always satisfiable" to "almost always unsatisfiable."

## Global Parameters

- **Variable count:** n = 100 (fallback to n = 50 if solver is too slow)
- **Clause-to-variable ratios:** m from 1.0 to 8.0 in steps of 0.25 (29 values)
- **Trials per m value:** 25
- **Solver timeout:** 10 seconds per instance
- **Randomness:** No fixed seed
- **Output:** Per-m summaries only (verbose mode available via flag for debugging)

## Data Representation

- **Variables:** Positive integers 1 to n
- **Literals:** Signed integers; positive k = xₖ, negative -k = ¬xₖ
- **Clause:** List of exactly 3 literals, e.g. `[1, -2, 3]` = (x₁ ∨ ¬x₂ ∨ x₃)
- **Formula:** List of clauses (conjunction of disjunctions)

---

# PHASE 1: Random Instance Generator

## `generate(n, m, verbose=False)` → `List[List[int]]`

**Inputs:** `n` = variable count, `m` = clause-to-variable ratio

**Algorithm:**
1. Compute `num_clauses = int(n * m)`
2. For each clause:
   - Sample 3 **distinct** variables without replacement: `random.sample(range(1, n+1), 3)`
   - Negate each independently with probability 0.5: `v * random.choice([1, -1])`
3. Return list of all clauses

This matches the standard random 3-SAT model (the theoretical threshold 4.267 applies to this model).

**Verbose output** (when `verbose=True`):
```
Generating 3-CNF: n={n}, m={m}, clauses={num_clauses}
```

## `validate_instance(instance, n, m)` → `bool`

Checks:
- `len(instance) == int(n * m)`
- Each clause has exactly 3 literals
- All literals l satisfy `1 <= abs(l) <= n`
- Each clause has 3 distinct variables

## Phase 1 Tests

1. **Manual check:** n=3, m=2 → 6 clauses, each with 3 literals in {-3..3}\{0}, all distinct variables per clause
2. **Property checks:** Run `validate_instance` on (n=3,m=2), (n=10,m=1), (n=10,m=5), (n=100,m=4.5)
3. **Statistical check:** 100 instances with n=10, m=3. Each variable should appear ~90 times total. Print mean/stddev.

---

# PHASE 2: SAT Solver

## `solve(instance, timeout=10)` → `"SAT"` | `"UNSAT"` | `"TIMEOUT"`

Returns a three-valued result to distinguish unsatisfiable from timed-out instances.

### DPLL Algorithm

```
function DPLL(formula, assignment):
    if elapsed_time > timeout: raise TimeoutError

    simplified = simplify(formula, assignment)

    if simplified is empty: return True           # all clauses satisfied
    if simplified contains empty clause: return False  # conflict

    # Unit propagation
    while unit clause [l] exists:
        assign variable(l) per sign of l
        re-simplify; if empty clause → return False

    # Pure literal elimination
    while pure literal l exists:
        assign variable(l) per sign of l
        re-simplify

    # Branch on first unassigned variable in formula
    var = pick_unassigned_variable(simplified)
    return DPLL(simplified, assignment ∪ {var: True})
        or DPLL(simplified, assignment ∪ {var: False})
```

**Wrapper:** `solve()` calls DPLL in a try/except. TimeoutError → return `"TIMEOUT"`. True → `"SAT"`. False → `"UNSAT"`.

### Key Implementation Details

- **Assignment:** `dict[int, bool]` mapping variable → value
- **Simplify:** Remove clauses with any True literal; remove False literals from remaining clauses
- **Timeout:** Check `time.time() - start > timeout` at each recursive call; raise on expiry
- **Variable selection:** First unassigned variable in first clause (simple, adequate)

### Helper Functions

1. `simplify(formula, assignment)` → simplified formula
2. `find_unit_clauses(formula)` → list of unit literals
3. `find_pure_literals(formula)` → list of pure literals
4. `get_variables(formula)` → set of variables

## Phase 2 Tests

### Satisfiable (should return `"SAT"`)
```python
assert solve([]) == "SAT"                           # empty formula
assert solve([[1]]) == "SAT"                        # single unit
assert solve([[1, 2, 3]]) == "SAT"                  # single clause
assert solve([[1, 2, 3], [4, 5, 6]]) == "SAT"      # independent clauses
assert solve([[1, 2, 3], [1, -3, 2], [-2, -3, 1]]) == "SAT"
```

### Unsatisfiable (should return `"UNSAT"`)
```python
assert solve([[1], [-1]]) == "UNSAT"                # contradictory units
assert solve([[1, 2], [-1], [-2]]) == "UNSAT"       # forced conflict
# All sign combinations over 2 variables — no assignment satisfies all 4:
assert solve([[1, 2], [1, -2], [-1, 2], [-1, -2]]) == "UNSAT"
```

### Random small instances
- Generate 10 instances with n=5, m=2; solve each; print results

### Performance
- n=20, m=3 → should complete in < 1s
- n=50, m=3 → should complete in < 5s

### Timeout
- n=100, m=6, timeout=1s → should return `"TIMEOUT"` (or `"UNSAT"` if fast enough)

---

# PHASE 3: Experimental Harness

## `run_experiment(n, m_values, trials_per_m, timeout)` → results dict

### Output Structure

```python
{
    m: {"sat": int, "unsat": int, "timeout": int}
    for each m in m_values
}
```

### Algorithm

```
for m in m_values:
    counters = {"sat": 0, "unsat": 0, "timeout": 0}
    for trial in range(trials_per_m):
        instance = generate(n, m)
        result = solve(instance, timeout)
        counters[result.lower()] += 1
    results[m] = counters
    print summary line for this m value
```

### Console Output (per-m only)

```
m=1.00: SAT=25  UNSAT=0   TIMEOUT=0   (100.0% sat)
m=1.25: SAT=24  UNSAT=1   TIMEOUT=0   (96.0% sat)
...
m=8.00: SAT=0   UNSAT=25  TIMEOUT=0   (0.0% sat)
```

### CSV Output (`sat_results.csv`)

Columns: `m, sat_count, unsat_count, timeout_count, trials, fraction_sat`

## Phase 3 Tests

1. **Dry run:** n=10, m_values=[1.0, 3.0, 6.0], trials=3. Verify loop works, output is correct.
2. **Medium run:** n=50, m_values=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0], trials=10. Verify trend: high sat at low m, low sat at high m.
3. **Full experiment:** n=100, full m range, trials=25.

### Expected Results

| m   | Fraction Satisfiable |
|-----|---------------------|
| 1.0 | ~1.00               |
| 2.0 | ~1.00               |
| 3.0 | ~0.95-1.00          |
| 4.0 | ~0.50-0.80          |
| 4.5 | ~0.20-0.50          |
| 5.0 | ~0.05-0.20          |
| 6.0 | ~0.00-0.05          |
| 7.0 | ~0.00               |
| 8.0 | ~0.00               |

**Performance note:** If the pure Python DPLL solver produces excessive timeouts in the critical region (m ≈ 4-5), reduce n to 50 and re-run.

---

# PHASE 4: Visualization

## `plot_results(results, filename='phase_transition.png')`

### Plot Specs

- **X-axis:** m (clause-to-variable ratio)
- **Y-axis:** fraction satisfiable (sat_count / trials)
- **Main curve:** Blue line with circle markers
- **Reference lines:**
  - Horizontal dashed gray at y=0.5
  - Vertical dashed red at x=4.267 labeled "Theoretical threshold"
- **Optional second curve:** Timeout fraction (dashed orange) to show where solver struggles
- **Figure:** 10x6 inches, grid on, axis ranges [0.5, 8.5] x [-0.05, 1.05]
- **Title:** "Phase Transition in Random 3-CNF-SAT"

### `estimate_transition(results)` → float

Use linear interpolation between the two consecutive m values that bracket fraction = 0.5, rather than just picking the closest point.

## Phase 4 Tests

1. **Mock data plot:** Use synthetic data with known shape; verify plot renders and saves
2. **Real data plot:** After full experiment; visually confirm S-curve around m ≈ 4-5

---

# PHASE 5: Integration

## File Structure

```
sat_experiment.py      # Single file with all functions + main()
sat_results.csv        # Output data
phase_transition.png   # Output plot
```

## `main()` Flow

1. Print parameters
2. Call `run_experiment(n=100, trials_per_m=25, timeout=10)`
3. Save CSV
4. Call `plot_results(results)`
5. Print `estimate_transition(results)`

## Phase 5 Tests

1. **Syntax check:** `python -c "import sat_experiment"`
2. **Small end-to-end:** n=20, m=[1,2,3,4,5,6], trials=5, timeout=5. Should complete in < 1 min.
3. **Full run:** `python sat_experiment.py`. Should produce CSV + plot with visible phase transition.

---

# Debugging Quick Reference

- **All SAT even at high m** → solver returning SAT by default; check UNSAT logic
- **All UNSAT even at low m** → solver returning UNSAT by default; check SAT base case
- **No transition** → verify m values are actually varying
- **Too many timeouts** → reduce n or increase timeout
- **Jagged curve** → increase trials_per_m

---

# Success Criteria

- Generator creates valid random 3-CNF instances with distinct variables per clause
- Solver correctly returns SAT/UNSAT/TIMEOUT
- Experiment completes without errors
- Plot shows clear S-curve phase transition around m ≈ 4-5
- Low m → >90% satisfiable; High m → <10% satisfiable
