"""Unit tests for the forward-mode controller runtime."""

from __future__ import annotations

from collections.abc import Iterable

from lift_sys.forward_mode.controller_runtime import ControllerHooks, ControllerRuntime
from lift_sys.forward_mode.synthesizer import CodeSynthesizer, Constraint, SynthesizerConfig


def test_runtime_compiles_schema_and_grammar(simple_ir) -> None:
    """Runtime should compile schema and grammar metadata on initialisation."""

    config = SynthesizerConfig(
        model_endpoint="http://localhost/model",
        provider_type="vllm",
        schema_uri="memory://schema.json",
        grammar_source="start -> unit",
    )
    runtime = ControllerRuntime(config)

    payload = runtime.build_payload(simple_ir, [])

    assert payload["schema"] == {"uri": "memory://schema.json", "compiled": True}
    assert payload["grammar"] == {"source": "start -> unit", "compiled": True}
    assert payload["constraint_intersections"] == {}


def test_runtime_executes_controller_hooks(simple_ir) -> None:
    """All controller hooks must execute in sequence when streaming."""

    events: list[str] = []

    def loader(context):
        def init(ctx):
            events.append("init")

        def pre(ctx, constraints: Iterable[Constraint]) -> None:
            events.append(f"pre:{len(list(constraints))}")

        def mid(ctx, token: str) -> str:
            events.append(f"mid:{token}")
            return token.upper()

        def post(ctx, result: dict) -> dict:
            events.append("post")
            result = dict(result)
            result["finalised"] = True
            return result

        return ControllerHooks(init=init, pre=pre, mid=mid, post=post)

    config = SynthesizerConfig(model_endpoint="http://localhost/model", provider_type="sglang")
    runtime = ControllerRuntime(config, loader=loader)

    constraints = [Constraint(name="assertion", value="x > 0")]
    payload = runtime.build_payload(simple_ir, constraints)
    tokens = list(runtime.stream(payload, constraints))

    assert events[0] == "init"
    assert [token for token in tokens if token.isupper()]
    assert runtime.context.state["post_result"]["finalised"] is True
    assert any(record["event"] == "token" for record in runtime.telemetry)


def test_code_synthesizer_generate_streams_tokens(simple_ir) -> None:
    """CodeSynthesizer.generate should produce a stream and telemetry payload."""

    def loader(context):
        def pre(ctx, constraints: Iterable[Constraint]) -> None:
            ctx.record("pre_hook", count=len(list(constraints)))

        def mid(ctx, token: str) -> str:
            return token[::-1]

        def post(ctx, result: dict) -> dict:
            result = dict(result)
            result["completed"] = True
            return result

        return ControllerHooks(pre=pre, mid=mid, post=post)

    def runtime_factory(config: SynthesizerConfig) -> ControllerRuntime:
        return ControllerRuntime(config, loader=loader)

    config = SynthesizerConfig(
        model_endpoint="http://localhost/model",
        provider_type="vllm",
        schema_uri="memory://schema.json",
        grammar_source="start -> unit",
    )
    synthesizer = CodeSynthesizer(config, runtime_factory=runtime_factory)

    result = synthesizer.generate(simple_ir)

    assert result["provider"] == "vllm"
    assert result["schema"]["compiled"] is True
    assert result["constraint_intersections"]["assertion"] == ["a >= 0", "b >= 0"]
    assert all(isinstance(token, str) for token in result["stream"])
    assert any(entry["event"] == "pre_hook" for entry in result["telemetry"])
