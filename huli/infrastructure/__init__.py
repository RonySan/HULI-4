"""Adaptadores técnicos e configuração da Huli."""

from huli.infrastructure.applications import (
    ApplicationLaunchError,
    ApplicationLauncher,
    InstalledApplication,
)
from huli.infrastructure.config import Settings, load_settings
from huli.infrastructure.database import SQLiteDatabase
from huli.infrastructure.logging import configure_logging
from huli.infrastructure.persistence import EventRepository, Interaction, InteractionRepository, RuntimeRecorder
from huli.infrastructure.productivity import AppointmentRecord, AppointmentRepository, TaskRecord, TaskRepository

__all__ = ["ApplicationLaunchError", "ApplicationLauncher", "AppointmentRecord", "AppointmentRepository", "EventRepository", "InstalledApplication", "Interaction", "InteractionRepository", "RuntimeRecorder", "SQLiteDatabase", "Settings", "TaskRecord", "TaskRepository", "configure_logging", "load_settings"]
