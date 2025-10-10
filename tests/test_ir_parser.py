from lift_sys.ir.parser import IRParser

SAMPLE = """
ir sample {
  intent: ensure positive input
  signature: sample(x: int) -> int
  assert:
    - x > 0
}
"""


def test_parser_round_trip():
    parser = IRParser()
    ir = parser.parse(SAMPLE)
    assert ir.signature.name == "sample"
    assert ir.assertions[0].predicate == "x > 0"
    text = parser.dumps(ir)
    assert "signature" in text
