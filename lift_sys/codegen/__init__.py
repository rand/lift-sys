"""Code generation from Intermediate Representations."""

from .assertion_injector import (
    AssertionInjector,
    AssertionMode,
    DefaultAssertionInjector,
    InjectedAssertion,
)
from .generator import CodeGenerator, CodeGeneratorConfig
from .models import GeneratedCode, ValidationResult
from .roundtrip import (
    DiffResult,
    IRDiffer,
    IRDifference,
    RoundTripResult,
    RoundTripValidator,
    SimpleIRExtractor,
)

__all__ = [
    "AssertionInjector",
    "AssertionMode",
    "CodeGenerator",
    "CodeGeneratorConfig",
    "DefaultAssertionInjector",
    "DiffResult",
    "GeneratedCode",
    "InjectedAssertion",
    "IRDiffer",
    "IRDifference",
    "RoundTripResult",
    "RoundTripValidator",
    "SimpleIRExtractor",
    "ValidationResult",
]
