# Post-Phase70 public alpha release notes — 0.1.4

**Status:** These notes cover the `0.1.4` public-alpha candidate. A release is
established only when the accepted wheel and sdist are available from both the
versioned GitHub pre-release and PyPI channels; this document neither creates
those channels nor substitutes for their byte verification.

This release makes Pietto source read more like Python, adds one-line
relationships, inferred JOIN sources and inline `def` functions, and fixes
compiler and CLI defects found after 0.1.3. Source that 0.1.3 parsed keeps
parsing as before, with one exception: a file whose first code line is
indented is now PIE-P1000.
Some programs that 0.1.3 accepted are now refused because their SQL would fail
or mean something else; see
[Compatibility and retained data](#compatibility-and-retained-data). Pietto
remains an alpha; the CLI does not execute database queries.

## Highlights

- **Python-style layout.** `select:`, `select distinct:`, `group by:`,
  `order by:`, `partition by:`, the row `let:` and `enum NAME:` take their
  items after `:` on the header line, separated by commas, or in an indented
  block whose lines each hold one item or a comma-separated list, for example
  `order by: ordered_at desc, id desc`. `where:`, `satisfying:` and a shape's
  `check NAME:` take one condition after `:` or one condition per line of an
  indented block; the lines are joined with `and`, each as if written in
  parentheses. Inside parentheses an expression can continue over several
  lines; there is no backslash continuation, and an unclosed `(` is PIE-P1008.
  These forms parse to the same tree as the one-item-per-line form or the
  `and` chain, so checks and SQL are unchanged.
- **Soft keywords as names.** 26 words, among them `type`, `source`, `from`,
  `where`, `select`, `query`, `limit` and `check`, may also name a shape field,
  a `select` output, a row `let:` binding, a parameter or a typed VALUES
  column, as in `where type == "click"`. They do not name declarations or
  relations. `and`, `or`, `not`, `null`, `true`, `false`, `between`, `like`,
  `nullable` and `window` stay reserved.
- **One-line relationships.** `relationship r: a.x == b.y`, with one or more
  `and`-joined equalities between fields of two different relations, declares
  the endpoints `a` and `b`, so its roles are the relation names. A
  relationship of a relation to itself keeps the block form.
- **Shorter relationship JOINs.** A JOIN that follows a declared relationship
  needs only its header; its `from` line and VIA roles are optional, and the
  header may carry one step: `: from b`, `: via r` or `: via r: s -> t`. In an
  explicit-module project (`schema_version = 2`) a JOIN without `from` uses the
  one earlier binding that has a relationship to its target, in exactly one
  usable direction. No candidate is preferred: otherwise PIE-S2333 at the JOIN
  names every candidate. A JOIN with `on` and a CROSS JOIN still name their
  source with `from` (PIE-S2378). Single-file and schema version 1 project
  checks do not infer.
- **Inline `def` functions.** `def f(p: T not null) -> R nullable: return e`
  names a reusable scalar expression over `Bool`, `Int`, `Float`, `Decimal`,
  `Text`, `Date`, `Timestamp` or `UUID` parameters with explicit nullability.
  It is checked once where it is declared, and each call is replaced by its
  body before the call site is checked, so a call emits exactly the SQL of the
  same expression written by hand; no database function is created. A def
  belongs to its module (no import or export), recursion is refused, and an
  error inside a call is reported once however often the body uses the
  argument, except in a call written inside another def's body, where an
  error other than an argument mismatch (PIE-S2395) is reported as often as
  its expansion makes it, and in two project cases (see
  [Known limitations](#known-limitations)). An error in a def body stops the
  check before semantic analysis: of its file, and in a project of every
  module. Available in single files and explicit-module projects.
- **New diagnostics:** PIE-P1008 (an unclosed `(`), PIE-S2378 (a JOIN with
  `on` or a CROSS JOIN without `from`), PIE-S2379 (`def` in a schema version 1
  project), PIE-S2395 to PIE-S2399 (`def` arguments, recursion, forms, names
  and expansion size), PIE-S2380 (an ORDER BY key a target would misread) and
  PIE-S2604 (a relationship `on` operand error).

## Compatibility and retained data

- Bundles and saved jobs made by 0.1.3 or earlier are rejected by the 0.1.4
  code identity. Pietto neither migrates nor rewrites those bytes; use their
  matching old environment, then compile again for 0.1.4. Format markers are
  unchanged. The VS Code extension 0.1.0 accepts only the 0.1.2 wheel or its
  baseline fingerprint and refuses 0.1.4. This release adds no stable editor
  API.
- Explicit-module projects:
  - A field of an enum, or of an alias of one, is typed as that enum, as in a
    single file, and a `def` parameter the field does not fit is PIE-S2395.
    Programs 0.1.3 accepted are refused: `where status` (PIE-S2202),
    `status in ("active")` and `status not like "a%"` (PIE-S2105), and
    `lower(status)` and `coalesce(status, "x")` (PIE-S2104). Programs 0.1.3
    refused pass `check --project`: with JOIN inputs, a selected `let:` name
    bound to an enum field (0.1.3: PIE-S2333), a JOIN `on` that compares enum
    fields (PIE-S2334 and PIE-S2335) and a JOIN over a relation `let` that
    outputs one (PIE-S2333); without them, `select distinct` of an enum field
    and a grouped `satisfying` that compares one (PIE-S2333), a window or
    QUALIFY partitioned or ordered by one (PIE-S2103 `Unknown function`), and
    `lag`, `lead`, `first_value`, `last_value` and `nth_value` of one
    (PIE-S2104 `value type must be concrete`). The other JOINs over a source
    with an enum field, on which 0.1.3 crashed with a ValueError traceback
    (see Included repairs), pass when they select, group, order, compare or
    window the field, and `count(c.status)` there is PIE-S2314.
    `emit-sql --project` still blocks every table or query that reads a
    source with an enum field (PIE-B1003). Some enum reads still fail closed
    with PIE-S2333 (see Known limitations).
  - A LIKE pattern read through a `let:` name of a relation with JOIN inputs
    and ending in an unpaired `!` is PIE-S2105, where 0.1.3 emitted a
    VERIFIED `LIKE ... ESCAPE '!'` that PostgreSQL rejects.
  - The WHERE of a relation with a `let:` binding of unknown type, such as
    `k = null`, or with an error in a binding is checked as in a single file,
    except in a `select distinct` relation or one with QUALIFY (see Known
    limitations): `where n == k` is PIE-S2105, where 0.1.3 passed `check` and
    `emit-sql --project` blocked the relation with PIE-B1003, and a `def`
    argument there that does not fit is PIE-S2395.
  - A relation reports the errors of each `let:` binding, of its WHERE and of
    its SELECT items, in source order, where 0.1.3 reported only the first
    part that failed: the first failing SELECT item hid the others, an error
    in any relation's `let:` hid its WHERE, and an error in a JOIN relation's
    `let:` hid its WHERE and SELECT errors. After such an error in a JOIN
    relation's `let:`, its WHERE and, without GROUP BY or aggregates, each
    SELECT item that is no window report their own errors when they read no
    relation (`exists`, `scalar` or `in`), no binding with an error of its
    own and no field that does not resolve; any other SELECT item, such as a
    grouped or aggregate one, still reports none. Without JOIN inputs, the
    SELECT items of a `select distinct` relation and an aggregate argument a
    project refuses still report no error of their own (see Known
    limitations).
  - Beside a binding of unknown type or with an error, the other bindings keep
    their types: with `k = null`, `f = id` and `h = f`, `v = h` passes, where
    0.1.3 reported PIE-S2102 `Unknown field: h`, and a window that reads no
    binding, also through the named window it uses, is analyzed, where 0.1.3
    reported PIE-S2103 `Unknown function` for every window there. A selected
    read of `k` itself takes its type from where it stands, as in a single
    file, so `v = coalesce(k, 1)` and `v = 1 if k else 2` pass
    `check --project` where 0.1.3 reported PIE-S2102 `Unknown field: k`;
    `emit-sql --project` still blocks such a relation (PIE-B1003). A window
    that reads a binding there fails closed with the binding's error or
    PIE-S2333.
  - With JOIN inputs, a `let:` binding of unknown type is written into a later
    binding's `def` argument and null test, as without them: with `k = null`,
    `w = coalesce(k, o.id)` and `v = tnn(w)` for a `Text not null` parameter,
    `v` is PIE-S2395. A read of such a binding is typed as without JOIN inputs
    too, so a later binding, SELECT item or WHERE that is ill-typed only then
    reports its error: with `j = coalesce(k, 1)`, `d = len(j)` is PIE-S2104
    where 0.1.3 reported a bare PIE-S2333; with nothing ill-typed, such a
    relation still fails closed with PIE-S2333. A `let` that renames a field,
    such as `g = r.n` with `group by: g`, selects that field's group key, so
    `k = g` passes and emits where 0.1.3 reported PIE-S2102; another `let:`
    name selected from the groups is PIE-S2333 instead of PIE-S2102.
  - In a relation with JOIN inputs, a null literal compared or combined in
    `satisfying:`, also as a nullable `def` argument, is PIE-S2327 at the
    literal, and any other predicate of unknown type is PIE-S2333, where 0.1.3
    crashed with a ValueError traceback.
  - `emit-sql --project` reports an ORDER BY key with a part of unknown type,
    such as `(null is null)`, BLOCKED with PIE-B1003 `order`, where 0.1.3
    reported INPUT_REJECTED `Invalid current planning roots.` (exit `2`). A
    plan whose `let:` stages carry more columns than half the generated-node
    limit is BLOCKED with PIE-B1007 `generated_structure_limit` once the
    contract is read, before it is assessed and realized, beside no other
    blocker than a premise conflict: a 300-binding chain is refused in
    seconds instead of about a minute.
  - A GROUP BY over a table or query that is one global aggregate row, such
    as a table that selects only `c = count()`, passes `check --project` and
    emits, where 0.1.3 crashed with a TypeError traceback in `check --project`
    and in `emit-sql --project` of either relation.
  - A SEMI or ANTI JOIN over some inputs, such as a table that selects the
    fields of a source with a unique key in another order than the source
    declares them, emits, where 0.1.3 reported every table and query of the
    project INPUT_REJECTED `Project planning roots are unavailable.` (exit
    `2`) although `check --project` passed.
- LEGACY_FLAT projects (`schema_version = 1`): a table or query whose `from`
  reads a set operation reports PIE-S2334 at that `from`, as a single file
  does, where 0.1.3 stopped `check --project` with an internal
  AssertionError.
- Programs that 0.1.3 accepted and 0.1.4 refuses:
  - a file whose first code line is indented (PIE-P1000);
  - a comparison with the null literal, or with a `let:` name bound to it,
    a `between` whose value or both bounds are null, and an `in`/`not in`
    list whose value or every option is null, all never true (PIE-S2105;
    write `is null` or `is not null`);
  - a single file with an expression nested more than 450 levels anywhere,
    a relationship `on`, a type `ensure` and a window frame offset included
    (PIE-S2006 in every command; projects are not held to this bound);
  - checks that do not depend on an argument's type now also run over rows of
    unknown type, such as a source without a shape: an unknown function or
    connector, a window function without `window`, the argument count of
    `sign`, `year`, `month`, `day` and a connector, `substr` bounds, and a
    cast to any type but `Float` (PIE-S2103, PIE-S2104, PIE-S2105,
    PIE-S2306);
  - a condition that is not a `Bool` beside values of unknown type, for which
    0.1.3 emitted SQL that PostgreSQL rejects and MySQL converts: over a
    source without a shape, a `where`, shape `check` or index `when`
    condition that is a built-in call whose signature fixes another result
    type, such as `where len(t)` or `where lower(t)`, also through a `let:`
    name bound to one (PIE-S2202), and an operand of `and`, `or` or `not` or
    the condition of a conditional that is such a call, or of a known type
    that is not `Bool` beside an operand or branch of unknown type, such as
    `not lower(t)`, `t and 5` or `1 if len(t) else 2` (PIE-S2105). The same
    holds where an always-null argument leaves such a call's type unknown,
    as in `where lower(coalesce(null, null))`, also with a shape and in an
    explicit-module relation, which 0.1.3 passed and blocked at emission with
    PIE-B1003 or reported as a bare PIE-S2333 (a WHERE of such a relation
    with JOIN inputs still fails closed with PIE-S2333 unless a `let:`
    binding there has an error of its own). Over a source without a shape a
    `count()` output read alone, as an `and` operand or compared with a value
    that is not a number in `satisfying:` is PIE-S2202 or PIE-S2105, which
    0.1.3 refused only at emission;
  - an ORDER BY key that is a bare constant once `let:` names are inlined, and
    in a query with aggregates and no GROUP BY a key that reads an input field
    outside an aggregate (PIE-S2380);
  - a ROWS or GROUPS frame offset that is not a nonnegative `Int` literal up
    to 9223372036854775807, a larger window count literal (PIE-S2104),
    `cast(null as T)` and a literal LIKE pattern ending in an unpaired `!`
    (PIE-S2105);
  - a division with a known operand that is not `Int`, `Float` or `Decimal`
    (PIE-S2105); `Int / Int` is now an `Int` and a `Float` operand gives a
    `Float`, so a division result is checked where it is used;
  - `count` of a field typed by an alias of `Any` or of an enum, which 0.1.3
    passed at check and refused at emission (PIE-B1000), is PIE-S2314 at
    check;
  - in single files: a connector argument that is not a string literal
    (PIE-S2306), a repeated enum member (PIE-S2001), an aliased bare name that
    names no field (PIE-S2102), an INNER or LEFT JOIN whose target, `from`
    binding, relationship or role is unknown or whose VIA path does not
    connect (PIE-S2301, PIE-S2335), and a `let:` chain whose inlined
    expansion exceeds 768 weighted levels or 100,000 nodes (PIE-S2328);
  - in explicit-module projects: relationship declaration errors
    (PIE-S2601 to PIE-S2603), shape item errors (PIE-S2501 to PIE-S2503) and
    repeated enum members (PIE-S2001), as single files report them, and a
    relationship `on` operand error (PIE-S2604, in both modes), whether or
    not a query uses the relationship;
  - PostgreSQL emission of an identifier longer than 63 bytes, which
    PostgreSQL would truncate, and of a window integer argument outside int32
    (PIE-B1000);
  - single-file PostgreSQL emission of an arithmetic whose every operand is
    `null`, such as `null + null`, `-null` or `coalesce(-null, n)`, which
    PostgreSQL cannot type, and of a table or query that another relation of
    the file reads when one of its outputs is `null` itself, such as
    `v = null` or a `let:` name bound to `null`, which PostgreSQL gives the
    reader as a `text` column (PIE-B1000); MySQL emission is unchanged;
  - a `between` with one null bound, which is now a `Bool` whose other bound
    is checked against the value: `n between null and "z"` with an `Int`
    field and a conditional such as `n if flag else n between null and 1`
    are PIE-S2105, where 0.1.3 passed `check` and emitted SQL that
    PostgreSQL rejects;
  - an operand of `+`, `-`, `*`, `/` or `%` that the operator does not take
    beside a `null` operand, also a `let:` name bound to one, such as
    `label + null` for a `Text` field, `lower(label) - null` or `0.5 % null`
    (PIE-S2105), as `label + label` and `0.5 % 0.5` are, where 0.1.3 emitted
    SQL that PostgreSQL rejects for a `Text` operand;
  - a `let:` value, or an expression that reads a `let:` name, that is
    ill-typed once the name has the type of its value written in its place:
    a name whose value is `null` takes its type from where it is read, as
    `null` does, and over a source without a shape a name has its binding's
    type. With `k = null` and `j = coalesce(k, 1)`, `d = len(j)` is PIE-S2104
    in the binding and `v = lower(j)` PIE-S2104 at `lower`, where 0.1.3
    emitted `lower(COALESCE(NULL, 1))`; over a source without a shape, with
    `w = n is null`, `-w` is PIE-S2105 and `coalesce(w, 0)` PIE-S2104. An
    explicit-module project reports such an error too: in a binding of a
    relation without JOIN inputs, as `d = len(j)`, which 0.1.3 passed; in a
    SELECT item of such a relation, as `v = lower(j)`, where 0.1.3 reported
    PIE-S2102 `Unknown field: j`; and with JOIN inputs, where 0.1.3 reported
    a bare PIE-S2333 (see Explicit-module projects above). A column that a
    relation computes from such a name has that type in later relations: with
    `z = coalesce(k, n)` for an `Int nullable` field `n`, a later relation's
    `v = lower(z)` is PIE-S2104, where 0.1.3 emitted `lower("z")` (and in a
    project reported PIE-S2102 `Unknown field: k` and PIE-S2333).
- SQL that differs for programs 0.1.3 already emitted:
  - MySQL `Int / Int` emits `a DIV b` instead of `a / b`, so the result is an
    integer, not a DECIMAL; PostgreSQL bytes are unchanged. This includes a
    `let:` name read as above: with `k = null` and `j = coalesce(k, id)`,
    `j / 2` emits ``COALESCE(NULL, `id`) DIV 2``, and over a source without
    a shape, with `u = 7`, `u / 2` emits `7 DIV 2`, as the values written in
    place do; a later relation's `z / 2` of the column `z` above emits
    `` `z` DIV 2 ``.
  - Single-file `cast(j as Float)` of a `let:` name whose value reads `null`,
    such as `j` above, or of a column an earlier relation computes from one,
    such as `z` above, emits `CAST(... AS double precision)` (PostgreSQL) or
    `CAST(... AS DOUBLE)` (MySQL) as the value written in place does, where
    0.1.3 refused it with PIE-B1000.
  - Single-file `avg` of an `Int` emits `AVG(CAST(x AS double precision))` on
    PostgreSQL and `AVG(CAST(x AS DOUBLE))` on MySQL, as project SQL does.
  - PostgreSQL `sign(x)` of an `Int` emits `CAST(sign(x) AS bigint)`.
  - Single-file PostgreSQL `lag`, `lead`, `first_value`, `last_value` and
    `nth_value` of a string literal without a `lag`/`lead` default write the
    literal as `CAST('b' AS text)`, where 0.1.3 wrote `LAG('b')`, which
    PostgreSQL rejects; MySQL bytes are unchanged.
  - An ORDER BY input field that has the same name as a different output alias
    is qualified with its FROM item's reference name.
- Single-file `explain` reports the type an output has when it is computed
  from a `let:` name whose value reads `null`, also as the column of a later
  relation, where 0.1.3 reported `unknown`: with `j = coalesce(k, id)`,
  `v = j + 1` is `Int`.
- Diagnostics: many messages name their cause more precisely. Invalid source
  gets different PIE-P1000 wording, counts and positions: at most one parser
  error per top-level declaration, naming the unexpected token and what was
  expected. A lone CR now ends a line in every reported position, and
  PIE-P1004 counts lines only at LF, CRLF and CR. A project reports a restated
  diagnostic once.
- CLI: a failed write to stdout, and a refused `--output` (no SQL to write,
  an existing output the user may not write or that belongs to another user,
  or in single-file mode an existing FIFO, socket or device), exit `2`; a
  failing stderr is ignored and the command keeps its own exit code.
  Repeated or abbreviated `--format` and `--project` options are resolved as
  argparse resolves them, so `--form json` is no longer ignored.

## Included repairs

Compiler:

- Division follows SQL: `Int / Int` truncates toward zero (PostgreSQL `/`,
  MySQL `DIV`), a `Float` operand gives a bare `/`, and Pietto never inserts a
  cast; write `a * 1.0 / b` or `cast(a as Float) / b` to keep the fraction.
- Type aliases, alias chains included, are read as their builtin type by
  arithmetic, `not`/`and`/`or`, comparisons, `between`, `in`, `like`, the
  fixed-signature scalar functions, Bool conditions, the aggregates and the
  window value functions, so an alias program checks and emits like its
  base-typed twin.
- `sum` and `avg` of a `Decimal * Decimal` argument emit single-file SQL
  instead of PIE-B1000. `amount in (1, 2)` with a `Decimal` field is accepted
  wherever `amount == 1` is; project emission refuses that pair with
  PIE-B1003 (`membership_type_pair_not_admitted`), as it refuses the
  comparison.
- The `let:` inline limit (PIE-S2328) measures the recursion emission needs
  instead of crashing with RecursionError; `let:` bodies are checked with the
  earlier bindings, and a binding's own error no longer cascades into unknown
  fields or extra window errors.
- Single-file analysis of a long chain of tables takes linear time.
- Gradual typing is kept: an aliased read of a field of any type is a
  computed output, aggregates and `satisfying` over fields of unknown type are
  not refused at check, and a `satisfying` predicate of unknown type fails at
  emission with PIE-B1000 instead of an internal error.
- In a grouped query, `first_value`, `last_value` and `nth_value` over an
  aggregate output emit SQL instead of crashing.
- In single files, a `lag` or `lead` result of an enum keeps the enum's
  declaration, as a `first_value` result does, so a later relation may
  combine the column with a field of that enum, as in
  `coalesce(previous, status)`, which 0.1.3 refused with PIE-S2104 (and a
  conditional with PIE-S2105).
- Projects: a project relation may read a declaration written later in its
  module; a relationship JOIN over an input completed in the same run, such
  as a named `select distinct` query, and a SEMI or ANTI JOIN over a table
  that reorders a keyed source's fields emit instead of INPUT_REJECTED;
  repeated `on` operands, a VIA through a grouped endpoint, an unknown grain, a
  grouped query listing a window before an aggregate, a JOIN over a source
  with enum or shape fields, an ORDER BY of an enum group key, a GROUP BY over
  a global aggregate and a LEGACY_FLAT read of a set operation no longer
  crash; deeply nested project expressions are PIE-S2006 instead of a
  RecursionError traceback, and a configuration or package manifest nested
  too deeply is a `project_resource` error; a `let:` binding read in a
  SELECT item no longer reports a false unknown field; a bare PIE-S2333 for a
  relationship JOIN over an input it cannot read yet names the reason; the
  JOIN fan-out remedy lists each key once; and query block IR verification
  checks every use against the output its owner names.
- The execution API reports a recursion overflow while preparing a query as
  PIE-R1004.

CLI:

- Every command writes its results through one stdout writer. A full device,
  closed stream or other write failure exits `2` with a fixed notice instead
  of a traceback, exit `120` or a silent exit `0`, and a reader that closes the
  pipe early ends the run quietly. `--help`, `--version` and usage errors use
  the same writers.
- Operating-system errors are reported by path with a fixed English reason
  and errno or winerror codes, without temporary names or localized text.
- `--output` writes UTF-8 with LF line endings on every platform. A new file
  gets the mode `open(path, "w")` gives (`0o666` less the umask, or what a
  default ACL grants). A replacement never gets wider permission bits than
  the file it replaces: it keeps them only on Linux when both files have the
  same owner and group and are shown to carry no ACL, and otherwise keeps at
  most the owner bits. Temporary files use short `.pietto-*.tmp` names.
- C1 controls, line and paragraph separators and bidirectional controls are
  written as `\uNNNN` in CLI diagnostics, paths and project text records; SQL
  text (stdout and `--output`) and JSON values keep them raw.
- Windows: trusted project reads no longer refuse unchanged files because of
  ctime, and directory junctions are refused like symbolic links.

## Known limitations

- The release target is compiler and package coverage on CPython 3.12 and
  3.13 for Linux x86-64; the support boundary is established by formal
  acceptance of the actual distribution bytes. Native-route evidence is
  limited to CPython 3.13.13 on the qualified integration host with the
  lock's exact artifacts. Other platforms, Python versions, database releases
  and driver closures are not claimed. No signing or attestation.
- A successful `check` is not an emission proof. Single-file `explain` and
  `emit-sql` refuse an authored `qualify:` block and a relationship JOIN with
  PIE-I1000; JOINs, set operations, DISTINCT and relation lets need
  `emit-sql --project`.
- An error in a call written inside another def's body is reported at that
  def as often as the called def's expansion makes it, in single files and
  projects: with
  `def low(x: Int nullable) -> Bool nullable: return x < 3 or x < 4`, a def
  body that calls `low(null)` gets two PIE-S2105. An argument mismatch
  (PIE-S2395) there is reported once.
- A project check still repeats the errors of a JOIN `on` condition, written
  by hand or made by a `def` call, and reports a query header parameter passed
  to a `def` and read in a position that refuses it (PIE-S2355) at each use of
  the argument.
- In single files, `lag`, `lead`, `first_value`, `last_value` and
  `nth_value` over a field typed by an alias of an enum are PIE-S2104, while
  the enum itself is accepted; an explicit-module project types such a field
  as the enum and accepts both.
- In an explicit-module project, some reads of an enum value fail closed with
  PIE-S2333 at the table or query, where a single file passes or reports
  another code: without JOIN inputs, an aggregate of an enum field
  (PIE-S2314 in a single file and after a JOIN), a selected `let:` name
  bound to an enum value and a computed output of enum type other than a
  window value, such as `coalesce(new_status, status)`; with or without them,
  an output such as `status in ("active", null)`, and a window value function
  over an enum field of a row that also has a field of another module's enum
  of the same name. A project check does not type the ungrouped `order by` of
  a relation without JOIN inputs that is not `select distinct`, so
  `order by: lower(status)` passes `check --project` there.
- In an explicit-module project, a relation without JOIN inputs reports no
  error of its SELECT items when it is `select distinct`, nor of an aggregate
  argument that a project refuses (PIE-S2314 or PIE-S2315 in a single file,
  such as `max(t + 1)`): it reports PIE-S2333 at its table or query, or,
  beside another error such as one in its WHERE, only that error.
- In an explicit-module project, after an error in the `let:` of a relation
  with JOIN inputs, a SELECT item reports no error of its own when the
  relation has a GROUP BY or aggregates, when it is a window, or when it
  reads a relation, a binding with an error of its own or a field that does
  not resolve.
- Over a source without a shape, a built-in call with an argument of unknown
  type has an unknown type outside a condition, also where its result type
  does not depend on the argument: `lower(t) + 1` passes `check` and emits
  SQL that PostgreSQL rejects, `len(t) / 2` emits `/` on MySQL, which keeps
  the fraction that PostgreSQL drops, and a condition built on such a call,
  such as `where len(t) + 1`, passes. Over such a source a `count` output
  with an argument has an unknown type to `satisfying` too.
- In an explicit-module project, a relationship JOIN without `on` whose input
  is a `select distinct` query completes on its own, but reports PIE-S2333 at
  its table or query when that table or query is itself `select distinct` or
  once a later table or query reads its result with a JOIN `on`, a CROSS JOIN
  or `select distinct`. In some shapes, for example when such a query is
  joined through a relationship with the relation it reads, `check --project`
  passes but `emit-sql --project` reports INPUT_REJECTED (exit `2`).
- A function argument of known type is not checked when another argument has
  an unknown type: over a source without a shape, `matches(a, 1)` passes
  `check` and PostgreSQL emission writes `"a" ~ 1`.
- A `def` argument of unknown type is not checked against its parameter.
  Inside a built-in call, `coalesce`, conditional or `in` list only `null`
  itself takes a type from where it stands, and `null` takes none inside
  `and`/`or` or in a built-in whose parameter admits
  more than one type (`year`, `month`, `day`, `sign`), so the arguments
  `null and true`, `year(null)` and `coalesce(-null, n)` pass a `not null`
  parameter unchecked, written by hand or through a `let:` name.
- In a relation without JOIN inputs that is not `select distinct`, a project
  check does not type a `def` argument in the ungrouped `order by`, as it
  does not type the same expression written by hand there. An argument of
  known type that does not fit its parameter therefore passes
  `check --project` there: with a field `text: Text not null` and
  `def nn(x: Int not null) -> Int not null: return x`, `order by: nn(text)`
  passes. `emit-sql --project` blocks it with PIE-B1003 without naming the
  argument.
- In an explicit-module project, a relation with a `let:` binding of unknown
  type, such as `k = null`, fails closed: with JOIN inputs, a GROUP BY,
  `select distinct` or QUALIFY it reports PIE-S2333 at its table or query
  even when nothing in it is ill-typed (a single file passes such a GROUP BY,
  QUALIFY or relationship JOIN without `on`), and otherwise
  `emit-sql --project` blocks it with PIE-B1003 once it passes
  `check --project`. A `select distinct` relation or one with QUALIFY does
  not check its WHERE beside such a binding or a binding with an error of its
  own: it reports that PIE-S2333, or the binding's error, in place of the
  WHERE's errors.
- A `substr` start and count must be `Int` literals written in the call: a
  `let:` name bound to one, such as `start = 1` in `substr(t, start, 1)`, is
  PIE-S2104, also in a `def` argument, although single-file emission would
  write the literal in its place.
- Division with a `Decimal` operand is not specified yet: it has no result
  type and emits a bare `/`. Division by zero follows the target (PostgreSQL
  raises an error, MySQL returns NULL), and dividing the smallest `Int` by -1
  is not specified.
- `def` takes only the eight builtin types (or a same-file alias of one) and
  positional arguments; a call is refused where the written form must be a
  literal, a field or a window call that Pietto checks by its own rule, such
  as inside a window specification, LIMIT, a VALUES row or a relationship
  condition (PIE-S2397). A comparison, `between` or arithmetic is not proven
  non-null, so such defs declare a `nullable` result. An argument appears in
  the SQL as often as the body uses its parameter. `constraint` and `derive`
  still cannot be called.
- `--output` does not copy a replaced file's owner, group, set-id or sticky
  bits or its ACL entries; the write check uses the real user, so root can
  still replace a read-only output.

## Support and release boundary

The [language guide](language.md) is the reference for the forms above; its
[Layout](language.md#layout) and
[Inline functions](language.md#inline-functions-def) sections describe the new
syntax. Published bytes are never overwritten. A later defect
is addressed in a later version; any PyPI yank remains an owner action.

---

# Phase70 public alpha release notes — 0.1.3

**Status:** These notes describe `0.1.3`, published and byte-verified on the
versioned GitHub pre-release and PyPI channels.

`0.1.3` extends query authoring and checked execution in explicit-module
projects (`schema_version = 2`). Pietto remains an alpha; the CLI still has no
database-execution command.

## New capabilities

- **Relation lets.** `let NAME:` at the start of a table or query body declares
  a local relation whose body is FROM-based, a set operation or a typed VALUES
  body. The other lets and the body of its declaration read it by name with
  `from`, a JOIN target, a set operand or an `exists`, `scalar` or `in` read,
  any number of times and whether it is written before or after them (a let
  with `capture` lines, below, is read exactly once). Project
  SQL emits each let once as one named CTE, after the lets it reads and exactly
  like the equivalent module-level declaration, and every read refers to that
  CTE; a let keeps its own LIMIT, so a filter written where it is read stays
  outside that LIMIT. A source read only inside a let is a source of the query
  for the emission contract, the compiled query, source qualification and R2
  source requirements. A let is never a module declaration: it cannot be
  exported, imported, selected by `emit-sql --project` or compiled on its own.
  A declaration has at most 64 lets (`PIE-S2357`); a let named like a module
  relation, an import binding, another let or a JOIN binding is `PIE-S2001`,
  and no name hides another. A let that no block of its declaration reads is
  `PIE-S2359`, reads that form a cycle, a let reading itself included, are
  `PIE-S2302`, and a let nested deeper than 16 query blocks is `PIE-S2360`.
  The row-level `let:` clause keeps its meaning.
- **Named query parameters.** An entry `query` header declares at most 64
  `Bool`, `Int`, `Float` or `Text` parameters, each `not null` or `nullable`,
  for example `query since(low: Int not null, note: Text nullable):`. A read is
  available in `let:` bindings, `where`, JOIN `on`, ungrouped SELECT items,
  `satisfying`, `qualify`, ORDER BY keys through a `let:` binding or a restated
  selected expression, a computed group key of a query without JOIN inputs,
  `count`, `avg`, `min` or `max` of one `let:` name, and as a window value,
  `lag`/`lead` default or structural count (`lag`/`lead` offset, `ntile` bucket
  count, `nth_value` position; an `Int not null` parameter, `PIE-S2358`).
  LIMIT, window frames, window PARTITION BY and ORDER BY keys and other
  positions refuse a read (`PIE-S2355`). A header is available on an entry
  query whose own FROM reads a relation, with or without relation lets. Every
  FROM-based let of that query reads the header like its body, under the same
  position rules, a let with `capture` lines included (its reads render where
  the let renders); no other declaration reads it. A parameter named like a
  let of the query or like an input field, `let:` name, relation, JOIN
  binding, SELECT output or named window of the query or of one of its lets is
  `PIE-S2354`, and a query with parameters is never the input of another
  relation nor read by `exists`, `scalar` or `in` (`PIE-S2356`). On a VALUES,
  set-operation or table-function body, and beside a let whose FROM is a table
  function (whether or not that let reads a parameter), a header stays
  `PIE-S2346` at each parameter.
  `emit-sql --project` writes the unbound template as `pietto.sql-emission.v2`
  with a typed placeholder for each read under both literal policies:
  PostgreSQL reuses one `$n` per parameter across every CTE, subquery and
  LATERAL derived table, and MySQL writes one `?` per read in rendering order.
  One statement renders at most 65,535 placeholders, reads and bind-safe slot
  uses together (`PIE-B1007`, `parameter_occurrence_limit`). A check that
  needs a value is a binding obligation (`int_range_representable`,
  `text_result_width` or `structural_count_interval`) naming every parameter
  it depends on, including one read in a let with `capture` lines, and
  re-derived at every binding. `compile_query` and
  `export_bundle` keep the unbound template (bundle format marker
  `pietto.compiled-execution.v2`), and `execute(..., parameters={...})` binds
  it by name on `postgres_rows`, `mysql_rows` and `postgres_adbc`; a missing
  or extra name, a value of the wrong type, NULL for a `not null` parameter
  and a failed obligation are refused before any connection. `save`,
  `save_recoverable` and `relay_live` bind new values the same way before the
  workspace opens; `open_saved_read`, `release_saved_read`,
  `publish_saved_generation`, `verified_export` and `recover` restate the
  saved binding, and any difference is `PIE-R1009` (`BINDING_VECTOR`).
  `values=` slots are unchanged and independent.
- **Computed group keys and `let:` extrema.** In an explicit-module query,
  `group by` may name a computed `let:` binding; the emitted SQL groups by that
  value's LET-stage column, never by a repeated expression. Such a key never
  supplies source-row grain, and R2 refuses it before any workspace access
  (`PUBLIC_R2_COMPUTED_GROUP_KEY`). With JOIN inputs the key records every JOIN
  side its value reads but never proves a side unique per group, so it never
  removes a fan-out refusal; only direct field keys protect a JOIN side. `min`
  and `max` accept one `let:` name and keep its proven range while admitting
  NULL; with JOIN inputs the argument reads its JOIN-side fields under the
  fan-out rule of a direct field argument.
- **Typed VALUES.** A table, query or relation-let body may be a typed
  `values(name: Type not null, ...)` header followed by one row of fixed
  literals per line, or the header alone for a zero-row relation. Each column
  is `Bool`, `Int`, `Float` or `Text`, `not null` or `nullable`; rows keep
  their order and duplicates, and the row schema comes only from the header. A
  column type, a row width, a cell that is not a fixed literal, a cell that
  does not match its column, and more than 1,000 rows or 64 columns are
  `PIE-S2361` to `PIE-S2365`; a body within those limits whose emission
  exceeds the compiler's generated-structure or document limit is BLOCKED with
  `PIE-B1007`. Project SQL writes every column alias and every cell inside a
  CAST to its declared type, and a cell is never a bound parameter. A VALUES
  body read beside a physical source emits and compiles for PostgreSQL and
  MySQL. A statement whose only inputs are VALUES bodies runs on PostgreSQL
  under a session-context qualification whose premise includes `pg_catalog`
  and that records no relation root and no relation catalog check; MySQL
  refuses it (`PIE-B1003` at emission and compilation, `PIE-R1003` before
  connecting). R2 refuses a query with a VALUES body before any workspace
  access (`PIE-R1004`, `PUBLIC_R2_VALUES_COORDINATE_BASIS`). Grouping over a
  VALUES input is not available yet (`PIE-S2333`).
- **Closed relation reads.** In a table or query body `exists r` and `not
  exists r` test whether `r` has a row, `scalar r.c` reads the column `c` of
  `r`, and `value in r` and `value not in r` compare a value with the one
  column of `r`; `r` is a source, a module table or query, or a let of the
  declaration. A read is available in WHERE and in the SELECT of an ungrouped
  query, let bodies included; anywhere else it is `PIE-S2349`, `PIE-S2348` or
  `PIE-S2350` at the read. `exists` is a `Bool not null`. `scalar` is always
  nullable: a read of no row is NULL, and a read of more than one row is the
  database's own runtime error, `PIE-R3003` with SQLSTATE `21000`; no LIMIT is
  added. `in` and `not in` keep SQL three-valued logic, are a nullable `Bool`
  and are never rewritten to an ANTI JOIN, a literal list or a COALESCE; over
  an empty `r`, `NULL in r` is false and `NULL not in r` is true. `scalar`
  cannot yet read a set, an authored JOIN, a table function or a relation that
  reads one of them or a VALUES body (`PIE-S2348`), while a VALUES body itself
  is read like any relation; for such a block `emit-sql --project` and
  `compile_query` check the one column of an `in` read (`PIE-B1003`). Project
  SQL emits each read block once as its own named CTE and each read as a
  subquery over it, so the read block's `order by` and `limit` stay inside its
  CTE. A source read only through relation reads is a source of the query. R2
  refuses a query with a relation read before any workspace access
  (`PIE-R1004`, `REFINEMENT_EXPRESSION_BLOCK_READ`).
- **Correlated lets and LATERAL joins.** A relation let may start with
  `capture NAME` lines, one per line, naming the FROM input or a JOIN binding
  of its declaration body; inside the let `NAME.field` reads that field of the
  current outer row, while bare names keep naming the let's own input. Only
  FROM and JOIN row fields are captured. A captured field keeps the outer
  field's type and is nullable when that field is or when an earlier LEFT,
  RIGHT or FULL JOIN may null-extend its binding; an outer JOIN ON condition
  never narrows it. Such a let is read exactly once: by `exists`, `not
  exists`, `scalar`, `in` or `not in` in the WHERE or in the SELECT of an
  ungrouped declaration body, or as the target of a `cross join`, `inner join`
  or `left join`, which reads it LATERAL with no new keyword. Every outer row,
  duplicates included, gets its own result: a correlated read is never
  rewritten to a JOIN, deduplicated or decorrelated, a correlated `scalar`
  keeps the runtime error for more than one row (`PIE-R3003`, SQLSTATE
  `21000`), `in` and `not in` stay three-valued, and a `left join` keeps each
  left row without a row of the let once, with the let's fields NULL. The let
  body is a FROM relation with an optional WHERE and an ungrouped, window-free
  SELECT; a let joined LATERAL or read by `scalar`, `in` or `not in` may end
  in ORDER BY and a static LIMIT, a top-k per outer row in which the database
  chooses among rows that tie on every key. Project SQL emits the let inside
  its read as nested derived tables, or as the JOIN's `CROSS JOIN LATERAL`,
  `INNER JOIN LATERAL ... ON` or `LEFT JOIN LATERAL` derived relation, never
  as a CTE. A `scalar`, `in` or `not in` read of a let that ends in ORDER BY
  and LIMIT is PostgreSQL only: PostgreSQL wraps the let in the read's own
  derived table, while MySQL `emit-sql --project` and `compile_query` refuse
  each such read, in source order, with `PIE-B1003`
  (`mysql_correlated_order_or_limit_read_not_admitted`) before any connection,
  and `load_bundle` refuses a MySQL bundle that claims one (`PIE-R1008`); a
  let joined LATERAL keeps its ORDER BY and LIMIT on both targets. The binding of a table
  function cannot be captured (`PIE-S2366`), though its body's JOIN bindings
  can; otherwise, a capture line naming no single FROM or JOIN
  row input is `PIE-S2366`, a repeated
  capture name `PIE-S2367`, a capture of an input of the let itself
  (self-correlation) `PIE-S2368`, a captured field the input does not have
  `PIE-S2369`, a direct table-function FROM in a capture let (read it through
  another let), another let body or ORDER BY that correlation does not support,
  and every read of the let after its first `PIE-S2370`, a capture of an input
  that is not left of the LATERAL JOIN `PIE-S2371`, and a RIGHT, FULL, SEMI or
  ANTI JOIN of such a let `PIE-S2372`. A field read of a captured input whose
  columns are not known before completion (a set, an authored JOIN, a typed
  VALUES body, a table function, a relation reading one of them, or a relation
  whose own errors leave its columns unknown) is `PIE-S2369` at `check
  --project`, whatever field it names. When the captured outer input's fields
  are known, the let's own FROM may read a set, an authored JOIN, a typed
  VALUES body or a let reading a table function. R2 refuses a query with a
  correlated read
  (`REFINEMENT_EXPRESSION_BLOCK_READ`) or a LATERAL JOIN
  (`REFINEMENT_LATERAL_JOIN`) before any workspace access; ordinary execution
  on every route, `save` and bundles accept them.
- **Bounded `generate_series`.** A table, query or let body may read
  `from generate_series(start, stop, step) as n`, a zero-input relation whose
  rows and only column `n` are `Int not null`. `generate_series` with exactly
  three fixed integer literals in the signed 64-bit range is the only admitted
  table function: another function is `PIE-S2373`, another argument count
  `PIE-S2374`, an argument that is not such a literal (`null`, another literal
  type, a name, a parameter or an expression) `PIE-S2375`, a zero step
  `PIE-S2376` and more than 1,048,576 rows `PIE-S2377`. Its closed catalog
  entry carries the determinism and side-effect evidence admission consumes.
  Grouping or aggregating directly over a table-function input is `PIE-S2333`
  for now (read it through a let first), and `scalar` cannot read it
  (`PIE-S2348`). Project SQL writes each input as a CTE over
  `pg_catalog.generate_series` with each fixed argument CAST to
  `pg_catalog.int8`, never as a bound parameter; a binding longer than 63
  UTF-8 bytes is `PIE-B1002` (`table_function_binding_unrepresentable`). It is
  PostgreSQL only: MySQL `emit-sql --project` and `compile_query` block each
  input with `PIE-B1003` (`table_function_not_admitted_on_target`), and
  `load_bundle` refuses a MySQL bundle that claims one (`PIE-R1008`).
  PostgreSQL runs a statement whose only inputs are table functions or VALUES
  bodies under the session-context qualification of a VALUES-only statement,
  with no runtime catalog check of the function. R2 refuses a query with a
  table function before any workspace access (`PIE-R1004`,
  `PUBLIC_R2_TABLE_FUNCTION_COORDINATE_BASIS`).

## Refusals and limits

The new forms are available only in EXPLICIT_MODULES projects. Single-file
analysis and LEGACY_FLAT projects keep refusing them with the temporary
`PIE-S2345..PIE-S2352` diagnostics, and PACKAGE_ROOT `explain --project` does
not read relation bodies, so explaining a package that uses them does not make
its relations available. In an explicit-module project each file reports its
pre-admission diagnostics first, in source order (the capture forms
`PIE-S2366`, `PIE-S2367`, `PIE-S2368` and `PIE-S2370..PIE-S2372` among them),
and then the header checks of its entry queries; after either, semantic
analysis does not run. In an explicit-module project a header on a VALUES,
set-operation or table-function body or beside a let that reads a table
function (`PIE-S2346`) is still refused this way. This release adds
`PIE-S2345` to `PIE-S2377`.

Known limitations of this release:

- A typed VALUES body of 1,000 rows and 64 columns passes `PIE-S2365` but is
  always BLOCKED at emission by the compiler's generated-structure or document
  limit (`PIE-B1007`).
- The width and type pair of an `in` read of a set, an authored JOIN, a
  typed VALUES body or a table function is checked only at emission
  (`PIE-B1003`), not by `check --project`.
- An INNER JOIN whose ON has a nullable `Bool` field as an AND conjunct of its
  own (`on o.flag`) checks, but `emit-sql --project` and `compile_query` block
  it with `PIE-B1002` (`join_output_nullability_drift`) on both targets;
  `o.flag == true` is not admitted either (`PIE-B1003`). Write the test in
  WHERE instead (`where o.flag`).
- In a let with `capture` lines, an ORDER BY key that is not a field of the
  let's input, such as one of the let's own SELECT outputs, is reported only
  as `PIE-S2333` at the declaration (`Project relation semantic completion is
  unavailable`), with no diagnostic at the key.
- While a module import cycle exists (`PIE-S2703`), a project check reports
  besides it only parse, semantic analysis and source connector diagnostics;
  the checks made while completing relations appear once every cycle is
  fixed.
- An unknown field in a SELECT item of an explicit-module query can be
  reported twice as `PIE-S2102` at the same position.
- In a single-relation explicit-module query, a reference or shape error in a
  grouped `satisfying` is reported only as `PIE-S2333` at the declaration.
- LEGACY_FLAT project checks report neither `satisfying` errors nor a WHERE
  condition that is not `Bool`, which single-file `check` reports, and a
  LEGACY_FLAT query that reads a set operation stops `check --project` with an
  internal `AssertionError`.
- A selected query that reads a table declared later in the same module checks,
  but `emit-sql --project` refuses it as
  INPUT_REJECTED (`Project planning roots are unavailable.`) and
  `compile_query` raises `CompileRejected`; declare the read relation first.
- `compile_query` refuses (`PIE-R1004`, `COMPILED_EXPORT_SOURCE_BINDING`) an
  emission contract that also describes a source the query does not read,
  which `emit-sql --project` accepts; describe only the query's sources.

## Included repairs

- A module import cycle in an explicit-module project no longer crashes the
  project check, `emit-sql --project` or `compile_query`; it is reported as
  `PIE-S2703`.
- `import pietto.execution` no longer imports the saved-result job subsystem;
  the first use of a saved-result name imports it.
- In an explicit-module project, `satisfying` on a query without GROUP BY no
  longer crashes `check --project`, `emit-sql --project` or `compile_query`:
  it is `PIE-S2323` (`PIE-S2308` when the predicate holds an aggregate), as in
  single-file analysis. A single-relation aggregate query with `satisfying`,
  which reported `PIE-S2333` in `0.1.2`, now also reports `PIE-S2323`, the
  documented code.
- On `postgres_adbc` a server error raised while the result is read keeps its
  SQLSTATE: a `scalar` read of more than one row is `PIE-R3003` with
  `sqlstate` `21000`, as on the other routes, instead of an error without a
  `sqlstate` (cause `ArrowInvalid`), and the 10 second statement limit reached
  while reading is `PIE-R3002` (`STATEMENT_TIMEOUT`) instead of `PIE-R3003`.
  [Execution](execution.md) now states the terminal facts of a server error
  per route: `postgres_adbc` reports cleanup `LOCAL_CLOSED_REMOTE_UNOBSERVED`
  with no cleanup failure, and on `mysql_rows` a statement error does not end
  the transaction, which is then rolled back (`ROLLBACK_ACK`).
- `save_recoverable` and `recover` now reject a query whose largest
  continuation page binds more placeholders than the `parameters` resource
  limit with `PIE-R1004` (`REFINEMENT_RESOURCE_LIMIT`) before workspace access
  or a connection.

## Compatibility and retained data

Bundles and saved jobs produced by `0.1.2` are refused under `0.1.3` by code
identity. Pietto neither migrates nor rewrites them; keep the matching old
environment to use retained state, and compile again for this release.
`pietto.sql-emission.v1` and project JSON v2 keep their formats, and relation
lets, VALUES bodies and relation reads add nothing to project JSON; only a
verified document of a query with header parameters is
`pietto.sql-emission.v2`, which a v1 reader refuses by its tag. Such a query
bundles as `pietto.compiled-execution.v2`, which a v1 reader refuses, and a
saved binding with parameters is recorded as `pietto.binding-vector.v2`; a
binding without parameters is recorded as before.
The VS Code extension `0.1.0` accepts only the `0.1.2` wheel or the `9e74aa68`
baseline fingerprint and refuses `0.1.3`; updating it belongs to the
extension's owner, and this release adds no stable editor API.

Target-conformance receipt v3 stores each public emission document once. It is
test and CI evidence only, not a query, bundle or saved-job format.

## Support and release boundary

The release target is compiler and package coverage on CPython 3.12 and 3.13
for Linux x86-64. That support boundary is established only by acceptance of
the formal distribution bytes. Native route evidence is limited to CPython
3.13.13 on the qualified integration host with the lock's exact artifacts;
other native platforms, Python versions, database releases and driver closures
are not claimed. Published bytes are never overwritten. A defect found after
release is fixed in `0.1.4`; any PyPI yank is the owner's action, noted on the
GitHub pre-release.

---

# Phase69 public alpha release notes — 0.1.2

These notes describe `0.1.2`. Its versioned GitHub pre-release and PyPI listing
determine release availability. The historical `0.1.1` wheel and `v0.1.1`
assets are not replaced.

## Public alpha API

- `pietto.execution` exposes explicit `postgres_rows` for PostgreSQL 18.6,
  `mysql_rows` for MySQL 8.4.12, and `postgres_adbc` for PostgreSQL 18.6.
  Each route uses its selected pinned dependency closure and never falls back to
  another route.
- Results use caller-owned Arrow batches and terminal outcome facts.
  `UNKNOWN`, `REMOTE_QUIESCENCE_UNCONFIRMED`, and remote-unobserved cleanup are
  not acknowledgements. `ResultHandle.cancel()` may be requested by a
  controller thread; it returns `None`, while the outcome retains the observed
  cancellation, transaction, and cleanup facts.
- Query bundles carry caller-held content, producer, and compatibility records.
  They are snapshots: source edits need a new compilation. Bundle loading and
  every execution attempt check current code identity. Bundle trust records
  are checked at load time; each execution needs fresh access and deployment
  premises.
- v7 saved workspaces provide ordinary save, R1 source-free re-read,
  fixed-snapshot verified export, R2 same-source recovery, local publication,
  narrow caller-owned unpublished-generation retirement, and relay to the
  local reference cooperative sink. `inspect_job()` is read-only recorded
  metadata and grants none of those authorities.
- The API remains alpha. Names, fields, error codes, and behavior may change
  in later alpha releases; existing compiler and CLI contracts remain separate.
  The CLI still has no database-execution command.

## Compatibility and retained data

The installed Pietto and ANTLR code identity is checked for compile, bundle
load, and execution. The `0.1.2` version update changes the CLI fallback version,
and the wider source tree can also change that identity. A bundle or saved-job
record made under `0.1.1` can therefore be refused under `0.1.2`. Pietto
preserves the original bytes and does not migrate them; use the matching old
environment when the old state must remain usable.

## Support and durability limits

Only CPython 3.13.13 on Linux x86-64, with the lock's exact artifacts on the
qualified integration host, has native evidence for all three routes. Windows
native execution is `NOTRUN`; offline Windows compiler-project checks do not
establish job, database, or platform support.

Public save creates v7 only, with no migration. A workspace permits one
coordinator at a time and refuses concurrent capture, recovery, or relay with
`RUNTIME_BUSY`. There is no public scheduler, general garbage collector,
age-based deletion, or general directory cleanup. `retire_generation` removes
only the caller-owned unpublished generation's latest-checkpoint root; it does
not delete files. Publication-owned retention is permanent.

R1 and verified export are source-free reads with compatible code, fresh
caller-held scalar trust, integrity, and reader protections. R2 is live
same-source recovery: it requalifies one caller-supplied compiled-source
requirement for every source in compiled order, including guarded and refined
sources. A saved close only resumes or awaits bounded cleanup; until it
settles, remote state is `UNKNOWN` and no acknowledgement is claimed.

## Included compiler and CLI repairs

- A single leading UTF-8 BOM is ignored without changing parsed AST or source
  locations; a second or non-leading BOM remains invalid, and the original
  UTF-8 byte budget still applies.
- When the terminal cannot encode CLI output, Pietto preserves the terminal's
  configured encoding and returns the established clear output-encoding error
  instead of silently replacing source or diagnostic text.
- A single-file relation name may be `table` or `schema.table` (MySQL uses the
  database position); each component is quoted independently. Empty components
  and names with more than one dot fail closed with `PIE-S2306`.
- Cross-family comparison operands fail closed with `PIE-S2105`; there is no
  implicit conversion. This does not change the existing SQL three-valued
  behavior for comparisons with `null`.

## Attribution and release boundary

`THIRD_PARTY_NOTICES.md` records unbundled runtime and execution dependencies
and separates wheel/sdist material from the GitHub source archive.
`LICENSES/SOURCES.md` records the retained original-text provenance. This is
an attribution record, not a legal conclusion.

Before publication, the release stage must inspect the exact accepted wheel,
sdist, and source archive against those per-channel notices. Independent
rebuilds may verify the accepted bytes but never replace them.
