"""Owned, reusable execution templates; each binding rederives compiler facts.

The syntax image is a private specialization, not a newly opened source file.
Original trusted bytes remain origin evidence and are never rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, replace
from typing import Any

from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
    with_project_single_match_requests,
)
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_verification import (
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from pietto._project.project_sql_plan import build_project_sql_plan
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto._project.project_sql_emission import EmissionArtifact, emit_project_sql
from pietto._project.project_sql_emission_parameters import value_valid
from pietto._project.project_single_match import ProjectSingleMatchAssessment

__all__: tuple[str, ...] = ()


class BindingError(ValueError):
    """Value-free category; compiler diagnostics must not disclose bind inputs."""


@dataclass(frozen=True, slots=True, eq=False)
class ExecutionSlot:
    ordinal: int
    tag: str
    original: Any = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class ExecutionTemplate:
    artifact: EmissionArtifact = field(repr=False)
    slots: tuple[ExecutionSlot, ...]
    _state: tuple = field(repr=False)
    guarded: Any = field(default=None, repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class ExecutionBinding:
    template: ExecutionTemplate = field(repr=False)
    values: tuple = field(repr=False)
    artifact: EmissionArtifact = field(repr=False)
    arguments: tuple = field(repr=False)
    _state: tuple = field(repr=False)
    guarded: Any = field(default=None, repr=False)


def prepare_template(artifact):
    from pietto._project import project_execution_binding_verification as check

    check.inspect(artifact)
    slots = tuple(
        ExecutionSlot(i, slot.tag.value, slot)
        for i, slot in enumerate(artifact.request.plan.literal_slots)
    )
    result = ExecutionTemplate(artifact, slots, check.template_state(artifact, slots))
    check.verify_template(result)
    return result


def _syntax_image(parsed, replacements):
    memo = {}

    def clone(node):
        if id(node) in memo:
            return memo[id(node)]
        if type(node) is tuple:
            return tuple(clone(item) for item in node)
        if (
            is_dataclass(node)
            and not isinstance(node, type)
            and type(node).__module__ == "pietto.ast_nodes"
        ):
            members = {f.name: clone(getattr(node, f.name)) for f in fields(node)}
            if id(node) in replacements:
                members["value"] = replacements[id(node)]
            result = replace(node, **members)
            memo[id(node)] = result
            return result
        return node

    inputs = tuple(replace(p, script=clone(p.script)) for p in parsed.parsed_inputs)

    def input_image(original):
        matches = tuple(i for i, p in enumerate(parsed.parsed_inputs) if p is original)
        if len(matches) != 1:
            raise BindingError("BINDING_MODULES")
        return inputs[matches[0]]

    modules = tuple(
        replace(
            m,
            parsed_input=input_image(m.parsed_input),
        )
        for m in parsed.modules
    )
    return replace(parsed, parsed_inputs=inputs, modules=modules), memo


def _requests(original, completed, image):
    """Rebind explicit request occurrences; proof owners run again afterwards."""
    from pietto._project.project_relationship_paths import ProjectRelationshipPathStep

    requests = []
    images = {}
    for request in original.single_match_requests:
        if id(request) in images:
            requests.append(images[id(request)])
            continue
        old = ProjectSingleMatchAssessment(
            root=original.effective_outputs, request=request
        )
        matches = tuple(
            c
            for c in completed.roots.join_conditions.entries
            if c.use.owner.definition is image[id(request.owner.definition)]
            and c.use.clause is image[id(request.use.clause)]
        )
        if len(matches) != 1 or old.condition is None or old.problems:
            raise BindingError("BINDING_OBLIGATION")
        condition = matches[0]
        path = condition.effective_use.path if request.path is not None else None
        hop = None
        if request.hop is not None:
            old_path = old.condition.effective_use.path
            if (
                isinstance(request.hop, ProjectRelationshipPathStep)
                and old_path is None
            ):
                raise BindingError("BINDING_OBLIGATION")
            old_hops = (
                (old_path.steps if old_path is not None else ())
                if isinstance(request.hop, ProjectRelationshipPathStep)
                else old.condition.use.step_uses
            )
            new_hops = (
                condition.effective_use.path.steps
                if isinstance(request.hop, ProjectRelationshipPathStep)
                else condition.use.step_uses
            )
            (position,) = tuple(i for i, h in enumerate(old_hops) if h is request.hop)
            hop = new_hops[position]
        new = replace(
            request,
            owner=condition.use.owner,
            use=condition.use,
            condition=condition if request.condition is not None else None,
            path=path,
            hop=hop,
            input_pairs=None,
        )
        if request.input_pairs is not None:
            assessment = ProjectSingleMatchAssessment(
                root=completed.effective_outputs, request=new
            )
            new = replace(new, input_pairs=assessment.input_pairs)
        images[id(request)] = new
        requests.append(new)
    return with_project_single_match_requests(completed, tuple(requests))


def _specialize(template, values):
    from pietto._project.project_execution_binding_verification import parse_root
    from pietto._project.project_scalar_meaning import acquire_scalar_meaning

    original = template.artifact.request
    replacements = {}
    for slot, value in zip(template.slots, values, strict=True):
        literal = id(slot.original.site.position.literal)
        # Each slot owns one leaf; sharing a leaf across distinct slot identities
        # would need a different syntax specialization, never last-writer-wins.
        if literal in replacements:
            raise BindingError("BINDING_SLOT_ALIAS")
        replacements[literal] = value
    parsed, image = _syntax_image(parse_root(template.artifact), replacements)
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    completed = _requests(original.verification.completed, completed, image)
    if not completed.ok:
        raise BindingError("BINDING_SEMANTICS")
    ir = build_project_query_block_ir(completed)
    bundle = build_project_query_block_ir_analysis_bundle(
        verify_project_query_block_ir(ir)
    )
    selected = tuple(
        owner
        for owner in ir.owners
        if owner.definition
        is image[id(original.verification.selected_owner.definition)]
    )
    if len(selected) != 1:
        raise BindingError("BINDING_OWNER")
    policy = original.verification.literal_policy
    plan = build_project_sql_plan(completed, bundle, selected[0], literal_policy=policy)
    verified = verify_project_sql_plan(
        plan, completed, bundle, selected[0], literal_policy=policy
    )
    if not verified.verified:
        raise BindingError("BINDING_PLAN")
    meaning = (
        acquire_scalar_meaning(verified)
        if original.scalar_meaning is not None
        else None
    )
    if template.guarded is not None:
        from pietto._project.project_guard_preparation import prepare_guarded

        return prepare_guarded(
            verified,
            original.accepted_bytes,
            target_request=original.target_request,
            scalar_meaning=meaning,
        )
    outcome = emit_project_sql(
        verified,
        original.accepted_bytes,
        target_request=original.target_request,
        scalar_meaning=meaning,
    )
    if outcome.status != "VERIFIED" or outcome.artifact is None:
        raise BindingError("BINDING_REPRESENTATION")
    return outcome.artifact


def bind_values(template, supplied):
    """Capture a complete ordered sequence of (exact slot, exact builtin value)."""
    from pietto._project import project_execution_binding_verification as check

    check.verify_template(template)
    if type(supplied) not in (tuple, list) or len(supplied) != len(template.slots):
        raise BindingError("BINDING_SLOTS")
    values = []
    for slot, pair in zip(template.slots, supplied, strict=True):
        if type(pair) not in (tuple, list) or len(pair) != 2 or pair[0] is not slot:
            raise BindingError("BINDING_SLOTS")
        if not value_valid(slot.tag, pair[1], template.artifact.request.family):
            raise BindingError(f"BINDING_VALUE:{slot.ordinal}:{slot.tag}")
        values.append(pair[1])
    captured = tuple(values)
    try:
        specialized = _specialize(template, captured) if captured else None
        guarded = (
            (specialized if captured else template.guarded)
            if template.guarded is not None
            else None
        )
        if guarded is not None:
            from pietto._project.project_guard_preparation import GuardedPreparation

            if type(guarded) is not GuardedPreparation:
                raise BindingError("BINDING_INVALID")
            artifact = guarded.artifact
        else:
            artifact = specialized if captured else template.artifact
            if type(artifact) is not EmissionArtifact:
                raise BindingError("BINDING_INVALID")
        arguments = check.native_arguments(artifact, captured)
        result = ExecutionBinding(template, captured, artifact, arguments, (), guarded)
        result = replace(result, _state=check.binding_state(result))
        check.verify_binding(result)
        return result
    except (ValueError, TypeError, AttributeError, KeyError, IndexError):
        raise BindingError("BINDING_INVALID") from None
