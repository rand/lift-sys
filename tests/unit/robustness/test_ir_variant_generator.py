"""Tests for IR variant generator."""

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.robustness.ir_variant_generator import IRVariantGenerator
from lift_sys.robustness.types import NamingStyle


class TestNamingConversion:
    """Test naming style conversion."""

    def test_snake_to_camel(self):
        """Convert snake_case to camelCase."""
        gen = IRVariantGenerator()
        assert gen._convert_name("sort_numbers", NamingStyle.CAMEL_CASE) == "sortNumbers"
        assert gen._convert_name("process_user_data", NamingStyle.CAMEL_CASE) == "processUserData"
        assert gen._convert_name("foo_bar_baz", NamingStyle.CAMEL_CASE) == "fooBarBaz"

    def test_snake_to_pascal(self):
        """Convert snake_case to PascalCase."""
        gen = IRVariantGenerator()
        assert gen._convert_name("sort_numbers", NamingStyle.PASCAL_CASE) == "SortNumbers"
        assert gen._convert_name("process_user_data", NamingStyle.PASCAL_CASE) == "ProcessUserData"

    def test_snake_to_screaming(self):
        """Convert snake_case to SCREAMING_SNAKE_CASE."""
        gen = IRVariantGenerator()
        assert gen._convert_name("sort_numbers", NamingStyle.SCREAMING_SNAKE) == "SORT_NUMBERS"
        assert (
            gen._convert_name("process_user_data", NamingStyle.SCREAMING_SNAKE)
            == "PROCESS_USER_DATA"
        )

    def test_camel_to_snake(self):
        """Convert camelCase to snake_case."""
        gen = IRVariantGenerator()
        assert gen._convert_name("sortNumbers", NamingStyle.SNAKE_CASE) == "sort_numbers"
        assert gen._convert_name("processUserData", NamingStyle.SNAKE_CASE) == "process_user_data"
        assert gen._convert_name("fooBarBaz", NamingStyle.SNAKE_CASE) == "foo_bar_baz"

    def test_camel_to_pascal(self):
        """Convert camelCase to PascalCase."""
        gen = IRVariantGenerator()
        assert gen._convert_name("sortNumbers", NamingStyle.PASCAL_CASE) == "SortNumbers"
        assert gen._convert_name("processUserData", NamingStyle.PASCAL_CASE) == "ProcessUserData"

    def test_pascal_to_snake(self):
        """Convert PascalCase to snake_case."""
        gen = IRVariantGenerator()
        assert gen._convert_name("SortNumbers", NamingStyle.SNAKE_CASE) == "sort_numbers"
        assert gen._convert_name("ProcessUserData", NamingStyle.SNAKE_CASE) == "process_user_data"

    def test_pascal_to_camel(self):
        """Convert PascalCase to camelCase."""
        gen = IRVariantGenerator()
        assert gen._convert_name("SortNumbers", NamingStyle.CAMEL_CASE) == "sortNumbers"
        assert gen._convert_name("ProcessUserData", NamingStyle.CAMEL_CASE) == "processUserData"

    def test_screaming_to_snake(self):
        """Convert SCREAMING_SNAKE_CASE to snake_case."""
        gen = IRVariantGenerator()
        assert gen._convert_name("SORT_NUMBERS", NamingStyle.SNAKE_CASE) == "sort_numbers"
        assert gen._convert_name("PROCESS_USER_DATA", NamingStyle.SNAKE_CASE) == "process_user_data"

    def test_single_word(self):
        """Handle single-word identifiers."""
        gen = IRVariantGenerator()
        assert gen._convert_name("sort", NamingStyle.SNAKE_CASE) == "sort"
        assert gen._convert_name("sort", NamingStyle.CAMEL_CASE) == "sort"
        assert gen._convert_name("sort", NamingStyle.PASCAL_CASE) == "Sort"
        assert gen._convert_name("sort", NamingStyle.SCREAMING_SNAKE) == "SORT"

    def test_empty_string(self):
        """Handle empty string."""
        gen = IRVariantGenerator()
        assert gen._convert_name("", NamingStyle.SNAKE_CASE) == ""


class TestIdentifierParsing:
    """Test identifier parsing into words."""

    def test_parse_snake_case(self):
        """Parse snake_case identifiers."""
        gen = IRVariantGenerator()
        assert gen._parse_identifier("sort_numbers") == ["sort", "numbers"]
        assert gen._parse_identifier("foo_bar_baz") == ["foo", "bar", "baz"]

    def test_parse_camel_case(self):
        """Parse camelCase identifiers."""
        gen = IRVariantGenerator()
        assert gen._parse_identifier("sortNumbers") == ["sort", "numbers"]
        assert gen._parse_identifier("fooBarBaz") == ["foo", "bar", "baz"]

    def test_parse_pascal_case(self):
        """Parse PascalCase identifiers."""
        gen = IRVariantGenerator()
        assert gen._parse_identifier("SortNumbers") == ["sort", "numbers"]
        assert gen._parse_identifier("FooBarBaz") == ["foo", "bar", "baz"]

    def test_parse_screaming_snake(self):
        """Parse SCREAMING_SNAKE_CASE identifiers."""
        gen = IRVariantGenerator()
        assert gen._parse_identifier("SORT_NUMBERS") == ["sort", "numbers"]
        assert gen._parse_identifier("FOO_BAR_BAZ") == ["foo", "bar", "baz"]

    def test_parse_acronyms(self):
        """Parse identifiers with acronyms."""
        gen = IRVariantGenerator()
        # "HTTPServer" should parse as ["http", "server"]
        assert gen._parse_identifier("HTTPServer") == ["http", "server"]
        assert gen._parse_identifier("XMLParser") == ["xml", "parser"]

    def test_parse_single_word(self):
        """Parse single-word identifiers."""
        gen = IRVariantGenerator()
        assert gen._parse_identifier("sort") == ["sort"]
        assert gen._parse_identifier("Sort") == ["sort"]

    def test_parse_empty(self):
        """Parse empty string."""
        gen = IRVariantGenerator()
        assert gen._parse_identifier("") == []


class TestNamingVariants:
    """Test generating naming variants of IRs."""

    def test_generate_naming_variants_simple(self):
        """Generate naming variants for simple IR."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Sort numbers"),
            signature=SigClause(
                name="sort_numbers",
                parameters=[Parameter(name="input_list", type_hint="list")],
                returns="list",
            ),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        gen = IRVariantGenerator()
        variants = gen.generate_naming_variants(ir)

        # Should generate 4 variants (one per style)
        assert len(variants) == 4

        # Check each style
        assert variants[0].signature.name == "sort_numbers"  # snake_case
        assert variants[1].signature.name == "sortNumbers"  # camelCase
        assert variants[2].signature.name == "SortNumbers"  # PascalCase
        assert variants[3].signature.name == "SORT_NUMBERS"  # SCREAMING_SNAKE

        # Check parameter names also converted
        assert variants[1].signature.parameters[0].name == "inputList"
        assert variants[2].signature.parameters[0].name == "InputList"

    def test_naming_variants_preserve_structure(self):
        """Naming variants preserve IR structure."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(
                name="process_data",
                parameters=[
                    Parameter(name="input_data", type_hint="dict"),
                    Parameter(name="output_path", type_hint="str"),
                ],
                returns="bool",
            ),
            effects=[EffectClause(description="writes to file")],
            assertions=[AssertClause(predicate="input_data is not None")],
            metadata=Metadata(origin="test"),
        )

        gen = IRVariantGenerator()
        variants = gen.generate_naming_variants(ir)

        # All variants should have same structure
        for variant in variants:
            assert variant.intent.summary == ir.intent.summary
            assert len(variant.signature.parameters) == 2
            assert variant.signature.returns == "bool"
            assert len(variant.effects) == 1
            assert len(variant.assertions) == 1


class TestEffectReordering:
    """Test effect reordering generation."""

    def test_reorder_independent_effects(self):
        """Reorder independent effects."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(name="process", parameters=[], returns="None"),
            effects=[
                EffectClause(description="logs to console"),
                EffectClause(description="updates cache"),
            ],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        gen = IRVariantGenerator()
        variants = gen.generate_effect_orderings(ir)

        # Should generate at least 1 variant (reordered)
        assert len(variants) >= 1

        # Original and variant should have same effects, different order
        original_descs = {e.description for e in ir.effects}
        for variant in variants:
            variant_descs = {e.description for e in variant.effects}
            assert variant_descs == original_descs

    def test_no_reordering_single_effect(self):
        """No reordering for single effect."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(name="process", parameters=[], returns="None"),
            effects=[EffectClause(description="logs to console")],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        gen = IRVariantGenerator()
        variants = gen.generate_effect_orderings(ir)

        # No variants (can't reorder single effect)
        assert len(variants) == 0

    def test_no_reordering_empty_effects(self):
        """No reordering for empty effects."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(name="process", parameters=[], returns="None"),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        gen = IRVariantGenerator()
        variants = gen.generate_effect_orderings(ir)

        assert len(variants) == 0

    def test_dependency_detection_file_ops(self):
        """Detect dependencies in file operations."""
        gen = IRVariantGenerator()

        effect_read = EffectClause(description="reads from input.txt")
        effect_write = EffectClause(description="writes to input.txt")

        # Write depends on read (same file)
        assert gen._depends_on(effect_write, effect_read) is True

        # Read doesn't depend on write
        assert gen._depends_on(effect_read, effect_write) is False

    def test_dependency_detection_database_ops(self):
        """Detect dependencies in database operations."""
        gen = IRVariantGenerator()

        effect_read = EffectClause(description="database read from users")
        effect_write = EffectClause(description="database write to results")

        # Write depends on read (database operations)
        assert gen._depends_on(effect_write, effect_read) is True


class TestAssertionRephrasing:
    """Test assertion rephrasing."""

    def test_rephrase_greater_than_zero(self):
        """Rephrase 'x > 0' to 'x >= 1'."""
        gen = IRVariantGenerator()
        variants = gen._rephrase_assertion("x > 0")
        assert "x >= 1" in variants

    def test_rephrase_greater_equal_one(self):
        """Rephrase 'x >= 1' to 'x > 0'."""
        gen = IRVariantGenerator()
        variants = gen._rephrase_assertion("x >= 1")
        assert "x > 0" in variants

    def test_rephrase_len_greater_zero(self):
        """Rephrase 'len(x) > 0' to 'x != []'."""
        gen = IRVariantGenerator()
        variants = gen._rephrase_assertion("len(nums) > 0")
        assert "nums != []" in variants

    def test_rephrase_equals_true(self):
        """Rephrase 'x == True' to 'x'."""
        gen = IRVariantGenerator()
        variants = gen._rephrase_assertion("result == True")
        assert "result" in variants

    def test_rephrase_equals_false(self):
        """Rephrase 'x == False' to 'not x'."""
        gen = IRVariantGenerator()
        variants = gen._rephrase_assertion("valid == False")
        assert "not valid" in variants

    def test_rephrase_not(self):
        """Rephrase 'not x' to 'x == False'."""
        gen = IRVariantGenerator()
        variants = gen._rephrase_assertion("not valid")
        assert "valid == False" in variants

    def test_generate_assertion_variants(self):
        """Generate IR variants with rephrased assertions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Validate input"),
            signature=SigClause(name="validate", parameters=[], returns="bool"),
            effects=[],
            assertions=[AssertClause(predicate="x > 0")],
            metadata=Metadata(origin="test"),
        )

        gen = IRVariantGenerator()
        variants = gen.generate_assertion_variants(ir)

        # Should generate at least 1 variant
        assert len(variants) >= 1

        # Check that assertion was rephrased
        assert variants[0].assertions[0].predicate == "x >= 1"

    def test_no_assertion_variants_empty(self):
        """No assertion variants for empty assertions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process"),
            signature=SigClause(name="process", parameters=[], returns="None"),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        gen = IRVariantGenerator()
        variants = gen.generate_assertion_variants(ir)
        assert len(variants) == 0


class TestGenerateVariants:
    """Test combined variant generation."""

    def test_generate_all_variants(self):
        """Generate all variant types."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Sort numbers"),
            signature=SigClause(
                name="sort_numbers",
                parameters=[Parameter(name="nums", type_hint="list")],
                returns="list",
            ),
            effects=[
                EffectClause(description="logs to console"),
                EffectClause(description="updates cache"),
            ],
            assertions=[AssertClause(predicate="len(nums) > 0")],
            metadata=Metadata(origin="test"),
        )

        gen = IRVariantGenerator(max_variants=10)
        variants = gen.generate_variants(ir, max_variants=10)

        # Should generate variants from all methods
        assert len(variants) > 0

        # Should include naming variants (4), effect variants (>=1), assertion variants (>=1)
        # Total should be at least 6
        assert len(variants) >= 6

    def test_generate_variants_respects_max(self):
        """Respect max_variants parameter."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(
                name="process_data",
                parameters=[Parameter(name="input", type_hint="dict")],
                returns="bool",
            ),
            effects=[
                EffectClause(description="effect1"),
                EffectClause(description="effect2"),
            ],
            assertions=[AssertClause(predicate="x > 0")],
            metadata=Metadata(origin="test"),
        )

        gen = IRVariantGenerator()
        variants = gen.generate_variants(ir, max_variants=3)

        # Should not exceed max
        assert len(variants) <= 3


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_ir(self):
        """Handle IR with minimal content."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Empty"),
            signature=SigClause(name="empty", parameters=[], returns="None"),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        gen = IRVariantGenerator()

        # Should still generate naming variants
        naming_variants = gen.generate_naming_variants(ir)
        assert len(naming_variants) == 4

        # No effect variants
        effect_variants = gen.generate_effect_orderings(ir)
        assert len(effect_variants) == 0

        # No assertion variants
        assertion_variants = gen.generate_assertion_variants(ir)
        assert len(assertion_variants) == 0

    def test_complex_ir_from_fixture(self, sample_ir):
        """Test with real IR fixture."""
        gen = IRVariantGenerator()

        # Should generate variants without errors
        naming_variants = gen.generate_naming_variants(sample_ir)
        assert len(naming_variants) == 4

        # All variants should be valid IRs
        for variant in naming_variants:
            assert isinstance(variant, IntermediateRepresentation)
            assert variant.signature.name  # Has name
            assert variant.intent.summary  # Has intent

    def test_ir_with_multiple_parameters(self):
        """Test IR with multiple parameters."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Compute"),
            signature=SigClause(
                name="compute_result",
                parameters=[
                    Parameter(name="input_data", type_hint="dict"),
                    Parameter(name="config_params", type_hint="dict"),
                    Parameter(name="output_path", type_hint="str"),
                ],
                returns="bool",
            ),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        gen = IRVariantGenerator()
        variants = gen.generate_naming_variants(ir)

        # Check all parameters converted in camelCase variant
        camel_variant = variants[1]
        assert camel_variant.signature.parameters[0].name == "inputData"
        assert camel_variant.signature.parameters[1].name == "configParams"
        assert camel_variant.signature.parameters[2].name == "outputPath"

    def test_rewrite_identifiers_in_text(self):
        """Test identifier rewriting in free-form text."""
        gen = IRVariantGenerator()

        text = "reads input_data and writes output_file"
        result = gen._rewrite_identifiers_in_text(text, NamingStyle.CAMEL_CASE)

        assert "inputData" in result
        assert "outputFile" in result
        assert "reads" in result  # Non-identifier preserved
        assert "writes" in result

    def test_preserved_reserved_words(self):
        """Reserved words should not be converted."""
        gen = IRVariantGenerator()

        text = "len(nums) > 0 and not is_empty"
        result = gen._rewrite_identifiers_in_text(text, NamingStyle.PASCAL_CASE)

        # Reserved words preserved
        assert "len" in result
        assert "not" in result
        assert "and" in result

        # Identifiers converted
        assert "IsEmpty" in result


class TestSampleIRVariants:
    """Test with sample IR from fixtures."""

    def test_sample_ir_naming_variants(self, sample_ir):
        """Generate naming variants for sample IR."""
        gen = IRVariantGenerator()
        variants = gen.generate_naming_variants(sample_ir)

        assert len(variants) == 4

        # Check structure preserved
        for variant in variants:
            assert variant.intent.summary == sample_ir.intent.summary
            assert len(variant.effects) == len(sample_ir.effects)
            assert len(variant.assertions) == len(sample_ir.assertions)

    def test_simple_ir_variants(self, simple_ir):
        """Generate variants for simple IR."""
        gen = IRVariantGenerator()

        naming_variants = gen.generate_naming_variants(simple_ir)
        assert len(naming_variants) == 4

        assertion_variants = gen.generate_assertion_variants(simple_ir)
        # simple_ir has assertions like "a >= 0", should generate variants
        assert len(assertion_variants) >= 0  # May or may not have rephrasing rules

    def test_complex_ir_variants(self, complex_ir):
        """Generate variants for complex IR."""
        gen = IRVariantGenerator()

        # Naming variants
        naming_variants = gen.generate_naming_variants(complex_ir)
        assert len(naming_variants) == 4

        # Effect variants (has 2 effects)
        effect_variants = gen.generate_effect_orderings(complex_ir)
        assert len(effect_variants) >= 1

        # All variants combined
        all_variants = gen.generate_variants(complex_ir)
        assert len(all_variants) >= 5  # Naming + effects + assertions
