from pietto.ast_nodes import Script
from pietto.errors import Severity
from pietto.ir import ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze


MATRIX_SHAPE = (
    "enum Status:\n"
    "    active\n"
    "    paused\n"
    "shape Order:\n"
    "    status: Text\n"
    "    region: Text\n"
    "    active: Bool\n"
    "    amount: Int\n"
    "    tax: Int\n"
    "    score: Float\n"
    "    weight: Float\n"
    "    price: Decimal\n"
    "    discount: Decimal\n"
    "    order_date: Date | None\n"
    "    created_at: Timestamp\n"
    "    raw: Bytes\n"
    "    payload: Json\n"
    "    customer_id: UUID\n"
    "    anything: Any | None\n"
    "    enum_status: Status\n"
)


def _compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    parsed = parse_source(source, path="aggregate-results.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    script = parsed.ast
    semantic = analyze(script)
    assert [d.code for d in semantic.diagnostics if d.severity is Severity.ERROR] == []
    script = semantic.script or script
    ir_result = build_ir(script, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return script, semantic, ir_result.ir
