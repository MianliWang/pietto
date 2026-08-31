"""Real-authored Project semantics to verified private Project IR observation."""

from __future__ import annotations

from dataclasses import dataclass, field

from pietto._project.model import ProjectSemanticResult
from pietto._project.project_ir_composition import (
    ProjectIRProjectPlan,
    build_project_ir_project_plan,
)
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_evaluation_context import (
    ProjectIREvaluationContextStage,
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_inspection import (
    ProjectIRInspection,
    ProjectIRInspectionProduct,
    build_project_ir_inspection,
    serialize_project_ir_inspection,
)
from pietto._project.project_ir_verification import (
    ProjectIRAnalysisBundle,
    ProjectIRVerificationResult,
    ProjectIRVerificationStatus,
    build_project_ir_analysis_bundle,
    verify_project_ir_stage,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRPipelineResult:
    """Exact connected products from one Project semantic result and allocation."""

    semantic_result: ProjectSemanticResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    project_plan: ProjectIRProjectPlan
    evaluation_context_stage: ProjectIREvaluationContextStage
    verification: ProjectIRVerificationResult
    analysis_bundle: ProjectIRAnalysisBundle
    inspection_product: ProjectIRInspectionProduct
    canonical_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.semantic_result) is not ProjectSemanticResult:
            raise TypeError("Project IR pipeline requires an exact semantic result.")
        semantic_facts = self.semantic_result.module_semantic_facts
        attribution = self.semantic_result.module_attribution_facts
        if semantic_facts is None or attribution is None:
            raise ValueError("Project IR pipeline requires retained Project roots.")
        if (
            type(self.starting_allocation) is not ProjectIRAllocationState
            or type(self.ending_allocation) is not ProjectIRAllocationState
            or type(self.project_plan) is not ProjectIRProjectPlan
            or type(self.evaluation_context_stage)
            is not ProjectIREvaluationContextStage
            or type(self.verification) is not ProjectIRVerificationResult
            or type(self.analysis_bundle) is not ProjectIRAnalysisBundle
            or type(self.inspection_product) is not ProjectIRInspectionProduct
        ):
            raise TypeError("Project IR pipeline requires exact stage products.")
        if (
            self.project_plan.semantic_facts is not semantic_facts
            or self.project_plan.attribution is not attribution
            or self.starting_allocation is not self.project_plan.starting_allocation
            or self.ending_allocation is not self.project_plan.ending_allocation
            or self.evaluation_context_stage.project_plan is not self.project_plan
            or self.verification.stage is not self.evaluation_context_stage
            or self.verification.status is not ProjectIRVerificationStatus.VERIFIED
            or self.verification.issues
            or self.analysis_bundle.verification is not self.verification
            or self.inspection_product.inspection.analysis_bundle
            is not self.analysis_bundle
        ):
            raise ValueError("Project IR pipeline products require exact continuity.")
        if type(self.canonical_bytes) is not bytes or (
            self.canonical_bytes != self.inspection_product.canonical_bytes
        ):
            raise ValueError("Project IR pipeline requires exact canonical bytes.")

    @property
    def inspection(self) -> ProjectIRInspection:
        """Return the exact retained private inspection."""

        return self.inspection_product.inspection


def build_project_ir_pipeline(
    *,
    semantic_result: ProjectSemanticResult,
    allocation: ProjectIRAllocationState,
) -> ProjectIRPipelineResult:
    """Build the published Slice 6-9 chain from exact authored semantics."""

    if type(semantic_result) is not ProjectSemanticResult:
        raise TypeError("Project IR pipeline requires an exact semantic result.")
    if type(allocation) is not ProjectIRAllocationState:
        raise TypeError("Project IR pipeline requires an exact allocation state.")
    semantic_facts = semantic_result.module_semantic_facts
    attribution = semantic_result.module_attribution_facts
    if semantic_facts is None or attribution is None:
        raise ValueError("Project IR pipeline requires retained Project roots.")
    if attribution._authority.semantic_facts is not semantic_facts:
        raise ValueError("Project IR pipeline requires exact attribution authority.")

    project_plan = build_project_ir_project_plan(
        semantic_facts=semantic_facts,
        attribution=attribution,
        allocation=allocation,
    )
    evaluation_context_stage = build_project_ir_evaluation_context_stage(project_plan)
    verification = verify_project_ir_stage(evaluation_context_stage)
    if (
        type(verification) is not ProjectIRVerificationResult
        or verification.status is not ProjectIRVerificationStatus.VERIFIED
        or verification.issues
    ):
        raise ValueError("Project IR pipeline integrity verification failed.")
    analysis_bundle = build_project_ir_analysis_bundle(verification)
    inspection_product = build_project_ir_inspection(analysis_bundle)
    canonical_bytes = serialize_project_ir_inspection(inspection_product.inspection)
    return ProjectIRPipelineResult(
        semantic_result=semantic_result,
        starting_allocation=allocation,
        ending_allocation=project_plan.ending_allocation,
        project_plan=project_plan,
        evaluation_context_stage=evaluation_context_stage,
        verification=verification,
        analysis_bundle=analysis_bundle,
        inspection_product=inspection_product,
        canonical_bytes=canonical_bytes,
    )
