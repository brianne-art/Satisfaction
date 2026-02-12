"""
3-CNF-SAT Phase Transition Experiment

Demonstrates the phase transition in random 3-CNF-SAT as a function
of the clause-to-variable ratio.
"""

import random
import time
import csv
import statistics
from typing import List, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ============================================================================
# PHASE 1: GENERATOR
# ============================================================================

def generate(n: int, m: float, verbose: bool = False) -> List[List[int]]:
    """Generate a random 3-CNF-SAT instance.

    Samples 3 distinct variables per clause, each negated independently
    with probability 0.5. This matches the standard random 3-SAT model.
    """
    num_clauses = int(n * m)
    if verbose:
        print(f"Generating 3-CNF: n={n}, m={m}, clauses={num_clauses}")

    clauses = []
    for _ in range(num_clauses):
        vars_ = random.sample(range(1, n + 1), 3)
        clause = [v * random.choice((1, -1)) for v in vars_]
        clauses.append(clause)
    return clauses


def validate_instance(instance: List[List[int]], n: int, m: float) -> bool:
    """Validate structural properties of a 3-CNF instance."""
    expected = int(n * m)
    if len(instance) != expected:
        print(f"FAIL: expected {expected} clauses, got {len(instance)}")
        return False
    for i, clause in enumerate(instance):
        if len(clause) != 3:
            print(f"FAIL: clause {i} has {len(clause)} literals")
            return False
        for lit in clause:
            if lit == 0 or abs(lit) > n:
                print(f"FAIL: clause {i} has invalid literal {lit}")
                return False
        if len({abs(l) for l in clause}) != 3:
            print(f"FAIL: clause {i} has duplicate variables: {clause}")
            return False
    return True


# ============================================================================
# PHASE 2: SOLVER
# ============================================================================

class _Timeout(Exception):
    pass


def simplify(formula: List[List[int]], assignment: Dict[int, bool]) -> List[List[int]]:
    """Simplify formula under a partial assignment.

    - Clauses with any True literal are removed (satisfied).
    - False literals are removed from remaining clauses.
    - Unassigned literals are kept as-is.
    """
    result = []
    for clause in formula:
        new_clause = []
        satisfied = False
        for lit in clause:
            var = abs(lit)
            if var not in assignment:
                new_clause.append(lit)
                continue
            val = assignment[var]
            # lit positive → True when val is True; lit negative → True when val is False
            if (lit > 0) == val:
                satisfied = True
                break
            # literal is False under assignment — drop it
        if not satisfied:
            result.append(new_clause)
    return result


def find_unit_clauses(formula: List[List[int]]) -> List[int]:
    """Return literals from all unit (single-literal) clauses."""
    return [clause[0] for clause in formula if len(clause) == 1]


def find_pure_literals(formula: List[List[int]]) -> List[int]:
    """Return one representative literal for each pure variable.

    A literal is pure if it appears in the formula but its negation does not.
    """
    lit_set: set[int] = set()
    for clause in formula:
        for lit in clause:
            lit_set.add(lit)
    pure = []
    for lit in lit_set:
        if -lit not in lit_set:
            pure.append(lit)
    return pure


def get_variables(formula: List[List[int]]) -> set[int]:
    """Return the set of variables appearing in the formula."""
    return {abs(lit) for clause in formula for lit in clause}


def solve(instance: List[List[int]], timeout: float = 10) -> str:
    """Solve a CNF instance using DPLL with unit propagation and pure literal elimination.

    Returns "SAT", "UNSAT", or "TIMEOUT".
    """
    start = time.time()

    def dpll(formula: List[List[int]], assignment: Dict[int, bool]) -> bool:
        if time.time() - start > timeout:
            raise _Timeout

        formula = simplify(formula, assignment)

        # All clauses satisfied
        if not formula:
            return True
        # Empty clause → conflict
        if any(len(c) == 0 for c in formula):
            return False

        # Unit propagation
        while True:
            units = find_unit_clauses(formula)
            if not units:
                break
            for lit in units:
                var = abs(lit)
                if var not in assignment:
                    assignment[var] = lit > 0
            formula = simplify(formula, assignment)
            if any(len(c) == 0 for c in formula):
                return False
            if not formula:
                return True

        # Pure literal elimination
        pures = find_pure_literals(formula)
        if pures:
            for lit in pures:
                var = abs(lit)
                if var not in assignment:
                    assignment[var] = lit > 0
            formula = simplify(formula, assignment)
            if not formula:
                return True
            if any(len(c) == 0 for c in formula):
                return False

        # Pick first unassigned variable from first clause
        var = abs(formula[0][0])

        # Branch True
        a_true = dict(assignment)
        a_true[var] = True
        if dpll(formula, a_true):
            return True

        # Branch False
        a_false = dict(assignment)
        a_false[var] = False
        return dpll(formula, a_false)

    try:
        if dpll(instance, {}):
            return "SAT"
        return "UNSAT"
    except _Timeout:
        return "TIMEOUT"


# ============================================================================
# PHASE 3: EXPERIMENTAL HARNESS
# ============================================================================

def run_experiment(
    n: int = 100,
    m_values: List[float] = None,
    trials_per_m: int = 25,
    timeout: float = 10,
) -> Dict[float, Dict[str, int]]:
    """Run the phase transition experiment.

    Returns {m: {"sat": int, "unsat": int, "timeout": int}} for each m value.
    """
    if m_values is None:
        m_values = [i * 0.25 for i in range(4, 33)]  # 1.0 to 8.0 by 0.25

    total = len(m_values) * trials_per_m
    print(f"Experiment: n={n}, {len(m_values)} m-values, "
          f"{trials_per_m} trials each, {total} total solves")

    results: Dict[float, Dict[str, int]] = {}
    for m in m_values:
        counters = {"sat": 0, "unsat": 0, "timeout": 0}
        for trial in range(trials_per_m):
            instance = generate(n, m)
            result = solve(instance, timeout)
            counters[result.lower()] += 1
        results[m] = counters
        frac = counters["sat"] / trials_per_m
        print(f"  m={m:<5.2f}: SAT={counters['sat']:<3d} "
              f"UNSAT={counters['unsat']:<3d} "
              f"TIMEOUT={counters['timeout']:<3d} "
              f"({frac:6.1%} sat)")

    return results


def save_csv(results: Dict[float, Dict[str, int]], trials_per_m: int,
             filename: str = "sat_results.csv") -> None:
    """Save experiment results to CSV."""
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["m", "sat_count", "unsat_count", "timeout_count",
                         "trials", "fraction_sat"])
        for m in sorted(results):
            c = results[m]
            total = c["sat"] + c["unsat"] + c["timeout"]
            writer.writerow([m, c["sat"], c["unsat"], c["timeout"],
                             total, c["sat"] / total])
    print(f"Results saved to {filename}")


# ============================================================================
# PHASE 4: VISUALIZATION
# ============================================================================

def estimate_transition(results: Dict[float, Dict[str, int]],
                        trials_per_m: int) -> float:
    """Estimate the m value where fraction satisfiable crosses 0.5.

    Uses linear interpolation between the two consecutive m values
    that bracket fraction = 0.5.
    """
    m_sorted = sorted(results)
    fracs = [results[m]["sat"] / trials_per_m for m in m_sorted]

    # Find first index where fraction drops below 0.5
    for i in range(1, len(m_sorted)):
        if fracs[i - 1] >= 0.5 and fracs[i] < 0.5:
            # Linear interpolation
            m0, m1 = m_sorted[i - 1], m_sorted[i]
            f0, f1 = fracs[i - 1], fracs[i]
            return m0 + (0.5 - f0) * (m1 - m0) / (f1 - f0)

    # Fallback: closest to 0.5
    best = min(range(len(m_sorted)), key=lambda i: abs(fracs[i] - 0.5))
    return m_sorted[best]


def plot_results(results: Dict[float, Dict[str, int]],
                 trials_per_m: int,
                 filename: str = "phase_transition.png") -> None:
    """Create phase transition plot and save to file."""
    m_values = sorted(results)
    sat_frac = [results[m]["sat"] / trials_per_m for m in m_values]
    timeout_frac = [results[m]["timeout"] / trials_per_m for m in m_values]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Main curve
    ax.plot(m_values, sat_frac, "o-", linewidth=2, markersize=6,
            color="tab:blue", label=f"n={len(m_values)} points, {trials_per_m} trials")

    # Timeout curve (if any timeouts occurred)
    if any(t > 0 for t in timeout_frac):
        ax.plot(m_values, timeout_frac, "s--", linewidth=1.5, markersize=4,
                color="tab:orange", alpha=0.7, label="Timeout fraction")

    # Reference lines
    ax.axhline(y=0.5, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax.axvline(x=4.267, color="red", linestyle="--", linewidth=1, alpha=0.7,
               label="Theoretical threshold (4.267)")

    ax.set_xlabel("Clause-to-Variable Ratio (m)", fontsize=12)
    ax.set_ylabel("Fraction of Satisfiable Instances", fontsize=12)
    ax.set_title("Phase Transition in Random 3-CNF-SAT",
                 fontsize=16, fontweight="bold")
    ax.set_xlim(0.5, 8.5)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    fig.tight_layout()
    fig.savefig(filename, dpi=150)
    plt.close(fig)
    print(f"Plot saved to {filename}")


# ============================================================================
# PHASE 5: INTEGRATION
# ============================================================================

def main() -> None:
    """Run the full phase transition experiment."""
    n = 100
    trials_per_m = 25
    timeout = 10

    print("=" * 60)
    print("3-CNF-SAT PHASE TRANSITION EXPERIMENT")
    print("=" * 60)
    print(f"  n = {n}")
    print(f"  m = 1.0 to 8.0 (step 0.25, 29 values)")
    print(f"  Trials per m: {trials_per_m}")
    print(f"  Solver timeout: {timeout}s")
    print()

    start_time = time.time()
    results = run_experiment(n=n, trials_per_m=trials_per_m, timeout=timeout)
    elapsed = time.time() - start_time

    print(f"\nExperiment completed in {elapsed / 60:.1f} minutes")

    save_csv(results, trials_per_m)
    plot_results(results, trials_per_m)

    threshold = estimate_transition(results, trials_per_m)
    print(f"\nEstimated transition point: m ≈ {threshold:.2f}")
    print("  (theoretical: 4.267)")
    print("\nOutput files:")
    print("  sat_results.csv")
    print("  phase_transition.png")


# ============================================================================
# TESTS
# ============================================================================

def run_tests() -> None:
    """Run all phase tests."""
    import os

    print("=" * 50)
    print("PHASE 1 TESTS")
    print("=" * 50)

    # Test 1: Manual check
    print("\n--- Test 1: Manual check (n=3, m=2) ---")
    inst = generate(3, 2, verbose=True)
    print(f"Instance: {inst}")
    assert validate_instance(inst, 3, 2), "Validation failed"
    print("PASSED")

    # Test 2: Property checks
    print("\n--- Test 2: Property checks ---")
    cases = [(3, 2), (10, 1), (10, 5), (100, 4.5)]
    for n, m in cases:
        inst = generate(n, m)
        ok = validate_instance(inst, n, m)
        print(f"  n={n}, m={m}: {'PASSED' if ok else 'FAILED'}")
        assert ok

    # Test 3: Statistical check
    print("\n--- Test 3: Statistical check (n=10, m=3, 100 instances) ---")
    var_counts = {v: 0 for v in range(1, 11)}
    for _ in range(100):
        inst = generate(10, 3)
        for clause in inst:
            for lit in clause:
                var_counts[abs(lit)] += 1
    counts = list(var_counts.values())
    mean = statistics.mean(counts)
    stdev = statistics.stdev(counts)
    print(f"  Variable appearance counts (over 100 instances):")
    print(f"  Mean: {mean:.1f}  (expected ~900)")
    print(f"  Stdev: {stdev:.1f}")
    assert 800 < mean < 1000, f"Mean {mean} out of expected range"
    print("PASSED")

    print("\nAll Phase 1 tests passed.")

    # ================================================================
    # PHASE 2 TESTS
    # ================================================================
    print("\n" + "=" * 50)
    print("PHASE 2 TESTS")
    print("=" * 50)

    # Test 1: Satisfiable instances
    print("\n--- Test 1: Trivially satisfiable ---")
    assert solve([]) == "SAT", "empty formula"
    assert solve([[1]]) == "SAT", "single unit"
    assert solve([[1, 2, 3]]) == "SAT", "single clause"
    assert solve([[1, 2, 3], [4, 5, 6]]) == "SAT", "independent clauses"
    assert solve([[1, 2, 3], [1, -3, 2], [-2, -3, 1]]) == "SAT", "small solvable"
    print("PASSED")

    # Test 2: Unsatisfiable instances
    print("\n--- Test 2: Unsatisfiable ---")
    assert solve([[1], [-1]]) == "UNSAT", "contradictory units"
    assert solve([[1, 2], [-1], [-2]]) == "UNSAT", "forced conflict"
    assert solve([[1, 2], [1, -2], [-1, 2], [-1, -2]]) == "UNSAT", "all sign combos"
    print("PASSED")

    # Test 3: Random small instances
    print("\n--- Test 3: Random small instances (n=5, m=2) ---")
    for i in range(10):
        inst = generate(5, 2)
        result = solve(inst, timeout=5)
        print(f"  Instance {i+1}: {result}")
    print("PASSED")

    # Test 4: Performance
    print("\n--- Test 4: Performance ---")
    inst = generate(20, 3)
    t0 = time.time()
    result = solve(inst, timeout=5)
    elapsed = time.time() - t0
    print(f"  n=20, m=3: {result} in {elapsed:.3f}s")
    assert elapsed < 1, f"Too slow: {elapsed:.3f}s"

    inst = generate(50, 3)
    t0 = time.time()
    result = solve(inst, timeout=5)
    elapsed = time.time() - t0
    print(f"  n=50, m=3: {result} in {elapsed:.3f}s")
    assert elapsed < 5, f"Too slow: {elapsed:.3f}s"
    print("PASSED")

    # Test 5: Timeout
    print("\n--- Test 5: Timeout ---")
    inst = generate(100, 6)
    t0 = time.time()
    result = solve(inst, timeout=1)
    elapsed = time.time() - t0
    print(f"  n=100, m=6, timeout=1s: {result} in {elapsed:.3f}s")
    assert elapsed < 2, f"Timeout not respected: {elapsed:.3f}s"
    print("PASSED")

    print("\nAll Phase 2 tests passed.")

    # ================================================================
    # PHASE 3 TESTS
    # ================================================================
    print("\n" + "=" * 50)
    print("PHASE 3 TESTS")
    print("=" * 50)

    # Test 1: Dry run
    print("\n--- Test 1: Dry run (n=10) ---")
    results = run_experiment(n=10, m_values=[1.0, 3.0, 6.0],
                             trials_per_m=3, timeout=5)
    assert len(results) == 3
    for m_val, counts in results.items():
        assert counts["sat"] + counts["unsat"] + counts["timeout"] == 3
    print("PASSED")

    # Test 2: Medium run — verify trend
    print("\n--- Test 2: Medium run (n=50) ---")
    m_list = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    results = run_experiment(n=50, m_values=m_list,
                             trials_per_m=10, timeout=10)
    low_sat = results[1.0]["sat"] / 10
    high_sat = results[6.0]["sat"] / 10
    print(f"  Trend check: sat fraction at m=1.0: {low_sat:.0%}, "
          f"at m=6.0: {high_sat:.0%}")
    assert low_sat > high_sat, "Expected higher sat rate at low m"
    print("PASSED")

    # Test 3: CSV output
    print("\n--- Test 3: CSV save ---")
    save_csv(results, 10, filename="sat_results_test.csv")
    with open("sat_results_test.csv") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert rows[0] == ["m", "sat_count", "unsat_count", "timeout_count",
                        "trials", "fraction_sat"]
    assert len(rows) == len(m_list) + 1  # header + data
    os.remove("sat_results_test.csv")
    print("PASSED")

    print("\nAll Phase 3 tests passed.")

    # ================================================================
    # PHASE 4 TESTS
    # ================================================================
    print("\n" + "=" * 50)
    print("PHASE 4 TESTS")
    print("=" * 50)

    # Test 1: Mock data plot
    print("\n--- Test 1: Mock data plot ---")
    mock_results = {
        1.0: {"sat": 10, "unsat": 0, "timeout": 0},
        2.0: {"sat": 10, "unsat": 0, "timeout": 0},
        3.0: {"sat": 9,  "unsat": 1, "timeout": 0},
        4.0: {"sat": 7,  "unsat": 3, "timeout": 0},
        4.5: {"sat": 3,  "unsat": 6, "timeout": 1},
        5.0: {"sat": 1,  "unsat": 9, "timeout": 0},
        6.0: {"sat": 0,  "unsat": 10, "timeout": 0},
        7.0: {"sat": 0,  "unsat": 10, "timeout": 0},
        8.0: {"sat": 0,  "unsat": 10, "timeout": 0},
    }
    plot_results(mock_results, trials_per_m=10, filename="test_plot.png")
    assert os.path.exists("test_plot.png"), "Plot file not created"
    size = os.path.getsize("test_plot.png")
    print(f"  File size: {size:,} bytes")
    assert size > 1000, "Plot file suspiciously small"
    print("PASSED")

    # Test 2: estimate_transition with mock data
    print("\n--- Test 2: estimate_transition ---")
    threshold = estimate_transition(mock_results, trials_per_m=10)
    print(f"  Estimated threshold: {threshold:.2f}")
    assert 4.0 <= threshold <= 5.0, f"Threshold {threshold} out of expected range"
    print("PASSED")

    # Test 3: Plot from Phase 3 medium-run results
    print("\n--- Test 3: Real data plot ---")
    plot_results(results, trials_per_m=10, filename="test_real_plot.png")
    assert os.path.exists("test_real_plot.png"), "Plot file not created"
    print("PASSED")

    # Cleanup test files
    os.remove("test_plot.png")
    os.remove("test_real_plot.png")

    print("\nAll Phase 4 tests passed.")

    # ================================================================
    # PHASE 5 TESTS
    # ================================================================
    print("\n" + "=" * 50)
    print("PHASE 5 TESTS")
    print("=" * 50)

    # Test 1: Small end-to-end
    print("\n--- Test 1: Small end-to-end (n=20) ---")
    r = run_experiment(n=20, m_values=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
                       trials_per_m=5, timeout=5)
    save_csv(r, 5, filename="test_e2e.csv")
    plot_results(r, trials_per_m=5, filename="test_e2e.png")
    threshold = estimate_transition(r, trials_per_m=5)
    print(f"  Estimated transition: {threshold:.2f}")
    assert os.path.exists("test_e2e.csv")
    assert os.path.exists("test_e2e.png")
    os.remove("test_e2e.csv")
    os.remove("test_e2e.png")
    print("PASSED")

    print("\nAll Phase 5 tests passed.")
    print("\n" + "=" * 50)
    print("ALL TESTS PASSED")
    print("=" * 50)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        run_tests()
    else:
        main()
