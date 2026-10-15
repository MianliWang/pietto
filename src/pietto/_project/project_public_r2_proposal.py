"""Unexported common preparation for either explicit public R2 carrier shape."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import weakref

from pietto._project.project_execution_source import (
    RetainedSourceRequirement,
    verify_requirement,
)
from pietto._project.project_refinement import (
    check_live_r2_refinement,
    prepare_live_r2_refinement,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class R2SourceInput:
    """One caller declaration. It grants no authority until native admission."""

    namespace: str
    name: str
    provider: str
    version: str
    revision: str
    registry_namespace: str
    registry_name: str
    definition: str = field(repr=False)
    token_columns: tuple[str, ...]
    role: str
    provider_guarantee: str


@dataclass(frozen=True, slots=True, eq=False, weakref_slot=True)
class LiveR2Preparation:
    refinement: Any = field(repr=False)
    witness: Any = field(repr=False)
    template: Any = field(repr=False)


_LIVE_R2_PREPARATIONS: weakref.WeakSet[LiveR2Preparation] = weakref.WeakSet()


def retained_requirements(artifact, inputs):
    """Bind complete ordered caller declarations to this artifact's own sources."""
    sources = artifact.request.sources
    if type(inputs) is not tuple or len(inputs) != len(sources):
        raise ValueError("PUBLIC_R2_SOURCE_CLOSURE")
    requirements = []
    for supplied, source in zip(inputs, sources, strict=True):
        if type(supplied) is not R2SourceInput or (
            supplied.namespace,
            supplied.name,
        ) != (source.namespace, source.name):
            raise ValueError("PUBLIC_R2_SOURCE_ORDER")
        requirement = RetainedSourceRequirement(
            source,
            supplied.provider,
            supplied.version,
            supplied.revision,
            supplied.registry_namespace,
            supplied.registry_name,
            supplied.definition,
            supplied.token_columns,
            supplied.role,
            supplied.provider_guarantee,
        )
        verify_requirement(requirement, sources, family=artifact.request.family)
        requirements.append(requirement)
    return tuple(requirements)


def prepare_live_refinement(query, binding, inputs):
    """Fix the R2 tie policy without exposing a generic refinement-plan object."""
    if (
        getattr(query, "origin", None) != "live"
        or getattr(query, "_template", None) is not binding.template
    ):
        raise ValueError("PUBLIC_R2_LIVE_QUERY")
    prepared = _prepare_for_template(binding, inputs, query._template)
    _LIVE_R2_PREPARATIONS.add(prepared)
    return prepared


def check_live_refinement(query, inputs):
    """The checks of `prepare_live_refinement` that read no bound value, in
    its order, for a restatement that has no binding yet (recover)."""
    if getattr(query, "origin", None) != "live":
        raise ValueError("PUBLIC_R2_LIVE_QUERY")
    template = query._template
    check_live_r2_refinement(template, retained_requirements(template.artifact, inputs))


def _prepare_for_template(binding, inputs, template, *, reanchor=False):
    """Rebind declarations only through one current live-template authority."""
    artifact = binding.artifact
    requirements = retained_requirements(artifact, inputs)
    refinement, witness = prepare_live_r2_refinement(
        template, binding, requirements, reanchor=reanchor
    )
    return LiveR2Preparation(refinement, witness, template)


def prepare_refinement_for_binding(binding, inputs, *, authority, reanchor=False):
    """Rebind only an authority issued by the public live-query entry."""
    if (
        type(authority) is not LiveR2Preparation
        or authority not in _LIVE_R2_PREPARATIONS
    ):
        raise ValueError("PUBLIC_R2_AUTHORITY")
    return _prepare_for_template(binding, inputs, authority.template, reanchor=reanchor)
