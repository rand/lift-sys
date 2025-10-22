"""Robustness testing suite for lift-sys.

This test suite validates the robustness of IR generation and code generation
to semantic-preserving transformations, following the TokDrift methodology.

Test Categories:
- Paraphrase robustness: NLP prompt variations
- IR variant robustness: Naming/ordering/assertion changes
- Code generation robustness: IR-to-code consistency
- End-to-end robustness: Full pipeline validation
"""
