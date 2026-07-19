"""Cloud Platform Foundation (Phase 17).

Architectural foundation ONLY: contracts, models, registry, metadata,
serialization, and validation for a future cloud-hosted deployment. This
phase is completely OFFLINE -- it implements no authentication, no cloud
synchronization, no networking, no APIs, no background workers, no
databases, no websocket communication, no remote execution, and calls no
external service. It is a management layer: it stores references (ids,
names, checksums) to artifacts produced by other engines, and never
inspects, imports, or depends on Backtesting, Optimization, Replay,
Validation, Research, Portfolio, or EA Generator internals.
"""

from app.cloud_platform.compiler import CloudCompiler
from app.cloud_platform.context import CloudPlatformContext, ProjectDraft, SnapshotDraft
from app.cloud_platform.engine import CloudPlatformEngine
from app.cloud_platform.exceptions import (
    CloudConfigurationError,
    CloudDisabledError,
    CloudNotFoundError,
    CloudPlatformError,
    CloudRegistrationError,
    CloudValidationError,
)
from app.cloud_platform.metadata import CLOUD_PLATFORM_RESULT_VERSION, CLOUD_SCHEMA_VERSION, WorkspaceMetadata
from app.cloud_platform.models import (
    ArtifactReference,
    CloudBuild,
    CloudProject,
    CloudReport,
    CloudSnapshot,
    CloudStatistics,
    CloudWorkspace,
    DatasetReference,
    ProjectReference,
    ReferenceKind,
    ResearchReference,
)
from app.cloud_platform.registry import CloudRegistry
from app.cloud_platform.report import CloudPlatformReport, build_executive_report
from app.cloud_platform.runner import BaseCloudRunner, CloudPlatformRunner, CloudSession, SessionStatus
from app.cloud_platform.serializer import CloudSerializer
from app.cloud_platform.statistics import aggregate_registry_statistics, compute_statistics
from app.cloud_platform.validator import CloudCheckResult, CloudIssue, CloudValidator

__all__ = [
    "CloudPlatformEngine",
    "CloudPlatformRunner",
    "BaseCloudRunner",
    "CloudSession",
    "SessionStatus",
    "CloudPlatformContext",
    "ProjectDraft",
    "SnapshotDraft",
    "CloudCompiler",
    "CloudValidator",
    "CloudCheckResult",
    "CloudIssue",
    "CloudSerializer",
    "CloudRegistry",
    "CloudPlatformReport",
    "build_executive_report",
    "compute_statistics",
    "aggregate_registry_statistics",
    "WorkspaceMetadata",
    "CLOUD_PLATFORM_RESULT_VERSION",
    "CLOUD_SCHEMA_VERSION",
    "ReferenceKind",
    "ProjectReference",
    "ResearchReference",
    "DatasetReference",
    "ArtifactReference",
    "CloudProject",
    "CloudSnapshot",
    "CloudWorkspace",
    "CloudStatistics",
    "CloudBuild",
    "CloudReport",
    "CloudPlatformError",
    "CloudConfigurationError",
    "CloudValidationError",
    "CloudNotFoundError",
    "CloudDisabledError",
    "CloudRegistrationError",
]
