"""
API Views for Task Analyzer.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pydantic import ValidationError
import json
import uuid

from .models import TaskInput, AnalyzeRequest, UserWeights, FeedbackInput
from .scoring import TaskAnalyzer, TaskScorer
from .cosmos_service import cosmos_service
from .openai_service import openai_service


class AnalyzeTasksView(APIView):
    """
    POST /api/tasks/analyze/
    
    Accept a list of tasks and return them sorted by priority score.
    """
    
    def post(self, request):
        try:
            # Parse and validate request
            data = request.data
            
            # Handle both direct task list and wrapped request
            if isinstance(data, list):
                tasks_data = data
                strategy = 'smart_balance'
                weights = None
                consider_weekends = True
            else:
                tasks_data = data.get('tasks', [])
                strategy = data.get('strategy', 'smart_balance')
                weights = data.get('weights')
                consider_weekends = data.get('consider_weekends', True)
            
            if not tasks_data:
                return Response(
                    {'error': 'No tasks provided', 'details': 'tasks array is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate each task
            validated_tasks = []
            validation_errors = []
            
            for i, task in enumerate(tasks_data):
                try:
                    # Ensure task has an ID
                    if 'id' not in task or not task['id']:
                        task['id'] = str(uuid.uuid4())
                    
                    validated = TaskInput(**task)
                    validated_tasks.append(validated.model_dump())
                except ValidationError as e:
                    validation_errors.append({
                        'task_index': i,
                        'task_title': task.get('title', 'Unknown'),
                        'errors': e.errors()
                    })
            
            if validation_errors and not validated_tasks:
                return Response(
                    {
                        'error': 'All tasks failed validation',
                        'validation_errors': validation_errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get AI classifications for date intelligence
            task_classifications = {}
            for task in validated_tasks:
                classification = openai_service.analyze_task_type(task['title'])
                task_classifications[task['id']] = classification
            
            # Validate weights if provided
            if weights:
                try:
                    weights = UserWeights(**weights).model_dump()
                except ValidationError:
                    weights = None
            
            # Analyze tasks
            analyzer = TaskAnalyzer(
                strategy=strategy,
                weights=weights,
                consider_weekends=consider_weekends
            )
            
            analyzed_tasks = analyzer.analyze_tasks(validated_tasks, task_classifications)
            
            # Check for circular dependencies
            scorer = TaskScorer()
            has_cycle, cycle_nodes = scorer.detect_circular_dependencies(validated_tasks)
            
            # Get Eisenhower matrix
            eisenhower_matrix = analyzer.get_eisenhower_matrix(analyzed_tasks)
            
            # Save tasks to Cosmos DB
            for task in analyzed_tasks:
                cosmos_service.save_task(task)
            
            response_data = {
                'success': True,
                'strategy': strategy,
                'total_tasks': len(analyzed_tasks),
                'tasks': analyzed_tasks,
                'eisenhower_matrix': {
                    'do_now': len(eisenhower_matrix['do_now']),
                    'schedule': len(eisenhower_matrix['schedule']),
                    'delegate': len(eisenhower_matrix['delegate']),
                    'drop': len(eisenhower_matrix['drop'])
                },
                'has_circular_dependencies': has_cycle,
                'circular_dependency_tasks': cycle_nodes,
                'weights_used': analyzer.scorer.weights
            }
            
            if validation_errors:
                response_data['validation_warnings'] = validation_errors
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': 'Analysis failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SuggestTasksView(APIView):
    """
    GET /api/tasks/suggest/
    
    Return the top 3 tasks the user should work on.
    """
    
    def get(self, request):
        try:
            # Get query parameters
            strategy = request.query_params.get('strategy', 'smart_balance')
            count = int(request.query_params.get('count', 3))
            user_id = request.query_params.get('user_id', 'default')
            
            # Get tasks from Cosmos DB
            tasks = cosmos_service.get_all_tasks()
            
            if not tasks:
                return Response(
                    {
                        'success': True,
                        'suggestions': [],
                        'message': 'No tasks found. Add tasks first using /api/tasks/analyze/'
                    },
                    status=status.HTTP_200_OK
                )
            
            # Get user weights if available
            weights = cosmos_service.get_user_weights(user_id)
            
            # Analyze and get suggestions
            analyzer = TaskAnalyzer(strategy=strategy, weights=weights)
            analyzed_tasks = analyzer.analyze_tasks(tasks)
            suggestions = analyzer.get_top_suggestions(analyzed_tasks, count)
            
            return Response(
                {
                    'success': True,
                    'strategy': strategy,
                    'suggestions': suggestions,
                    'total_tasks': len(tasks)
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': 'Failed to get suggestions', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EisenhowerMatrixView(APIView):
    """
    GET /api/tasks/matrix/
    
    Return tasks organized in Eisenhower Matrix format.
    """
    
    def get(self, request):
        try:
            # Get tasks from Cosmos DB
            tasks = cosmos_service.get_all_tasks()
            
            if not tasks:
                return Response(
                    {
                        'success': True,
                        'matrix': {
                            'do_now': [],
                            'schedule': [],
                            'delegate': [],
                            'drop': []
                        },
                        'message': 'No tasks found'
                    },
                    status=status.HTTP_200_OK
                )
            
            # Analyze tasks
            analyzer = TaskAnalyzer()
            analyzed_tasks = analyzer.analyze_tasks(tasks)
            matrix = analyzer.get_eisenhower_matrix(analyzed_tasks)
            
            return Response(
                {
                    'success': True,
                    'matrix': matrix,
                    'summary': {
                        'do_now': len(matrix['do_now']),
                        'schedule': len(matrix['schedule']),
                        'delegate': len(matrix['delegate']),
                        'drop': len(matrix['drop'])
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': 'Failed to get matrix', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Accept tasks and return Eisenhower matrix."""
        try:
            tasks_data = request.data.get('tasks', [])
            
            if not tasks_data:
                return Response(
                    {'error': 'No tasks provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate tasks
            validated_tasks = []
            for task in tasks_data:
                try:
                    if 'id' not in task or not task['id']:
                        task['id'] = str(uuid.uuid4())
                    validated = TaskInput(**task)
                    validated_tasks.append(validated.model_dump())
                except ValidationError:
                    continue
            
            # Analyze and get matrix
            analyzer = TaskAnalyzer()
            analyzed_tasks = analyzer.analyze_tasks(validated_tasks)
            matrix = analyzer.get_eisenhower_matrix(analyzed_tasks)
            
            return Response(
                {
                    'success': True,
                    'matrix': matrix,
                    'summary': {
                        'do_now': len(matrix['do_now']),
                        'schedule': len(matrix['schedule']),
                        'delegate': len(matrix['delegate']),
                        'drop': len(matrix['drop'])
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': 'Failed to generate matrix', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserWeightsView(APIView):
    """
    GET/POST /api/tasks/weights/
    
    Manage user weight configurations.
    """
    
    def get(self, request):
        """Get current user weights."""
        try:
            user_id = request.query_params.get('user_id', 'default')
            weights = cosmos_service.get_user_weights(user_id)
            
            if not weights:
                weights = TaskScorer.DEFAULT_WEIGHTS.copy()
                weights['custom_weights_enabled'] = False
            
            return Response(
                {
                    'success': True,
                    'user_id': user_id,
                    'weights': weights
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': 'Failed to get weights', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Update user weights."""
        try:
            user_id = request.data.get('user_id', 'default')
            weights_data = request.data.get('weights', {})
            
            # Validate weights
            try:
                validated = UserWeights(**weights_data)
                weights = validated.model_dump()
            except ValidationError as e:
                return Response(
                    {'error': 'Invalid weights', 'details': e.errors()},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Save to Cosmos DB
            cosmos_service.save_user_weights(user_id, weights)
            
            return Response(
                {
                    'success': True,
                    'user_id': user_id,
                    'weights': weights,
                    'message': 'Weights updated successfully'
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': 'Failed to update weights', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FeedbackView(APIView):
    """
    POST /api/tasks/feedback/
    
    Submit feedback on task suggestions for learning system.
    """
    
    def post(self, request):
        try:
            # Validate feedback
            try:
                feedback = FeedbackInput(**request.data)
            except ValidationError as e:
                return Response(
                    {'error': 'Invalid feedback', 'details': e.errors()},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get task details for learning
            task = cosmos_service.get_task(feedback.task_id)
            
            feedback_data = {
                'task_id': feedback.task_id,
                'helpful': feedback.helpful,
                'feedback_text': feedback.feedback_text,
                'urgency_score': task.get('urgency_score') if task else None,
                'importance_score': task.get('importance_score') if task else None,
                'effort_score': task.get('effort_score') if task else None,
                'blocking_score': task.get('blocking_score') if task else None
            }
            
            # Save feedback
            cosmos_service.save_feedback(feedback_data)
            
            return Response(
                {
                    'success': True,
                    'message': 'Feedback recorded successfully'
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': 'Failed to record feedback', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LearnWeightsView(APIView):
    """
    POST /api/tasks/learn/
    
    Trigger learning system to adjust weights based on feedback.
    """
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id', 'default')
            
            # Get current weights
            current_weights = cosmos_service.get_user_weights(user_id)
            if not current_weights:
                current_weights = TaskScorer.DEFAULT_WEIGHTS.copy()
            
            # Get feedback data
            feedback_stats = cosmos_service.get_feedback_stats()
            
            if not feedback_stats['feedbacks']:
                return Response(
                    {
                        'success': True,
                        'message': 'No feedback data available for learning',
                        'weights': current_weights
                    },
                    status=status.HTTP_200_OK
                )
            
            # Use AI to adjust weights
            new_weights = openai_service.adjust_weights_from_feedback(
                current_weights,
                feedback_stats['feedbacks']
            )
            
            # Save new weights
            new_weights['custom_weights_enabled'] = True
            cosmos_service.save_user_weights(user_id, new_weights)
            
            return Response(
                {
                    'success': True,
                    'message': 'Weights adjusted based on feedback',
                    'previous_weights': current_weights,
                    'new_weights': new_weights,
                    'feedback_summary': {
                        'helpful': feedback_stats['helpful'],
                        'not_helpful': feedback_stats['not_helpful']
                    },
                    'reasoning': new_weights.get('reasoning', '')
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': 'Learning failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TasksListView(APIView):
    """
    GET /api/tasks/
    
    Get all stored tasks.
    """
    
    def get(self, request):
        try:
            tasks = cosmos_service.get_all_tasks()
            
            return Response(
                {
                    'success': True,
                    'total': len(tasks),
                    'tasks': tasks
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': 'Failed to get tasks', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request):
        """Delete a task."""
        try:
            task_id = request.data.get('task_id')
            
            if not task_id:
                return Response(
                    {'error': 'task_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            success = cosmos_service.delete_task(task_id)
            
            return Response(
                {
                    'success': success,
                    'message': 'Task deleted' if success else 'Task not found'
                },
                status=status.HTTP_200_OK if success else status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            return Response(
                {'error': 'Failed to delete task', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
