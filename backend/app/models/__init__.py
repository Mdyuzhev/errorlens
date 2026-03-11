"""Models package — re-exports all SQLAlchemy and Pydantic models."""

# Base
from app.models.article import Article, ArticleFolder, ArticleImage
from app.models.base import Base, generate_uuid
from app.models.misc import (
    AutomationRule,
    AutomationRun,
    EntityLink,
    GitLabConnection,
    Notification,
    SavedFilter,
    TestRun,
)

# Domain models
from app.models.project import Folder, Project, ProjectMember
from app.models.session import AnalysisResult, Session, SessionData
from app.models.task import (
    StatusTransition,
    Task,
    TaskActivity,
    TaskComment,
    TaskRelation,
    TaskStatus,
    TaskType,
)
from app.models.testcase import TestCase, TestCaseFolder
from app.models.testplan import TestPlan, TestPlanCase, TestPlanRun, TestPlanRunResult
from app.models.user import User

# Pydantic models
from app.models_pydantic import (
    AnalyzeRequest,
    AnalyzeResponse,
    ConsoleLogEntry,
    DetectedVariable,
    ExportPostmanRequest,
    ExportPostmanResponse,
    JSException,
    NetworkError,
    RecordedRequest,
    RequestAssertion,
    SessionAnalysisRequest,
    SessionAnalysisResponse,
)

__all__ = [
    # Base
    "Base",
    "generate_uuid",
    # Project
    "Project",
    "Folder",
    "ProjectMember",
    # Session
    "Session",
    "SessionData",
    "AnalysisResult",
    # TestCase
    "TestCase",
    "TestCaseFolder",
    # Task
    "TaskType",
    "TaskStatus",
    "StatusTransition",
    "Task",
    "TaskComment",
    "TaskActivity",
    "TaskRelation",
    # Article
    "ArticleFolder",
    "Article",
    "ArticleImage",
    # TestPlan
    "TestPlan",
    "TestPlanCase",
    "TestPlanRun",
    "TestPlanRunResult",
    # Misc
    "TestRun",
    "Notification",
    "GitLabConnection",
    "EntityLink",
    "SavedFilter",
    "AutomationRule",
    "AutomationRun",
    # User
    "User",
    # Pydantic
    "AnalyzeRequest",
    "AnalyzeResponse",
    "ConsoleLogEntry",
    "DetectedVariable",
    "ExportPostmanRequest",
    "ExportPostmanResponse",
    "JSException",
    "NetworkError",
    "RecordedRequest",
    "RequestAssertion",
    "SessionAnalysisRequest",
    "SessionAnalysisResponse",
]
