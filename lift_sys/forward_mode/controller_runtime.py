"""Runtime orchestration for WebAssembly-based forward-mode controllers."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from ..ir.models import IntermediateRepresentation
    from .synthesizer import Constraint, SynthesizerConfig


class MidHook(Protocol):
    """Protocol for the streaming mid hook."""

    def __call__(self, context: ControllerContext, token: str) -> str: ...


class PreHook(Protocol):
    """Protocol for the pre-stream hook."""

    def __call__(self, context: ControllerContext, constraints: Iterable[Constraint]) -> None: ...


class PostHook(Protocol):
    """Protocol for the post-stream hook."""

    def __call__(
        self, context: ControllerContext, result: dict[str, object]
    ) -> dict[str, object]: ...


class InitHook(Protocol):
    """Protocol for the controller initialisation hook."""

    def __call__(self, context: ControllerContext) -> None: ...


@dataclass
class ControllerHooks:
    """Collection of lifecycle hooks exported by the controller."""

    init: InitHook | None = None
    pre: PreHook | None = None
    mid: MidHook | None = None
    post: PostHook | None = None


@dataclass
class ControllerContext:
    """Mutable context exposed to controller hooks."""

    config: SynthesizerConfig
    schema: dict[str, object]
    grammar: dict[str, object] | None
    telemetry: list[dict[str, object]] = field(default_factory=list)
    state: dict[str, object] = field(default_factory=dict)

    def record(self, event: str, **payload: object) -> None:
        self.telemetry.append({"event": event, **payload})


Loader = Callable[[ControllerContext], ControllerHooks]


class ControllerRuntime:
    """Orchestrates controller lifecycle, schema initialisation, and streaming."""

    def __init__(self, config: SynthesizerConfig, loader: Loader | None = None) -> None:
        self.config = config
        self.schema = self._compile_schema()
        self.grammar = self._compile_grammar()
        self.context = ControllerContext(config=config, schema=self.schema, grammar=self.grammar)
        self._loader = loader or self._default_loader
        self.hooks = self.load_controller()
        if self.hooks.init:
            self.hooks.init(self.context)
        self._base_state = deepcopy(self.context.state)
        self._base_telemetry = list(self.context.telemetry)

    @property
    def telemetry(self) -> list[dict[str, object]]:
        return list(self.context.telemetry)

    def load_controller(self) -> ControllerHooks:
        hooks = self._loader(self.context)
        if hooks.mid is None:
            hooks.mid = self._noop_mid
        if hooks.pre is None:
            hooks.pre = self._noop_pre
        if hooks.post is None:
            hooks.post = self._noop_post
        return hooks

    def build_payload(
        self,
        ir: IntermediateRepresentation,
        constraints: Iterable[Constraint],
    ) -> dict[str, object]:
        prompt = {
            "intent": ir.intent.summary,
            "signature": ir.signature.to_dict()
            if hasattr(ir.signature, "to_dict")
            else ir.signature.name,
            "constraints": [constraint.__dict__ for constraint in constraints],
        }
        constraint_intersections = self.apply_constraint_intersections(constraints)
        payload = {
            "endpoint": self.config.model_endpoint,
            "provider": self.config.provider_type,
            "temperature": self.config.temperature,
            "prompt": prompt,
            "schema": self.schema,
            "grammar": self.grammar,
            "constraint_intersections": constraint_intersections,
        }
        self.context.record("build_payload", intersections=constraint_intersections)
        return payload

    def stream(
        self,
        payload: dict[str, object],
        constraints: Iterable[Constraint],
    ) -> Iterator[str]:
        self._reset_runtime_state()
        constraint_list = list(constraints)
        if self.hooks.pre:
            self.hooks.pre(self.context, constraint_list)
        for token in self._provider_stream(payload):
            processed = self.hooks.mid(self.context, token) if self.hooks.mid else token
            self.context.state.setdefault("tokens", []).append(processed)
            self.context.record("token", value=processed)
            yield processed
        if self.hooks.post:
            summary = {"tokens": list(self.context.state.get("tokens", []))}
            result = self.hooks.post(self.context, summary)
            self.context.state["post_result"] = result
            self.context.record("post", result=result)

    def apply_constraint_intersections(
        self, constraints: Iterable[Constraint]
    ) -> dict[str, list[str]]:
        intersections: dict[str, list[str]] = {}
        for constraint in constraints:
            collection = intersections.setdefault(constraint.name, [])
            if constraint.value not in collection:
                collection.append(constraint.value)
        return intersections

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _compile_schema(self) -> dict[str, object]:
        if getattr(self.config, "schema_uri", None):
            return {"uri": self.config.schema_uri, "compiled": True}
        return {"uri": None, "compiled": False}

    def _compile_grammar(self) -> dict[str, object] | None:
        if getattr(self.config, "grammar_source", None):
            return {"source": self.config.grammar_source, "compiled": True}
        return None

    def _provider_stream(self, payload: dict[str, object]) -> Iterator[str]:
        intent = payload.get("prompt", {}).get("intent", "")
        provider = payload.get("provider", "vllm").lower()
        seed = f"{provider}:{intent}".strip(":")
        if not seed:
            return iter(())
        for token in seed.split():
            yield token

    def _reset_runtime_state(self) -> None:
        """Clear per-request runtime state while preserving controller setup."""
        self.context.state = deepcopy(self._base_state)
        self.context.telemetry = list(self._base_telemetry)
        self.context.state.pop("tokens", None)

    # ------------------------------------------------------------------
    # Default hook implementations
    # ------------------------------------------------------------------
    @staticmethod
    def _noop_mid(context: ControllerContext, token: str) -> str:  # pragma: no cover - defensive
        return token

    @staticmethod
    def _noop_pre(
        context: ControllerContext, constraints: Iterable[Constraint]
    ) -> None:  # pragma: no cover
        if hasattr(constraints, "__len__"):
            count = len(constraints)  # type: ignore[arg-type]
        else:
            constraints = list(constraints)
            count = len(constraints)
        context.record("pre", count=count)

    @staticmethod
    def _noop_post(
        context: ControllerContext, result: dict[str, object]
    ) -> dict[str, object]:  # pragma: no cover
        context.record("post_default", size=len(context.state.get("tokens", [])))
        return result

    def _default_loader(self, context: ControllerContext) -> ControllerHooks:
        def init(ctx: ControllerContext) -> None:
            ctx.record("init", schema=ctx.schema, grammar=ctx.grammar)

        def pre(ctx: ControllerContext, constraints: Iterable[Constraint]) -> None:
            count = len(list(constraints))
            ctx.record("pre", constraints=count)
            ctx.state["constraint_count"] = count

        def mid(ctx: ControllerContext, token: str) -> str:
            return token

        def post(ctx: ControllerContext, result: dict[str, object]) -> dict[str, object]:
            result = dict(result)
            result["token_count"] = len(ctx.state.get("tokens", []))
            return result

        return ControllerHooks(init=init, pre=pre, mid=mid, post=post)


__all__ = [
    "ControllerRuntime",
    "ControllerContext",
    "ControllerHooks",
]
