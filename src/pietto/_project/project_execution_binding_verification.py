"""Independent correspondence for private bindings; never rebuilds a binding."""

from dataclasses import fields, is_dataclass

from pietto.ast_nodes import LiteralExpr
from pietto._project.project_sql_emission import (
    EmissionArtifact,
    CompiledEmissionArtifact,
)
from pietto._project.project_sql_emission_inspection import inspect_project_sql_emission
from pietto._project.project_sql_emission_parameters import PHYSICAL, value_valid
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_execution_template import (
    BindingError,
    ExecutionTemplate,
    ExecutionParameter,
    ExecutionSlot,
    ExecutionBinding,
)
from pietto._project.project_verification_scope import entry

__all__: tuple[str, ...] = ()


def atom(value):
    return (type(value), value.hex() if type(value) is float else value)


def inspect(artifact, guarded=None):
    if guarded is None and type(artifact) not in (
        EmissionArtifact,
        CompiledEmissionArtifact,
    ):
        raise BindingError("BINDING_ARTIFACT")
    try:
        if guarded is not None:
            from pietto._project.project_guard_preparation import inspect_pending

            return inspect_pending(guarded, artifact)
        return inspect_project_sql_emission(artifact, artifact.request)
    except (ValueError, TypeError, AttributeError, KeyError, IndexError):
        raise BindingError("BINDING_ARTIFACT") from None


def parse_root(artifact):
    return artifact.request.verification.completed.semantic_result.module_attribution_facts._authority.parse_result


def syntax_state(node):
    if type(node) is tuple:
        return tuple(syntax_state(v) for v in node)
    if is_dataclass(node) and type(node).__module__ == "pietto.ast_nodes":
        return (
            type(node),
            id(node),
            tuple((f.name, syntax_state(getattr(node, f.name))) for f in fields(node)),
        )
    return atom(node)


def template_state(artifact, slots, guarded=None, *, parameters=()):
    request = artifact.request
    header = tuple(
        (p, p.ordinal, p.name, p.tag, p.nullable, p.original) for p in parameters
    )
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    if type(request) is CompiledPreparedEmission:
        root = request.verification.completed.root
        return (
            "compiled",
            artifact,
            request,
            request.verification,
            root,
            root.expected_pin,
            request.accepted_bytes,
            request.normalized_bytes,
            request.family,
            request.release,
            request.plan.literal_policy,
            tuple((s, s.ordinal, s.tag, s.original, s.original.site) for s in slots),
            guarded,
            header,
        )
    parsed = parse_root(artifact)
    return (
        artifact,
        request,
        request.verification,
        request.accepted_bytes,
        request.normalized_bytes,
        request.family,
        request.release,
        request.target_request,
        request.scalar_meaning,
        request.verification.selected_owner,
        request.verification.literal_policy,
        parsed,
        parsed.inputs,
        parsed.selected_input_index,
        parsed.trusted_source_snapshots,
        tuple((m, m.project_input, m.parsed_input) for m in parsed.modules),
        tuple(syntax_state(p.script) for p in parsed.parsed_inputs),
        tuple((s, s.ordinal, s.tag, s.original, s.original.site) for s in slots),
        tuple(request.verification.completed.single_match_requests),
        guarded,
        header,
    )


@entry
def verify_template(template):
    if type(template) is not ExecutionTemplate or type(template.slots) is not tuple:
        raise BindingError("BINDING_TEMPLATE")
    inspect(template.artifact, template.guarded)
    slots = template.artifact.request.plan.literal_slots
    if len(slots) != len(template.slots) or any(
        type(s) is not ExecutionSlot
        or type(s.ordinal) is not int
        or s.ordinal != i
        or s.original is not original
        or s.tag != original.tag.value
        for i, (s, original) in enumerate(zip(template.slots, slots, strict=True))
    ):
        raise BindingError("BINDING_INVENTORY")
    from pietto._project.project_execution_template import template_parameters

    header = template_parameters(template.artifact)
    if type(template.parameters) is not tuple or len(template.parameters) != len(
        header
    ):
        raise BindingError("BINDING_INVENTORY")
    for actual, expected in zip(template.parameters, header, strict=True):
        if (
            type(actual) is not ExecutionParameter
            or actual.original is not expected.original
            or (actual.ordinal, actual.name, actual.tag, actual.nullable)
            != (expected.ordinal, expected.name, expected.tag, expected.nullable)
        ):
            raise BindingError("BINDING_INVENTORY")
    if (
        template_state(
            template.artifact,
            template.slots,
            template.guarded,
            parameters=template.parameters,
        )
        != template._state
    ):
        raise BindingError("BINDING_TEMPLATE_STATE")


def use_owner(use):
    """A native occurrence's owner: a bind-safe slot or a header parameter."""
    return use.slot if use.parameter is None else use.parameter


def use_tag(use):
    """The Pietto tag of a native occurrence's owner."""
    return use.slot.tag.value if use.parameter is None else use.parameter.tag


def native_arguments(artifact, values, parameters=()):
    """Read actual use occurrences, preserving PG reuse and MySQL multiplicity.

    ``values`` follow the literal slots and ``parameters`` the header; a
    header parameter bound to None sends a typed NULL through its anchor."""
    slots = artifact.request.plan.literal_slots
    header = artifact.request.plan.parameters
    if type(values) is not tuple or len(values) != len(slots):
        raise BindingError("BINDING_VALUES")
    if type(parameters) is not tuple or len(parameters) != len(header):
        raise BindingError("BINDING_VALUES")
    arguments, seen = [], []
    family = artifact.request.family
    for ordinal, use in enumerate(artifact.parameter_uses):
        if use.ordinal != ordinal:
            raise BindingError("BINDING_USES")
        if use.parameter is not None:
            matches = tuple(i for i, p in enumerate(header) if use.parameter is p)
            if len(matches) != 1 or use.slot is not None:
                raise BindingError("BINDING_USES")
            owner, value = header[matches[0]], parameters[matches[0]]
            tag = owner.tag
        else:
            matches = tuple(i for i, slot in enumerate(slots) if use.slot is slot)
            if len(matches) != 1:
                raise BindingError("BINDING_USES")
            owner, value = slots[matches[0]], values[matches[0]]
            tag = owner.tag.value
        if use.physical_type != PHYSICAL[family][tag]:
            raise BindingError("BINDING_ANCHOR")
        if family == "mysql" or not any(s is owner for s in seen):
            seen.append(owner)
            arguments.append(
                int(value)
                if family == "mysql" and tag == "Bool" and value is not None
                else value
            )
            server_index = len(arguments)
        else:
            server_index = next(i + 1 for i, s in enumerate(seen) if s is owner)
        if type(use.server_index) is not int or use.server_index != server_index:
            raise BindingError("BINDING_USES")
    return tuple(arguments)


def artifact_values(artifact):
    """The slot and header values an artifact was derived with.

    An unbound template (a compiled root emitted without parameter values, or
    a live parameterized emission) has no values to send."""
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    request = artifact.request
    values = tuple(s.site.position.literal.value for s in request.plan.literal_slots)
    if not request.plan.parameters:
        return values, ()
    bound = (
        request.verification.completed.parameters
        if type(request) is CompiledPreparedEmission
        else None
    )
    if type(bound) is not tuple:
        raise BindingError("BINDING_UNBOUND")
    return values, bound


def artifact_arguments(artifact):
    """Native arguments for an artifact's own values, in server order."""
    return native_arguments(artifact, *artifact_values(artifact))


def occurrence_value(artifact, use):
    """The value one native occurrence sends (before any MySQL Bool widening)."""
    values, parameters = artifact_values(artifact)
    if use.parameter is not None:
        (index,) = tuple(
            i
            for i, p in enumerate(artifact.request.plan.parameters)
            if p is use.parameter
        )
        return parameters[index]
    (index,) = tuple(
        i for i, s in enumerate(artifact.request.plan.literal_slots) if s is use.slot
    )
    return values[index]


def binding_state(binding):
    return (
        binding.instance_reference,
        binding.guarded,
        binding.template,
        binding.artifact,
        binding.artifact.request,
        tuple(atom(v) for v in binding.values),
        tuple(atom(v) for v in binding.parameters),
        tuple(atom(v) for v in binding.arguments),
        tuple(
            (u, u.slot, u.parameter, u.original, u.physical_type, u.server_index)
            for u in binding.artifact.parameter_uses
        ),
    )


def _syntax_correspondence(template, artifact, values):
    old, new = parse_root(template.artifact), parse_root(artifact)
    replacements = {
        id(s.original.site.position.literal): v
        for s, v in zip(template.slots, values, strict=True)
    }
    if len(replacements) != len(template.slots):
        raise BindingError("BINDING_SLOT_ALIAS")
    mapped, reverse = {}, {}

    def visit(left, right):
        if type(left) is not type(right):
            raise BindingError("BINDING_SYNTAX")
        if type(left) is tuple:
            if len(left) != len(right):
                raise BindingError("BINDING_SYNTAX")
            for a, b in zip(left, right, strict=True):
                visit(a, b)
        elif is_dataclass(left) and type(left).__module__ == "pietto.ast_nodes":
            if id(left) in mapped:
                if mapped[id(left)] is not right:
                    raise BindingError("BINDING_SYNTAX_ALIAS")
                return
            if left is right or id(right) in reverse:
                raise BindingError("BINDING_SYNTAX_ALIAS")
            mapped[id(left)] = right
            reverse[id(right)] = left
            for member in fields(left):
                a, b = getattr(left, member.name), getattr(right, member.name)
                if (
                    type(left) is LiteralExpr
                    and member.name == "value"
                    and id(left) in replacements
                ):
                    if atom(b) != atom(replacements[id(left)]):
                        raise BindingError("BINDING_LITERAL")
                else:
                    visit(a, b)
        elif atom(left) != atom(right):
            raise BindingError("BINDING_STRUCTURE")

    if old is new or len(old.parsed_inputs) != len(new.parsed_inputs):
        raise BindingError("BINDING_PARSE_ROOT")
    for member in fields(old):
        if member.name not in ("parsed_inputs", "modules") and getattr(
            old, member.name
        ) is not getattr(new, member.name):
            raise BindingError("BINDING_ORIGIN")
    for a, b in zip(old.parsed_inputs, new.parsed_inputs, strict=True):
        if a.path != b.path:
            raise BindingError("BINDING_ORIGIN")
        visit(a.script, b.script)
    if len(old.modules) != len(new.modules):
        raise BindingError("BINDING_MODULES")
    for a, b in zip(old.modules, new.modules, strict=True):
        for member in fields(a):
            if member.name == "parsed_input":
                pairs = tuple(
                    i for i, p in enumerate(old.parsed_inputs) if p is a.parsed_input
                )
                if len(pairs) != 1 or b.parsed_input is not new.parsed_inputs[pairs[0]]:
                    raise BindingError("BINDING_MODULES")
            elif getattr(a, member.name) is not getattr(b, member.name):
                raise BindingError("BINDING_MODULES")
    return mapped


def _obligations(before, after, image):
    from pietto._project.project_relationship_paths import ProjectRelationshipPathStep
    from pietto._project.project_single_match import ProjectSingleMatchAssessment

    old, new = before.single_match_requests, after.single_match_requests
    if len(old) != len(new):
        raise BindingError("BINDING_OBLIGATIONS")
    images, reverse = {}, {}
    for a, b in zip(old, new, strict=True):
        if (id(a) in images and images[id(a)] is not b) or (
            id(b) in reverse and reverse[id(b)] is not a
        ):
            raise BindingError("BINDING_OBLIGATION_ALIAS")
        images[id(a)], reverse[id(b)] = b, a
        x = ProjectSingleMatchAssessment(root=before.effective_outputs, request=a)
        y = ProjectSingleMatchAssessment(root=after.effective_outputs, request=b)
        if (
            a is b
            or x.problems
            or y.problems
            or b.owner.authored is not image[id(a.owner.authored)]
            or b.use.clause is not image[id(a.use.clause)]
            or b.scope is not a.scope
            or b.unit is not a.unit
            or (a.condition is None) != (b.condition is None)
            or (a.path is None) != (b.path is None)
            or (a.input_pairs is None) != (b.input_pairs is None)
            or type(a.hop) is not type(b.hop)
        ):
            raise BindingError("BINDING_OBLIGATIONS")
        if a.hop is not None:
            if x.condition is None or y.condition is None:
                raise BindingError("BINDING_OBLIGATIONS")
            x_path, y_path = (
                x.condition.effective_use.path,
                y.condition.effective_use.path,
            )
            if isinstance(a.hop, ProjectRelationshipPathStep) and (
                x_path is None or y_path is None
            ):
                raise BindingError("BINDING_OBLIGATIONS")
            aa = (
                (x_path.steps if x_path is not None else ())
                if isinstance(a.hop, ProjectRelationshipPathStep)
                else x.condition.use.step_uses
            )
            bb = (
                (y_path.steps if y_path is not None else ())
                if isinstance(b.hop, ProjectRelationshipPathStep)
                else y.condition.use.step_uses
            )
            if tuple(i for i, h in enumerate(aa) if h is a.hop) != tuple(
                i for i, h in enumerate(bb) if h is b.hop
            ):
                raise BindingError("BINDING_OBLIGATIONS")


@entry
def verify_binding(binding):
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    if type(binding) is not ExecutionBinding:
        raise BindingError("BINDING_AUTHORITY")
    if (
        type(binding.instance_reference) is not str
        or not binding.instance_reference.startswith("pietto-binding-v1:")
        or len(binding.instance_reference) != 50
        or any(c not in "0123456789abcdef" for c in binding.instance_reference[18:])
    ):
        raise BindingError("BINDING_INSTANCE_REFERENCE")
    verify_template(binding.template)
    template, artifact, values = binding.template, binding.artifact, binding.values
    if (template.guarded is None) != (binding.guarded is None):
        raise BindingError("BINDING_GUARDED_CONTEXT")
    inspect(artifact, binding.guarded)
    if type(values) is not tuple or len(values) != len(template.slots):
        raise BindingError("BINDING_VALUES")
    for s, v in zip(template.slots, values, strict=True):
        if not value_valid(s.tag, v, template.artifact.request.family):
            raise BindingError("BINDING_VALUE")
    named = binding.parameters
    if type(named) is not tuple or len(named) != len(template.parameters):
        raise BindingError("BINDING_PARAMETERS")
    for p, v in zip(template.parameters, named, strict=True):
        if not (
            p.nullable
            if v is None
            else value_valid(p.tag, v, template.artifact.request.family)
        ):
            raise BindingError("BINDING_PARAMETERS")
    if template.parameters and artifact.rendered.sql != template.artifact.rendered.sql:
        # A binding never changes the statement: only its arguments differ.
        raise BindingError("BINDING_TEMPLATE_BYTES")
    if not values and not template.parameters:
        if artifact is not template.artifact:
            raise BindingError("BINDING_PARAMETERLESS")
    elif type(artifact.request) is CompiledPreparedEmission:
        _compiled_correspondence(template, artifact, values, named)
    else:
        image = _syntax_correspondence(template, artifact, values)
        a, b = template.artifact.request, artifact.request
        from pietto._project.project_sql_emission_contract import PreparedEmission

        if type(a) is not PreparedEmission or type(b) is not PreparedEmission:
            raise BindingError("BINDING_CONTEXT")
        if (
            b.accepted_bytes != a.accepted_bytes
            or b.target_request is not a.target_request
            or b.verification.literal_policy is not a.verification.literal_policy
            or b.verification.selected_owner.authored
            is not image[id(a.verification.selected_owner.authored)]
            or (a.scalar_meaning is None) != (b.scalar_meaning is None)
        ):
            raise BindingError("BINDING_CONTEXT")
        _obligations(a.verification.completed, b.verification.completed, image)
        old, new = a.plan.literal_slots, b.plan.literal_slots
        if len(old) != len(new) or len(artifact.fixed_values) != len(values):
            raise BindingError("BINDING_INVENTORY")
        for x, y, fixed, value in zip(
            old, new, artifact.fixed_values, values, strict=True
        ):
            p, q = x.site.position, y.site.position
            if (
                x.tag is not y.tag
                or p.role is not q.role
                or q.literal is not image[id(p.literal)]
                or q.owner.authored is not image[id(p.owner.authored)]
                or len(p.ancestry) != len(q.ancestry)
                or any(
                    image[id(u)] is not v or i != j
                    for (u, i), (v, j) in zip(p.ancestry, q.ancestry, strict=True)
                )
                or fixed.slot is not y
                or atom(fixed.value) != atom(value)
            ):
                raise BindingError("BINDING_SITE")
        # Native uses are verified upstream in this call, then matched to original
        # owned slots and occurrence positions, not text or equal-looking values.
        au, bu = template.artifact.parameter_uses, artifact.parameter_uses
        if len(au) != len(bu):
            raise BindingError("BINDING_USES")
        for x, y in zip(au, bu, strict=True):
            if (
                tuple(i for i, s in enumerate(old) if s is x.slot)
                != tuple(i for i, s in enumerate(new) if s is y.slot)
                or x.ordinal != y.ordinal
                or x.server_index != y.server_index
                or x.physical_type != y.physical_type
            ):
                raise BindingError("BINDING_USES")
    if (
        type(binding.arguments) is not tuple
        or tuple(atom(v) for v in binding.arguments)
        != tuple(atom(v) for v in native_arguments(artifact, values, named))
        or binding_state(binding) != binding._state
    ):
        raise BindingError("BINDING_STATE")


def _compiled_correspondence(template, artifact, values, named=()):
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    old, new = template.artifact.request, artifact.request
    derived = new.verification.completed.parameters
    if (
        type(old) is not CompiledPreparedEmission
        or type(new) is not CompiledPreparedEmission
        or new.verification.completed.root is not old.verification.completed.root
        or old.verification.completed.parameters is not None
        or (
            derived is not None
            if not template.parameters
            else type(derived) is not tuple
            or tuple(atom(v) for v in derived) != tuple(atom(v) for v in named)
        )
        or tuple(atom(v) for v in new.verification.completed.values)
        != tuple(atom(v) for v in values)
        or new.accepted_bytes != old.accepted_bytes
        or new.normalized_bytes != old.normalized_bytes
        or (new.family, new.release) != (old.family, old.release)
        or new.plan.literal_policy is not old.plan.literal_policy
        or new.plan.scope is old.plan.scope
    ):
        raise BindingError("BINDING_COMPILED_CONTEXT")
    previous, current = old.plan.literal_slots, new.plan.literal_slots
    if len(previous) != len(current) or len(artifact.fixed_values) != len(values):
        raise BindingError("BINDING_INVENTORY")
    for a, b, fixed, value in zip(
        previous, current, artifact.fixed_values, values, strict=True
    ):
        if (
            a is b
            or a.tag is not b.tag
            or (a.ref.kind, a.ref.position) != (b.ref.kind, b.ref.position)
            or (a.site.ref.kind, a.site.ref.position)
            != (b.site.ref.kind, b.site.ref.position)
            or a.site.position.role is not b.site.position.role
            or a.site.position.ancestry != b.site.position.ancestry
            or fixed.slot is not b
            or atom(fixed.value) != atom(value)
            or a.site.position.literal is b.site.position.literal
        ):
            raise BindingError("BINDING_COMPILED_SITE")
    before, after = template.artifact.parameter_uses, artifact.parameter_uses
    if len(before) != len(after):
        raise BindingError("BINDING_USES")
    header_before = old.plan.parameters
    header_after = new.plan.parameters
    if len(header_before) != len(header_after):
        raise BindingError("BINDING_USES")
    for a, b in zip(before, after, strict=True):
        if (
            tuple(i for i, s in enumerate(previous) if s is a.slot)
            != tuple(i for i, s in enumerate(current) if s is b.slot)
            or tuple(i for i, p in enumerate(header_before) if p is a.parameter)
            != tuple(i for i, p in enumerate(header_after) if p is b.parameter)
            or (a.ordinal, a.server_index, a.physical_type)
            != (
                b.ordinal,
                b.server_index,
                b.physical_type,
            )
        ):
            raise BindingError("BINDING_USES")
    if template.parameters:
        _discharged(template, artifact, named)


def _int_range_discharged(image, family, named):
    """A bound Int result has one exact range inside its carrier."""
    realization = image.realization
    bounds = rows.int_bounds(realization)
    limits = rows.signed_range(realization.storage)
    return (
        not realization.binding
        and bounds is not None
        and limits is not None
        and realization.proven_int_range == bounds
        and limits[0] <= bounds[0] <= bounds[1] <= limits[1]
    )


def _text_width_discharged(image, family, named):
    """A bound Text result has an exact width."""
    realization = image.realization
    width = realization.domain.get("max_characters")
    return (
        realization.tag == "Text"
        and not realization.binding
        and type(width) is int
        and width >= 0
    )


# Closed: a template obligation whose kind has no check here never binds.
BINDING_CHECKS = {
    rows.INT_RANGE_OBLIGATION: _int_range_discharged,
    rows.TEXT_WIDTH_OBLIGATION: _text_width_discharged,
}


def _discharged(template, artifact, named):
    """Every deferred check of the template holds for the re-derived binding."""
    from pietto._project.project_sql_emission_ast import (
        row_binding_obligations,
        row_value_roots,
    )

    def nodes(source):
        return tuple(
            node
            for value in row_value_roots(source.ast)
            for node in rows.rendered_value_nodes(value)
        )

    before, after = nodes(template.artifact), nodes(artifact)
    if len(before) != len(after) or any(
        type(a) is not type(b) for a, b in zip(before, after, strict=True)
    ):
        raise BindingError("BINDING_OBLIGATIONS")
    images = {id(a): b for a, b in zip(before, after, strict=True)}
    family = artifact.request.family
    for node in row_binding_obligations(template.artifact.ast):
        kind = node.realization.obligation
        check = None if kind is None else BINDING_CHECKS.get(kind)
        if check is None:
            raise BindingError("BINDING_OBLIGATION_KIND")
        image = images.get(id(node))
        if image is None or not check(image, family, named):
            raise BindingError("BINDING_OBLIGATION")
