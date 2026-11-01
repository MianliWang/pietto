"""Phase71 S17 IPC payload admission and the nested IPC oracle; checkers need no Arrow.

Before any body is decoded, ``project_result_ipc`` refuses a payload that
carries a compressed record batch or a dictionary batch (``IPC_ENCODING``),
for every binding. The C6 source binding drives nested ``encode_ipc`` and
``open_ipc``; the tools catalog supplies its malformed payload corpus.
"""

import hashlib
import importlib
import json
import struct
from unittest.mock import patch

GROUPS = ("nested_ipc_admission", "nested_ipc_oracle")
# Exact-path load order: each module imports the one before it by name.
ORACLES = (
    "_pietto_target_conformance_resources",
    "_pietto_target_conformance_observation",
    "_pietto_execution_nested_oracle",
    "_pietto_plan_nested",
    "_pietto_sql_nested_collect",
    "_pietto_results_nested_ipc_oracle",
)
COMPRESSED = ("compression_zstd", "compression_lz4")
# Arrow 0.17's V4 form: the codec only under this Message.custom_metadata key.
KEY = "ARROW:experimental_compression"
EXPERIMENTAL = dict(experimental_zstd="zstd", experimental_lz4="lz4")
# A dictionary-typed child is written as a dictionary batch, which admission
# refuses before the reader's schema check would.
REFUSED = (*COMPRESSED, "child_dictionary")
CONTROLS = (
    "single_batch",
    "legacy_format",
    "metadata_v4",
    "missing_eos",
    "zero_length_offsets_buffer",
    "truncate_mid_body",
)
TARGETS = ("postgres", "mysql")
# The default reader batch budget, which ``open_ipc`` hands the walk.
BUDGET = 1024
ACCEPTED = ("canonical", "metadata_v4", "legacy_format", "missing_eos")


def oracle(p):
    for name in ORACLES:
        p._helper(name)
    return p._helper(ORACLES[-1])


def v4_payload(pa, ipc_oracle, schema, batches, codec, metadata):
    """V4 batches with Message.custom_metadata; a compressed payload's
    ``RecordBatch.compression`` vtable entry is zeroed."""
    sink = pa.BufferOutputStream()
    options = pa.ipc.IpcWriteOptions(
        metadata_version=pa.ipc.MetadataVersion.V4, allow_64bit=False, compression=codec
    )
    with pa.ipc.new_stream(sink, schema, options=options) as writer:
        for batch in batches:
            writer.write_batch(batch, custom_metadata=metadata)
    data = bytearray(sink.getvalue().to_pybytes())

    def read(form, at):
        return struct.unpack_from(form, data, at)[0]

    def entry(table, slot):
        return table - read("<i", table) + 4 + 2 * slot

    for start in ipc_oracle.boundaries(pa, bytes(data))[:-1] if codec else ():
        message = start + 8 + read("<I", start + 8)
        header = message + read("<H", entry(message, 2))
        struct.pack_into("<H", data, entry(header + read("<I", header), 3), 0)
    return bytes(data)


def admission(pa, payload):
    from pietto._project import project_result_ipc as ipc
    from pietto._project.project_result_contract import ResultError

    try:
        ipc._admit_payload(pa, memoryview(payload), BUDGET)
    except ResultError as exc:
        return exc.category
    return "ADMIT"


def undecoded(pa, payload):
    """The refusal category and every decoder call made while reaching it."""
    from pietto._project import project_result_ipc as ipc

    calls = []

    def decoder(name):
        def call(*args, **kwargs):
            calls.append(name)
            raise AssertionError("decoder invoked")

        return call

    with (
        patch.object(pa.ipc, "open_stream", decoder("open_stream")),
        patch.object(pa.ipc, "read_record_batch", decoder("read_record_batch")),
    ):
        category = outcome(lambda: ipc._open_reader(memoryview(payload), BUDGET))
    return [category, calls]


def outcome(action):
    from pietto._project.project_result_contract import ResultError

    try:
        action()
    except ResultError as exc:
        return exc.category
    return "ACCEPTED"


def flat(p, pa, ipc_oracle, root, target):
    """Re-encoded flat finite frames through the real ``open_ipc``."""
    from pietto._project import project_arrow_result as a
    from pietto._project import project_result_ipc as ipc
    from pietto._project.project_result_contract_portable import (
        export_result_contract,
    )

    *_, producer, _ = p.finite_fixture(root / ("flat-" + target), target)
    binding = a.bind_arrow(producer, **p.finite_policy(producer))
    digest = hashlib.sha256(
        export_result_contract(
            producer.contract, producer.contract.authority
        ).canonical_bytes
    ).digest()
    batch = p.native_finite()
    text = next(i for i, f in enumerate(batch.schema) if pa.types.is_string(f.type))
    encoded = batch.column(text).dictionary_encode()
    field = batch.schema.field(text)
    dictionary = batch.set_column(text, field.with_type(encoded.type), encoded)

    def frame(source=batch, strip=False, **options):
        parts = [source.slice(0, 2), source.slice(2, 2)]
        payload = ipc_oracle._write(pa, source.schema, parts, **options)
        payload = ipc_oracle.strip_eos(payload) if strip else payload
        return p.ipc_envelope(payload, 4, 2, digest)

    def v4_frame(codec, metadata):
        parts = [batch.slice(0, 2), batch.slice(2, 2)]
        payload = v4_payload(pa, ipc_oracle, batch.schema, parts, codec, metadata)
        return p.ipc_envelope(payload, 4, 2, digest)

    def reject(data):
        try:
            ipc.open_ipc(binding, data, expected_rows=4).close()
        except Exception as error:
            return p.ipc_error_tags(error)
        return ["ACCEPTED"]

    frames = dict(
        canonical=frame(),
        metadata_v4=frame(version=pa.ipc.MetadataVersion.V4),
        metadata_v4_custom=v4_frame(None, {"codec": "zstd"}),
        legacy_format=frame(legacy=True),
        missing_eos=frame(strip=True),
        zstd=frame(compression="zstd"),
        lz4=frame(compression="lz4"),
        dictionary=frame(dictionary),
        **{name: v4_frame(codec, {KEY: codec}) for name, codec in EXPERIMENTAL.items()},
    )
    observed = dict(
        accepted={
            name: p.ipc_decode_observation(binding, frames[name], 4)
            for name in ACCEPTED
        },
        refused={
            name: reject(frames[name])
            for name in ("zstd", "lz4", "dictionary", *EXPERIMENTAL)
        },
        # Admission passes V4 custom_metadata without the key; Arrow itself then
        # refuses the batch (only LZ4_FRAME or ZSTD may be named there).
        v4_custom=p.ipc_decode_observation(binding, frames["metadata_v4_custom"], 4),
    )
    # Without the admission check the compressed frame decodes (inflating the
    # body), the dictionary frame reaches the reader's schema check, and the
    # experimental key alone makes Arrow inflate the body to canonical values.
    with patch.object(ipc, "_admit_payload", lambda pa, payload, budget: None):
        observed["unchecked"] = {
            name: reject(frames[name]) for name in ("zstd", "dictionary")
        }
        observed["inflated"] = {
            name: p.ipc_decode_observation(binding, frames[name], 4)
            for name in EXPERIMENTAL
        }
    return observed


def source_binding(p, pa, ipc_oracle, root):
    """The real C6 PostgreSQL output, bound through the rows-reader owner."""
    from pietto._project import project_arrow_result as arrow
    from pietto._project.project_execution_reader import bind_postgres_output
    from pietto._project.project_result_output import prepare_output

    collecting = p._helper("_pietto_sql_nested_collect")
    item = ipc_oracle.literal.program(ipc_oracle.PROGRAM)
    outcome = collecting.wired_outcome(
        root / "source", dict(item.files), collecting.oracle_contract()
    )
    assert outcome.artifact is not None
    output = prepare_output(outcome.artifact)
    producer = bind_postgres_output(output, p._nested().metadata(output))
    binding = arrow.bind_arrow(producer)
    assert binding.schema.equals(
        ipc_oracle.canonical_schema(pa, ipc_oracle.literal.DEFAULT_LEAVES),
        check_metadata=True,
    )
    return binding


def source_roundtrips(p, pa, ipc_oracle, root, binding):
    """Opened S17-B paths for the currently admitted default-leaf binding."""
    from pietto._project import project_result_ipc as ipc

    rows = ipc_oracle.canonical_rows(ipc_oracle.literal.DEFAULT_LEAVES)
    batch = pa.RecordBatch.from_pylist(rows, schema=binding.schema)

    def roundtrip(batches, expected):
        frame = ipc.encode_ipc(
            binding,
            pa.RecordBatchReader.from_batches(binding.schema, batches),
            expected_rows=len(expected),
        )
        stream = ipc.open_ipc(binding, frame, expected_rows=len(expected))
        found = pa.RecordBatchReader.from_stream(stream).read_all().to_pylist()
        stream.close()
        completion = ipc.verify_ipc_completion(stream)
        return [found == expected, completion.rows, completion.batches, stream.state]

    compiled = p._helper("_pietto_sql_nested_collect")
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_result_contract import build_result_contract

    item = ipc_oracle.literal.program(ipc_oracle.PROGRAM)
    outcome = compiled.wired_outcome(
        root / "compiled", dict(item.files), compiled.oracle_contract()
    )
    assert outcome.artifact is not None
    compiled_contract = build_result_contract(
        emit_compiled(build_compiled(outcome.artifact).root, ()).request.verification
    )
    return dict(
        single=roundtrip((batch,), rows),
        rebatch=roundtrip((batch.slice(0, 2), batch.slice(2, 0), batch.slice(2)), rows),
        empty=roundtrip((batch.slice(0, 0),), []),
        offset=roundtrip((batch.slice(1),), rows[1:]),
        digests=[
            len(ipc.contract_digest(binding.producer.contract)),
            len(ipc.contract_digest(compiled_contract)),
            ipc.contract_digest(binding.producer.contract)
            != ipc.contract_digest(compiled_contract),
        ],
    )


def source_catalog(p, pa, ipc_oracle, binding):
    """Every default-leaf, non-null catalog category through actual open_ipc."""
    from pietto._project import project_result_ipc as ipc

    digest = ipc.contract_digest(binding.producer.contract)

    def actual(case):
        if case.input == "batch":
            batch = case.build(pa, case.leaves)
            frame = ipc.encode_ipc(
                binding,
                pa.RecordBatchReader.from_batches(binding.schema, [batch]),
                expected_rows=case.rows,
            )
        else:
            payload = case.build(pa, case.leaves)
            contract = b"\xff" * 32 if case.framing == "foreign" else digest
            frame = p.ipc_envelope(payload, case.rows, case.batches, contract)
            if case.framing == "unreframed":
                frame = frame[: -case.frame_cut]
        stream = None
        try:
            stream = ipc.open_ipc(binding, frame, expected_rows=case.rows)
            rows = pa.RecordBatchReader.from_stream(stream).read_all().to_pylist()
            stream.close()
            completion = ipc.verify_ipc_completion(stream)
            return (
                case.expect == "ACCEPT"
                and rows == list(case.values or ())
                and (completion.rows, completion.batches) == (case.rows, case.batches)
            )
        except BaseException as error:
            primary = None if stream is None else stream.primary_error
            tags = p.ipc_error_tags(primary if primary is not None else error)
            if stream is not None:
                stream.close()
            allowed = {
                "REFUSE_FRAME": {"IPC_FRAME", "LIMIT"},
                "REFUSE_CONTRACT": {"IPC_CONTRACT"},
                "REFUSE_ENCODING": {"IPC_ENCODING"},
                "REFUSE_READ": {"IPC_READ", "READER_SOURCE"},
                "REFUSE_SCHEMA": {"ARROW_SCHEMA", "IPC_ENCODING"},
                "REFUSE_BATCH": {"ARROW_BATCH", "NULL"},
                "REFUSE_EXTENT": {"READER_EXTENT", "IPC_COMPLETION"},
                "REFUSE_LIMIT": {"LIMIT"},
            }
            return case.expect != "ACCEPT" and bool(set(tags) & allowed[case.expect])

    return {
        case.name: actual(case)
        for case in ipc_oracle.catalog()
        if case.binding == "nested"
    }


def admitted(p, root):
    from pietto._project import project_result_ipc as ipc

    pa = importlib.import_module("pyarrow")
    ipc_oracle = oracle(p)
    payloads = {
        case.name: case.build(pa, case.leaves)
        for case in ipc_oracle.catalog()
        if case.input == "payload"
    }
    values = pa.array(["x", "y"]).dictionary_encode()
    dictionary = ipc_oracle._write(
        pa, pa.schema([pa.field("d", values.type)]), [pa.record_batch([values], ["d"])]
    )
    leaves = ipc_oracle.literal.DEFAULT_LEAVES
    nested = [ipc_oracle._canonical_batch(pa, leaves)]
    schema = ipc_oracle.canonical_schema(pa, leaves)
    hidden = {
        name: v4_payload(pa, ipc_oracle, schema, nested, codec, {KEY: codec})
        for name, codec in EXPERIMENTAL.items()
    }
    binding = source_binding(p, pa, ipc_oracle, root)
    return dict(
        catalog={name: admission(pa, data) for name, data in payloads.items()},
        extra=dict(
            dictionary=admission(pa, dictionary),
            empty=[
                admission(pa, b""),
                outcome(lambda: ipc._open_reader(memoryview(b""), BUDGET)),
            ],
            **{name: admission(pa, data) for name, data in hidden.items()},
        ),
        undecoded={
            **{name: undecoded(pa, payloads[name]) for name in COMPRESSED},
            **{name: undecoded(pa, data) for name, data in hidden.items()},
        },
        flat={target: flat(p, pa, ipc_oracle, root, target) for target in TARGETS},
        source=source_roundtrips(p, pa, ipc_oracle, root, binding),
        source_catalog=source_catalog(p, pa, ipc_oracle, binding),
    )


def self_checked(p, root):
    """The tools oracle's own pinned-pyarrow self-check, recorded per case."""
    report = root / "nested-ipc-oracle.json"
    returncode = oracle(p).self_check(report)
    document = json.loads(report.read_text())
    return dict(
        returncode=returncode,
        ok=document["ok"],
        pyarrow=document["pyarrow"],
        corpus_within_limit=document["corpus_within_limit"],
        entries=[
            [len(e["leaves"]), e["name"], e.get("expect"), e.get("errors")]
            for e in document["entries"]
        ],
    )


def run(p, root, cases):
    root.mkdir(parents=True, exist_ok=True)
    result = {GROUPS[0]: admitted(p, root), GROUPS[1]: self_checked(p, root)}
    # Round-trip through JSON first, as the saved report is checked.
    verify({**cases, **json.loads(json.dumps(result))}, p)
    return result


def verify(cases, p):
    """Hand-written verdicts; the Arrow-free oracle catalog is the denominator."""
    try:
        ipc_oracle = oracle(p)
        names = [c.name for c in ipc_oracle.catalog() if c.input == "payload"]
        decoded = p.ipc_decoded_expected([2, 2])
        expected = {
            GROUPS[0]: dict(
                catalog={n: "IPC_ENCODING" if n in REFUSED else "ADMIT" for n in names},
                extra=dict(
                    dictionary="IPC_ENCODING",
                    empty=["ADMIT", "IPC_READ"],
                    **{name: "IPC_ENCODING" for name in EXPERIMENTAL},
                ),
                undecoded={
                    name: ["IPC_ENCODING", []] for name in (*COMPRESSED, *EXPERIMENTAL)
                },
                flat={
                    target: dict(
                        accepted={name: decoded for name in ACCEPTED},
                        refused={
                            name: ["IPC_ENCODING"]
                            for name in ("zstd", "lz4", "dictionary", *EXPERIMENTAL)
                        },
                        unchecked=dict(zstd=["ACCEPTED"], dictionary=["ARROW_SCHEMA"]),
                        v4_custom=p.ipc_decoded_expected(
                            [],
                            errors=["READER_SOURCE", "ArrowInvalid"],
                            complete=False,
                            closed="FAILED",
                        ),
                        inflated={name: decoded for name in EXPERIMENTAL},
                    )
                    for target in TARGETS
                },
                source=dict(
                    single=[True, 6, 1, "CLOSED"],
                    rebatch=[True, 6, 3, "CLOSED"],
                    empty=[True, 0, 1, "CLOSED"],
                    offset=[True, 5, 1, "CLOSED"],
                    digests=[32, 32, True],
                ),
                source_catalog={
                    case.name: True
                    for case in ipc_oracle.catalog()
                    if case.binding == "nested"
                },
            ),
            GROUPS[1]: dict(
                returncode=0,
                ok=True,
                pyarrow=p.PIN,
                corpus_within_limit=True,
                entries=[
                    [len(leaves), case.name, case.expect, []]
                    for leaves in (
                        ipc_oracle.literal.DEFAULT_LEAVES,
                        ipc_oracle.literal.LEAVES,
                    )
                    for case in ipc_oracle.catalog(leaves)
                ],
            ),
        }
        if not set(REFUSED + CONTROLS) <= set(names) or any(
            not p._exact(cases[name], expected[name]) for name in GROUPS
        ):
            raise ValueError("nested IPC evidence")
    except (KeyError, TypeError) as exc:
        raise ValueError("nested IPC evidence shape") from exc


def damage():
    return (
        lambda v: v["cases"][GROUPS[0]]["catalog"].update(compression_zstd="ADMIT"),
        lambda v: v["cases"][GROUPS[0]]["catalog"].update(legacy_format="IPC_ENCODING"),
        lambda v: v["cases"][GROUPS[0]]["extra"].update(experimental_lz4="ADMIT"),
        lambda v: v["cases"][GROUPS[0]]["flat"]["postgres"]["refused"].update(
            experimental_zstd=["ACCEPTED"]
        ),
        lambda v: v["cases"][GROUPS[0]]["undecoded"]["compression_lz4"][1].append(
            "open_stream"
        ),
        lambda v: v["cases"][GROUPS[0]]["flat"]["mysql"]["refused"].update(
            dictionary=["ARROW_SCHEMA"]
        ),
        lambda v: v["cases"][GROUPS[0]]["source"]["offset"].__setitem__(0, False),
        lambda v: v["cases"][GROUPS[1]]["entries"][0][3].append("injected"),
        lambda v: v["cases"][GROUPS[1]]["entries"].pop(),
    )
