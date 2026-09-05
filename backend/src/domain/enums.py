"""Status vocabularies.

These were free-form strings scattered across modules, so a typo would reach
the database unnoticed. The column types stay ``String`` — turning them into
database enums would be a schema change with no behavioural benefit here — but
every producer and consumer now names the same constant.
"""

from enum import StrEnum


class ProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ScanStatus(StrEnum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    FAILED = "failed"


class AlertLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
