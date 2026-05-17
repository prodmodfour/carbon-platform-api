"""Usage sample ingestion business service."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from carbon_platform_api.repositories.usage_samples import (
    UsageSampleCreate,
    UsageSampleRecord,
)
from carbon_platform_api.schemas.carbon_calculations import (
    CarbonCalculationInput,
    CarbonCalculationResult,
)
from carbon_platform_api.schemas.usage_samples import UsageSampleIngestionRequest
from carbon_platform_api.services.carbon_calculations import (
    CarbonCalculationError,
    CarbonCalculationService,
)


class WorkspaceLookupRepositoryProtocol(Protocol):
    """Workspace persistence operations required by usage ingestion."""

    async def get(self, workspace_id: UUID) -> object | None:
        """Fetch a workspace by primary key, returning None when missing."""
        ...


class UsageSampleRepositoryProtocol(Protocol):
    """Usage sample persistence operations required by usage ingestion."""

    async def create(self, sample: UsageSampleCreate) -> UsageSampleRecord:
        """Persist one usage sample."""
        ...


class CarbonCalculationProtocol(Protocol):
    """Calculation operation required by usage ingestion."""

    def calculate(
        self,
        calculation_input: CarbonCalculationInput,
    ) -> CarbonCalculationResult:
        """Calculate a deterministic carbon estimate for one usage sample."""
        ...


class UsageSampleWorkspaceNotFoundError(LookupError):
    """Raised when a usage sample references a missing workspace."""


class InvalidUsageSampleError(ValueError):
    """Raised when a usage sample cannot be calculated or persisted safely."""


class UsageIngestionService:
    """Business operation for ingesting compute usage samples."""

    def __init__(
        self,
        *,
        workspace_repository: WorkspaceLookupRepositoryProtocol,
        usage_sample_repository: UsageSampleRepositoryProtocol,
        calculation_service: CarbonCalculationProtocol | None = None,
    ) -> None:
        """Create a service with small injectable abstractions."""
        self._workspace_repository = workspace_repository
        self._usage_sample_repository = usage_sample_repository
        self._calculation_service = calculation_service or CarbonCalculationService()

    async def ingest_usage_sample(
        self,
        *,
        workspace_id: UUID,
        request: UsageSampleIngestionRequest,
    ) -> UsageSampleRecord:
        """Validate, calculate, and persist one usage sample."""
        workspace = await self._workspace_repository.get(workspace_id)
        if workspace is None:
            raise UsageSampleWorkspaceNotFoundError(str(workspace_id))

        calculation_input = CarbonCalculationInput(
            resource_type=request.resource_type,
            region=request.region,
            usage_amount=request.usage_amount,
            usage_unit=request.usage_unit,
            carbon_intensity_grams_co2e_per_kwh=(
                request.carbon_intensity_grams_co2e_per_kwh
            ),
        )
        try:
            calculation_result = self._calculation_service.calculate(calculation_input)
        except CarbonCalculationError as exc:
            raise InvalidUsageSampleError(
                "Usage unit is not compatible with resource type."
            ) from exc

        sample_to_create = UsageSampleCreate(
            workspace_id=workspace_id,
            provider=request.provider,
            region=request.region,
            resource_type=request.resource_type.value,
            usage_amount=request.usage_amount,
            usage_unit=request.usage_unit.value,
            measured_at=request.measured_at,
            normalized_usage_amount=calculation_result.normalized_usage_amount,
            normalized_usage_unit=calculation_result.normalized_usage_unit.value,
            energy_kwh=calculation_result.energy_kwh,
            carbon_intensity_grams_co2e_per_kwh=(
                calculation_result.carbon_intensity_grams_co2e_per_kwh
            ),
            estimated_grams_co2e=calculation_result.estimated_grams_co2e,
            factor_source=calculation_result.factor_source,
        )
        return await self._usage_sample_repository.create(sample_to_create)
