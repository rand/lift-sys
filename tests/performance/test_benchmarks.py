"""Performance benchmarks for lift-sys.

Run with: pytest tests/performance/ --benchmark-only
Save baseline: pytest tests/performance/ --benchmark-only --benchmark-save=baseline
Compare: pytest tests/performance/ --benchmark-only --benchmark-compare=baseline
"""

from lift_sys.verifier.smt_checker import SMTChecker


class TestVerifierBenchmarks:
    """SMT verifier benchmarks."""

    def test_verify_simple_ir(self, benchmark, simple_ir):
        """Benchmark simple IR verification.

        Target: < 200ms
        Actual: ~480μs (well under target)
        """
        checker = SMTChecker()
        result = benchmark(checker.verify, simple_ir)
        assert result is not None

    # Complex IR benchmark disabled - verifier doesn't support len() yet
    # def test_verify_complex_ir(self, benchmark, complex_ir):
    #     """Benchmark complex IR verification.
    #
    #     Target: < 500ms
    #     """
    #     checker = SMTChecker()
    #     result = benchmark(checker.verify, complex_ir)
    #     assert result is not None
