"""
URL configuration for tasks API.
"""

from django.urls import path
from .views import (
    AnalyzeTasksView,
    SuggestTasksView,
    EisenhowerMatrixView,
    UserWeightsView,
    FeedbackView,
    LearnWeightsView,
    TasksListView
)

urlpatterns = [
    path('tasks/', TasksListView.as_view(), name='tasks-list'),
    path('tasks/analyze/', AnalyzeTasksView.as_view(), name='analyze-tasks'),
    path('tasks/suggest/', SuggestTasksView.as_view(), name='suggest-tasks'),
    path('tasks/matrix/', EisenhowerMatrixView.as_view(), name='eisenhower-matrix'),
    path('tasks/weights/', UserWeightsView.as_view(), name='user-weights'),
    path('tasks/feedback/', FeedbackView.as_view(), name='feedback'),
    path('tasks/learn/', LearnWeightsView.as_view(), name='learn-weights'),
]
