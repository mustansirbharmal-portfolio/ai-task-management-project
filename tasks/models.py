"""
Task models and validation using Pydantic.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import date, datetime
import uuid


class TaskInput(BaseModel):
    """Input model for task validation."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=1, max_length=500)
    due_date: str = Field(...)
    estimated_hours: float = Field(..., ge=0.1, le=1000)
    importance: int = Field(..., ge=1, le=10)
    dependencies: List[str] = Field(default_factory=list)
    
    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        """Validate date format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('due_date must be in YYYY-MM-DD format')
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate title is not empty."""
        if not v or not v.strip():
            raise ValueError('title cannot be empty')
        return v.strip()


class TaskOutput(BaseModel):
    """Output model for analyzed task."""
    id: str
    title: str
    due_date: str
    estimated_hours: float
    importance: int
    dependencies: List[str]
    priority_score: float
    urgency_score: float
    importance_score: float
    effort_score: float
    blocking_score: float
    priority_level: str  # High, Medium, Low
    score_explanation: str
    is_overdue: bool
    days_until_due: int
    is_corporate: Optional[bool] = None
    is_urgent_task: Optional[bool] = None


class UserWeights(BaseModel):
    """User-configurable weights for scoring."""
    urgency_weight: float = Field(default=0.3, ge=0, le=1)
    importance_weight: float = Field(default=0.3, ge=0, le=1)
    effort_weight: float = Field(default=0.2, ge=0, le=1)
    blocking_weight: float = Field(default=0.2, ge=0, le=1)
    custom_weights_enabled: bool = Field(default=False)
    
    @field_validator('blocking_weight')
    @classmethod
    def validate_weights_sum(cls, v, info):
        """Validate that weights sum to approximately 1."""
        values = info.data
        total = values.get('urgency_weight', 0.3) + values.get('importance_weight', 0.3) + \
                values.get('effort_weight', 0.2) + v
        if abs(total - 1.0) > 0.01:
            raise ValueError(f'Weights must sum to 1.0, got {total}')
        return v


class FeedbackInput(BaseModel):
    """Model for user feedback on suggestions."""
    task_id: str
    helpful: bool
    feedback_text: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """Request model for analyze endpoint."""
    tasks: List[TaskInput]
    strategy: str = Field(default='smart_balance')  # fastest_wins, high_impact, deadline_driven, smart_balance
    weights: Optional[UserWeights] = None
    consider_weekends: bool = Field(default=True)
    
    @field_validator('strategy')
    @classmethod
    def validate_strategy(cls, v):
        """Validate sorting strategy."""
        valid_strategies = ['fastest_wins', 'high_impact', 'deadline_driven', 'smart_balance']
        if v not in valid_strategies:
            raise ValueError(f'strategy must be one of {valid_strategies}')
        return v
