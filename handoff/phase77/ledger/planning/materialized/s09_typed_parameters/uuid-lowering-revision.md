# UUID correction: implementation freedom, not an owner decision

## Established contract

The current result/public-pure contract already names MySQL UUID storage as
`my_uuid_bytes` with `{"kind": "uuid", "encoding": "standard_bytes"}`.
The row law explicitly equates PostgreSQL UUID ordering with unsigned
big-endian MySQL `BINARY(16)` ordering.  The stored public header value is
already the canonical lower-case UUID text in the typed binding vector.

Therefore the UUID carrier selection does not require a new public contract:
the supported physical result carrier is `my_uuid_bytes`, and the public
typed value/wire remains `["UUID", canonical_lower_text]`.  Choosing how the
private MySQL prepared argument reaches that established carrier is
`IMPLEMENTATION_FREEDOM`, provided it preserves those facts, NULL, errors,
and canonical bytes.

## Two exact lowerings the present callers can carry

| Lowering | Prepared SQL | Native argument from the existing public value | Public/bundle impact | Status |
| --- | --- | --- | --- | --- |
| strict text slot | `UNHEX(REPLACE(?, '-', ''))` | existing canonical `str(UUID)` from `native_value()` | none; typed vector remains canonical UUID text | viable SQL alternative; raw metadata/type still needs DB proof |
| selected native bytes | `CAST(? AS BINARY(16))` | `UUID.bytes` (exactly 16 standard-order bytes) | none to the public typed value or binding vector; private MySQL native argument only | smallest selected candidate, pending raw DB proof |

Both give the same standard bytes only when the text path removes exactly the
four hyphens and the bytes path uses `UUID.bytes`, not `bytes_le`,
`UUID.int.to_bytes(..., 'little')`, or time-swapping.  Do not retain both
production paths: select native bytes because the established physical carrier
is bytes and it avoids a server-side text transformation.

## Exact closure and non-impact claim

- `native_value(tag, value, family)` is the only runtime argument conversion
  point: specialize only its MySQL/UUID arm from canonical text to
  `value.bytes`; preserve its PostgreSQL UUID text behavior.
- `native_arguments()` already preserves one MySQL argument per occurrence,
  so duplicate UUID reads need no new allocation framework.
- `anchor_suffix()` / rendering needs a target spelling for
  `my_uuid_bytes`: `CAST(? AS BINARY(16))`. Its verifier must independently
  require exactly those bytes.
- The compiled/pure reader already recognizes `my_uuid_bytes` plus
  `standard_bytes`. A newly enabled compiled MySQL parameter artifact must
  carry that existing physical identity; old artifacts do not change.
- The public compiled/binding scalar is still canonical text. Runtime
  `UUID.bytes` is derived only after public binding validation, so it changes
  neither public wire bytes nor stored vector identity.

This is not a proof that Connector/Python parameter metadata or expression
metadata reports the required BINARY(16) shape. The required direct prepared
database probe remains the authority for raw SQL bytes, driver parameter
encoding, prepare/result metadata, warnings, NULL, high-bit UUID, and row
differential.

The executable [pure_parameter_prep_selfcheck.py](pure_parameter_prep_selfcheck.py)
checks the exact no-DB transformations below; it does not substitute for that
probe.

