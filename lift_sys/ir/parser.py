"""Parser for the lift-sys Intermediate Representation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from lark import Lark, Transformer, v_args

from .models import (
    AssertClause,
    EffectClause,
    HoleKind,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
    TypedHole,
)

_GRAMMAR = r"""
?start: ir

ir: "ir" NAME "{" intent signature effects? assertions? "}"
intent: "intent" ":" text (hole_list)?
signature: "signature" ":" NAME parameter_block return_type? (hole_list)?
parameter_block: "(" [param ("," param)*] ")"
param: NAME ":" NAME
return_type: "->" NAME

?effects: "effects" ":" effect_item+
effect_item: "-" text (hole_list)?

?assertions: "assert" ":" assertion_item+
assertion_item: "-" text (hole_list)?

?hole_list: "{" hole ("," hole)* "}"
hole: "<?" NAME ":" NAME hole_meta? "?>"
hole_meta: ("=" STRING)? ("@" NAME)?

text: /[^\n\r{}]+/

NAME: /[A-Za-z_][A-Za-z0-9_.]*/
STRING: /\"(\\.|[^\"])*\"/

%import common.WS
%ignore WS
%ignore /\#[^\n]*/
"""


@dataclass
class ParserConfig:
    allow_typed_holes: bool = True


@v_args(inline=True)
class _IRTransformer(Transformer):
    def __init__(self, allow_typed_holes: bool = True) -> None:
        super().__init__()
        self.allow_typed_holes = allow_typed_holes

    def ir(self, name_token, intent, signature_data, *sections):  # type: ignore[override]
        effects = []
        assertions = []
        for section in sections:
            if not section:
                continue
            if isinstance(section, list):
                first = section[0]
                if isinstance(first, EffectClause):
                    effects = section
                elif isinstance(first, AssertClause):
                    assertions = section
            elif isinstance(section, EffectClause):
                effects.append(section)
            elif isinstance(section, AssertClause):
                assertions.append(section)
        signature = SigClause(
            name=signature_data["name"],
            parameters=signature_data["parameters"],
            returns=signature_data.get("returns"),
            holes=signature_data.get("holes", []),
        )
        return IntermediateRepresentation(intent=intent, signature=signature, effects=effects, assertions=assertions)

    def intent(self, summary, holes=None):  # type: ignore[override]
        summary_text = str(summary).strip()
        if holes is None:
            hole_items = []
        elif isinstance(holes, list):
            hole_items = holes
        else:
            hole_items = [holes]  # Single hole case
        return IntentClause(summary=summary_text, holes=hole_items)

    def signature(self, name, parameters, returns=None, holes=None):  # type: ignore[override]
        if holes is None:
            hole_items = []
        elif isinstance(holes, list):
            hole_items = holes
        else:
            hole_items = [holes]  # Single hole case
        return {
            "name": str(name),
            "parameters": parameters,
            "returns": str(returns) if returns else None,
            "holes": hole_items,
        }

    def parameter_block(self, *params):  # type: ignore[override]
        # Filter out None values (empty parameter list)
        return [p for p in params if p is not None]

    def param(self, *parts):  # type: ignore[override]
        name = str(parts[0])
        type_name = parts[-1]
        return Parameter(name=name, type_hint=str(type_name))

    def return_type(self, *parts):  # type: ignore[override]
        return str(parts[-1])

    def effects(self, *items):  # type: ignore[override]
        return list(items)

    def effect_item(self, description, holes=None):  # type: ignore[override]
        if holes is None:
            hole_items = []
        elif isinstance(holes, list):
            hole_items = holes
        else:
            hole_items = [holes]  # Single hole case
        return EffectClause(description=str(description).strip(), holes=hole_items)

    def assertions(self, *items):  # type: ignore[override]
        return list(items)

    def assertion_item(self, predicate, holes=None):  # type: ignore[override]
        if holes is None:
            hole_items = []
        elif isinstance(holes, list):
            hole_items = holes
        else:
            hole_items = [holes]  # Single hole case
        return AssertClause(predicate=str(predicate).strip(), holes=hole_items)

    def hole_list(self, *_parts):  # type: ignore[override]
        return [part for part in _parts if isinstance(part, TypedHole)]

    def hole(self, name, type_name, meta=None):  # type: ignore[override]
        description = ""
        constraints = {}
        kind = HoleKind.INTENT
        if meta:
            if "description" in meta:
                description = meta["description"]
            if "kind" in meta:
                kind = HoleKind(meta["kind"])
        if not self.allow_typed_holes:
            raise ValueError("Typed holes are disabled for this parser instance")
        return TypedHole(identifier=str(name), type_hint=str(type_name), description=description, kind=kind, constraints=constraints)

    def hole_meta(self, *_parts):  # type: ignore[override]
        description = None
        kind = None
        for part in _parts:
            if hasattr(part, "type") and part.type == "STRING":
                description = str(part)[1:-1]
            elif hasattr(part, "type") and part.type == "NAME":
                kind = str(part)
        return {"description": description or "", "kind": kind or HoleKind.INTENT.value}

    def text(self, token):  # type: ignore[override]
        return str(token)


class IRParser:
    """High level wrapper around the Lark generated parser."""

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()
        self._parser = Lark(_GRAMMAR, start="ir", parser="lalr")

    def parse(self, source: str) -> IntermediateRepresentation:
        tree = self._parser.parse(source)
        transformer = _IRTransformer(allow_typed_holes=self.config.allow_typed_holes)
        return transformer.transform(tree)  # type: ignore[return-value]

    def parse_file(self, path: str | Path) -> IntermediateRepresentation:
        content = Path(path).read_text(encoding="utf8")
        return self.parse(content)

    def dumps(self, ir: IntermediateRepresentation) -> str:
        """Render an IR instance back to textual form."""

        lines = [f"ir {ir.signature.name} {{"]
        intent = ir.intent
        lines.append(f"  intent: {intent.summary}")
        if intent.holes:
            lines.append(self._format_holes(intent.holes, indent=4))
        sig = ir.signature
        params = ", ".join(f"{param.name}: {param.type_hint}" for param in sig.parameters)
        line = f"  signature: {sig.name}({params})"
        if sig.returns:
            line += f" -> {sig.returns}"
        lines.append(line)
        if sig.holes:
            lines.append(self._format_holes(sig.holes, indent=4))
        if ir.effects:
            lines.append("  effects:")
            for effect in ir.effects:
                lines.append(f"    - {effect.description}")
                if effect.holes:
                    lines.append(self._format_holes(effect.holes, indent=8))
        if ir.assertions:
            lines.append("  assert:")
            for assertion in ir.assertions:
                lines.append(f"    - {assertion.predicate}")
                if assertion.holes:
                    lines.append(self._format_holes(assertion.holes, indent=8))
        lines.append("}")
        return "\n".join(lines)

    def _format_holes(self, holes: Iterable[TypedHole], indent: int) -> str:
        def _format_meta(hole: TypedHole) -> str:
            parts: list[str] = []
            if hole.description:
                escaped = (
                    hole.description.replace("\\", "\\\\").replace("\"", "\\\"")
                )
                parts.append(f"=\"{escaped}\"")
            if hole.kind:
                parts.append(f"@{hole.kind.value}")
            return "".join(parts)

        entries = ", ".join(
            f"<?{hole.identifier}: {hole.type_hint}{_format_meta(hole)}?>" for hole in holes
        )
        return " " * indent + "{" + entries + "}"


__all__ = ["IRParser", "ParserConfig"]
