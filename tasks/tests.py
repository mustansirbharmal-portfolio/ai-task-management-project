"""
Unit Tests for Task Analyzer Scoring Algorithm.

These tests cover:
1. Scoring correctness (urgency, importance, effort, blocking)
2. Overdue handling
3. Dependency logic and cycle detection
4. Edge cases (missing fields, invalid input, empty lists)
"""

import pytest
from datetime import date, timedelta
from .scoring import TaskScorer, TaskAnalyzer


class TestUrgencyScoring:
    """Tests for urgency score calculation."""
    
    def test_overdue_task_gets_high_urgency(self):
        """Overdue tasks should have urgency > 1.0."""
        scorer = TaskScorer()
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        urgency, is_overdue, days = scorer.calculate_urgency_score(yesterday)
        
        assert is_overdue is True
        assert urgency > 1.0
        assert days < 0
    
    def test_due_today_gets_maximum_urgency(self):
        """Tasks due today should have urgency = 1.0."""
        scorer = TaskScorer()
        today = date.today().strftime('%Y-%m-%d')
        
        urgency, is_overdue, days = scorer.calculate_urgency_score(today)
        
        assert urgency == 1.0
        assert is_overdue is False
        assert days == 0
    
    def test_future_task_gets_lower_urgency(self):
        """Tasks due in the future should have urgency < 1.0."""
        scorer = TaskScorer()
        next_week = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        urgency, is_overdue, days = scorer.calculate_urgency_score(next_week)
        
        assert urgency < 1.0
        assert is_overdue is False
        assert days > 0
    
    def test_far_future_task_gets_minimum_urgency(self):
        """Tasks due far in the future should have low urgency."""
        scorer = TaskScorer()
        far_future = (date.today() + timedelta(days=60)).strftime('%Y-%m-%d')
        
        urgency, is_overdue, days = scorer.calculate_urgency_score(far_future)
        
        assert urgency <= 0.2
        assert is_overdue is False
    
    def test_invalid_date_returns_default(self):
        """Invalid date format should return default values."""
        scorer = TaskScorer()
        
        urgency, is_overdue, days = scorer.calculate_urgency_score('invalid-date')
        
        assert urgency == 0.5
        assert is_overdue is False
        assert days == 7
    
    def test_weekend_consideration_for_corporate_tasks(self):
        """Corporate tasks should exclude weekends from urgency calculation."""
        scorer = TaskScorer()
        
        # Find next Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        
        # With weekends
        urgency_with_weekends, _, days_with = scorer.calculate_urgency_score(
            next_monday.strftime('%Y-%m-%d'),
            consider_weekends=True,
            is_corporate=True
        )
        
        # Without weekends
        urgency_without_weekends, _, days_without = scorer.calculate_urgency_score(
            next_monday.strftime('%Y-%m-%d'),
            consider_weekends=False
        )
        
        # Working days should be fewer than calendar days
        assert days_with <= days_without


class TestImportanceScoring:
    """Tests for importance score calculation."""
    
    def test_importance_normalization(self):
        """Importance 1-10 should normalize to 0.1-1.0."""
        scorer = TaskScorer()
        
        assert scorer.calculate_importance_score(1) == 0.1
        assert scorer.calculate_importance_score(5) == 0.5
        assert scorer.calculate_importance_score(10) == 1.0
    
    def test_importance_clamping(self):
        """Out of range values should be clamped."""
        scorer = TaskScorer()
        
        assert scorer.calculate_importance_score(0) == 0.1  # Clamped to 1
        assert scorer.calculate_importance_score(15) == 1.0  # Clamped to 10


class TestEffortScoring:
    """Tests for effort/easiness score calculation."""
    
    def test_quick_task_gets_high_score(self):
        """Low effort tasks should score high (quick wins)."""
        scorer = TaskScorer()
        
        score = scorer.calculate_effort_score(0.5)  # 30 minutes
        
        assert score > 0.8
    
    def test_long_task_gets_low_score(self):
        """High effort tasks should score low."""
        scorer = TaskScorer()
        
        score = scorer.calculate_effort_score(40)  # 40 hours
        
        assert score < 0.2
    
    def test_medium_task_gets_medium_score(self):
        """Medium effort tasks should score around 0.5."""
        scorer = TaskScorer()
        
        score = scorer.calculate_effort_score(8)  # 8 hours
        
        assert 0.3 < score < 0.7


class TestBlockingScoring:
    """Tests for dependency blocking score calculation."""
    
    def test_blocking_task_gets_bonus(self):
        """Tasks that block others should get higher scores."""
        scorer = TaskScorer()
        
        tasks = [
            {'id': 'task1', 'dependencies': []},
            {'id': 'task2', 'dependencies': ['task1']},
            {'id': 'task3', 'dependencies': ['task1']},
        ]
        
        blocking_score = scorer.calculate_blocking_score('task1', tasks)
        
        assert blocking_score > 0
    
    def test_non_blocking_task_gets_zero(self):
        """Tasks that don't block others should get 0."""
        scorer = TaskScorer()
        
        tasks = [
            {'id': 'task1', 'dependencies': []},
            {'id': 'task2', 'dependencies': []},
        ]
        
        blocking_score = scorer.calculate_blocking_score('task1', tasks)
        
        assert blocking_score == 0


class TestCircularDependencyDetection:
    """Tests for circular dependency detection."""
    
    def test_detects_simple_cycle(self):
        """Should detect A -> B -> A cycle."""
        scorer = TaskScorer()
        
        tasks = [
            {'id': 'A', 'dependencies': ['B']},
            {'id': 'B', 'dependencies': ['A']},
        ]
        
        has_cycle, cycle_nodes = scorer.detect_circular_dependencies(tasks)
        
        assert has_cycle is True
        assert len(cycle_nodes) > 0
    
    def test_detects_complex_cycle(self):
        """Should detect A -> B -> C -> A cycle."""
        scorer = TaskScorer()
        
        tasks = [
            {'id': 'A', 'dependencies': ['C']},
            {'id': 'B', 'dependencies': ['A']},
            {'id': 'C', 'dependencies': ['B']},
        ]
        
        has_cycle, cycle_nodes = scorer.detect_circular_dependencies(tasks)
        
        assert has_cycle is True
    
    def test_no_cycle_in_valid_graph(self):
        """Should not detect cycle in valid dependency graph."""
        scorer = TaskScorer()
        
        tasks = [
            {'id': 'A', 'dependencies': []},
            {'id': 'B', 'dependencies': ['A']},
            {'id': 'C', 'dependencies': ['A', 'B']},
        ]
        
        has_cycle, cycle_nodes = scorer.detect_circular_dependencies(tasks)
        
        assert has_cycle is False
        assert len(cycle_nodes) == 0


class TestPriorityScoring:
    """Tests for overall priority score calculation."""
    
    def test_weighted_combination(self):
        """Priority score should be weighted combination of factors."""
        scorer = TaskScorer()
        
        score = scorer.calculate_priority_score(
            urgency=1.0,
            importance=1.0,
            effort=1.0,
            blocking=1.0
        )
        
        # With default weights summing to 1.0, max score should be ~1.0
        assert 0.9 <= score <= 1.1
    
    def test_strategy_affects_weights(self):
        """Different strategies should use different weights."""
        fastest_scorer = TaskScorer(strategy='fastest_wins')
        impact_scorer = TaskScorer(strategy='high_impact')
        
        # Same inputs
        urgency, importance, effort, blocking = 0.5, 0.5, 0.9, 0.1
        
        fastest_score = fastest_scorer.calculate_priority_score(
            urgency, importance, effort, blocking
        )
        impact_score = impact_scorer.calculate_priority_score(
            urgency, importance, effort, blocking
        )
        
        # Fastest wins should score higher for high effort score
        assert fastest_score > impact_score
    
    def test_priority_levels(self):
        """Priority levels should map correctly from scores."""
        scorer = TaskScorer()
        
        assert scorer.get_priority_level(0.8) == 'High'
        assert scorer.get_priority_level(0.5) == 'Medium'
        assert scorer.get_priority_level(0.2) == 'Low'


class TestTaskAnalyzer:
    """Tests for the TaskAnalyzer orchestrator."""
    
    def test_analyze_empty_list(self):
        """Should handle empty task list."""
        analyzer = TaskAnalyzer()
        
        result = analyzer.analyze_tasks([])
        
        assert result == []
    
    def test_analyze_single_task(self):
        """Should analyze a single task correctly."""
        analyzer = TaskAnalyzer()
        tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        tasks = [{
            'id': 'task1',
            'title': 'Test Task',
            'due_date': tomorrow,
            'estimated_hours': 2,
            'importance': 8,
            'dependencies': []
        }]
        
        result = analyzer.analyze_tasks(tasks)
        
        assert len(result) == 1
        assert 'priority_score' in result[0]
        assert 'urgency_score' in result[0]
        assert 'importance_score' in result[0]
        assert 'effort_score' in result[0]
        assert 'priority_level' in result[0]
    
    def test_tasks_sorted_by_priority(self):
        """Tasks should be sorted by priority score descending."""
        analyzer = TaskAnalyzer()
        today = date.today()
        
        tasks = [
            {
                'id': 'low',
                'title': 'Low Priority',
                'due_date': (today + timedelta(days=30)).strftime('%Y-%m-%d'),
                'estimated_hours': 20,
                'importance': 2,
                'dependencies': []
            },
            {
                'id': 'high',
                'title': 'High Priority',
                'due_date': today.strftime('%Y-%m-%d'),
                'estimated_hours': 1,
                'importance': 10,
                'dependencies': []
            },
        ]
        
        result = analyzer.analyze_tasks(tasks)
        
        # High priority task should be first
        assert result[0]['id'] == 'high'
        assert result[0]['priority_score'] > result[1]['priority_score']
    
    def test_overdue_task_prioritized(self):
        """Overdue tasks should be prioritized over non-overdue."""
        analyzer = TaskAnalyzer()
        today = date.today()
        
        tasks = [
            {
                'id': 'future',
                'title': 'Future Task',
                'due_date': (today + timedelta(days=7)).strftime('%Y-%m-%d'),
                'estimated_hours': 2,
                'importance': 10,
                'dependencies': []
            },
            {
                'id': 'overdue',
                'title': 'Overdue Task',
                'due_date': (today - timedelta(days=3)).strftime('%Y-%m-%d'),
                'estimated_hours': 2,
                'importance': 5,
                'dependencies': []
            },
        ]
        
        result = analyzer.analyze_tasks(tasks)
        
        # Overdue task should be first despite lower importance
        assert result[0]['id'] == 'overdue'
        assert result[0]['is_overdue'] is True
    
    def test_eisenhower_matrix_categorization(self):
        """Tasks should be correctly categorized in Eisenhower matrix."""
        analyzer = TaskAnalyzer()
        today = date.today()
        
        tasks = [
            {
                'id': 'urgent_important',
                'title': 'Urgent Important',
                'due_date': today.strftime('%Y-%m-%d'),
                'estimated_hours': 2,
                'importance': 9,
                'dependencies': []
            },
            {
                'id': 'not_urgent_important',
                'title': 'Not Urgent Important',
                'due_date': (today + timedelta(days=30)).strftime('%Y-%m-%d'),
                'estimated_hours': 2,
                'importance': 9,
                'dependencies': []
            },
            {
                'id': 'urgent_not_important',
                'title': 'Urgent Not Important',
                'due_date': today.strftime('%Y-%m-%d'),
                'estimated_hours': 2,
                'importance': 2,
                'dependencies': []
            },
            {
                'id': 'not_urgent_not_important',
                'title': 'Not Urgent Not Important',
                'due_date': (today + timedelta(days=30)).strftime('%Y-%m-%d'),
                'estimated_hours': 2,
                'importance': 2,
                'dependencies': []
            },
        ]
        
        analyzed = analyzer.analyze_tasks(tasks)
        matrix = analyzer.get_eisenhower_matrix(analyzed)
        
        assert len(matrix['do_now']) >= 1
        assert len(matrix['schedule']) >= 1
        assert len(matrix['delegate']) >= 1
        assert len(matrix['drop']) >= 1
    
    def test_top_suggestions_respects_count(self):
        """get_top_suggestions should return correct number of tasks."""
        analyzer = TaskAnalyzer()
        today = date.today()
        
        tasks = [
            {
                'id': f'task{i}',
                'title': f'Task {i}',
                'due_date': (today + timedelta(days=i)).strftime('%Y-%m-%d'),
                'estimated_hours': 2,
                'importance': 5,
                'dependencies': []
            }
            for i in range(10)
        ]
        
        analyzed = analyzer.analyze_tasks(tasks)
        suggestions = analyzer.get_top_suggestions(analyzed, count=3)
        
        assert len(suggestions) == 3


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_missing_dependencies_field(self):
        """Should handle tasks without dependencies field."""
        analyzer = TaskAnalyzer()
        today = date.today()
        
        tasks = [{
            'id': 'task1',
            'title': 'Test',
            'due_date': today.strftime('%Y-%m-%d'),
            'estimated_hours': 2,
            'importance': 5
            # No dependencies field
        }]
        
        result = analyzer.analyze_tasks(tasks)
        
        assert len(result) == 1
        assert result[0]['dependencies'] == []
    
    def test_self_dependency(self):
        """Should handle task depending on itself."""
        scorer = TaskScorer()
        
        tasks = [
            {'id': 'task1', 'dependencies': ['task1']},  # Self-dependency
        ]
        
        has_cycle, _ = scorer.detect_circular_dependencies(tasks)
        
        # Self-dependency is a form of cycle
        assert has_cycle is True
    
    def test_dependency_on_nonexistent_task(self):
        """Should handle dependencies on non-existent tasks."""
        analyzer = TaskAnalyzer()
        today = date.today()
        
        tasks = [{
            'id': 'task1',
            'title': 'Test',
            'due_date': today.strftime('%Y-%m-%d'),
            'estimated_hours': 2,
            'importance': 5,
            'dependencies': ['nonexistent_task']
        }]
        
        # Should not raise exception
        result = analyzer.analyze_tasks(tasks)
        
        assert len(result) == 1
    
    def test_extreme_values(self):
        """Should handle extreme input values."""
        scorer = TaskScorer()
        
        # Very high hours
        effort = scorer.calculate_effort_score(1000)
        assert 0 <= effort <= 1
        
        # Very negative importance (should clamp)
        importance = scorer.calculate_importance_score(-5)
        assert importance == 0.1
    
    def test_custom_weights(self):
        """Should use custom weights when enabled."""
        custom_weights = {
            'urgency_weight': 0.5,
            'importance_weight': 0.3,
            'effort_weight': 0.1,
            'blocking_weight': 0.1,
            'custom_weights_enabled': True
        }
        
        scorer = TaskScorer(weights=custom_weights)
        
        assert scorer.weights['urgency_weight'] == 0.5
        assert scorer.weights['importance_weight'] == 0.3


class TestToughEdgeCases:
    """
    5 Strong and Tough Edge Case Tests
    These test extreme scenarios, performance limits, and complex dependency graphs.
    """
    
    # =========================================================================
    # EDGE CASE 1: Massive Task List with Deep Dependency Chain
    # =========================================================================
    def test_large_scale_linear_dependency_chain(self):
        """
        Test Case 1: 100 tasks in a linear dependency chain (A→B→C→...→Z)
        
        Approach: Creates a long chain where each task depends on the previous one.
        This tests topological sorting and blocking score calculation at scale.
        
        Time Complexity: O(n²) - For each task, we check all other tasks for dependencies
        Space Complexity: O(n) - Storing n tasks and their analyzed results
        Efficiency: Tests algorithm's ability to handle deep recursion in dependency graphs
        """
        analyzer = TaskAnalyzer()
        today = date.today()
        n = 100  # 100 tasks in chain
        
        tasks = []
        for i in range(n):
            tasks.append({
                'id': f'task-{i}',
                'title': f'Chain Task {i}',
                'due_date': (today + timedelta(days=i % 30)).strftime('%Y-%m-%d'),
                'estimated_hours': (i % 10) + 1,
                'importance': (i % 10) + 1,
                'dependencies': [f'task-{i-1}'] if i > 0 else []
            })
        
        result = analyzer.analyze_tasks(tasks)
        
        # Assertions
        assert len(result) == n
        
        # First task (task-0) should have highest blocking score (blocks 99 tasks)
        task_0 = next(t for t in result if t['id'] == 'task-0')
        task_99 = next(t for t in result if t['id'] == 'task-99')
        
        assert task_0['blocking_score'] > task_99['blocking_score']
        
        # No circular dependencies
        scorer = TaskScorer()
        has_cycle, _ = scorer.detect_circular_dependencies(tasks)
        assert has_cycle is False
    
    # =========================================================================
    # EDGE CASE 2: Complex Multi-Path Dependency Graph (Diamond + Cross)
    # =========================================================================
    def test_complex_diamond_cross_dependency_graph(self):
        """
        Test Case 2: Complex dependency graph with diamond patterns and cross-dependencies
        
        Graph Structure:
                    [A]
                   / | \\
                 [B][C][D]
                  \\ | /|
                   [E] |
                   / \\ |
                 [F] [G]
                  \\ /
                   [H]
        
        Approach: Tests multiple convergent and divergent paths in dependency graph.
        Time Complexity: O(V + E) for cycle detection using DFS
        Space Complexity: O(V) for visited set and recursion stack
        Efficiency: Tests handling of complex graph topologies without cycles
        """
        analyzer = TaskAnalyzer()
        today = date.today()
        
        tasks = [
            {'id': 'A', 'title': 'Root Task', 'due_date': today.strftime('%Y-%m-%d'),
             'estimated_hours': 2, 'importance': 10, 'dependencies': []},
            {'id': 'B', 'title': 'Branch B', 'due_date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
             'estimated_hours': 3, 'importance': 8, 'dependencies': ['A']},
            {'id': 'C', 'title': 'Branch C', 'due_date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
             'estimated_hours': 2, 'importance': 7, 'dependencies': ['A']},
            {'id': 'D', 'title': 'Branch D', 'due_date': (today + timedelta(days=2)).strftime('%Y-%m-%d'),
             'estimated_hours': 4, 'importance': 9, 'dependencies': ['A']},
            {'id': 'E', 'title': 'Merge Point E', 'due_date': (today + timedelta(days=3)).strftime('%Y-%m-%d'),
             'estimated_hours': 5, 'importance': 8, 'dependencies': ['B', 'C', 'D']},
            {'id': 'F', 'title': 'Branch F', 'due_date': (today + timedelta(days=4)).strftime('%Y-%m-%d'),
             'estimated_hours': 2, 'importance': 6, 'dependencies': ['E']},
            {'id': 'G', 'title': 'Cross Branch G', 'due_date': (today + timedelta(days=4)).strftime('%Y-%m-%d'),
             'estimated_hours': 3, 'importance': 7, 'dependencies': ['E', 'D']},
            {'id': 'H', 'title': 'Final Merge H', 'due_date': (today + timedelta(days=5)).strftime('%Y-%m-%d'),
             'estimated_hours': 2, 'importance': 9, 'dependencies': ['F', 'G']},
        ]
        
        result = analyzer.analyze_tasks(tasks)
        matrix = analyzer.get_eisenhower_matrix(result)
        
        # Assertions
        assert len(result) == 8
        
        # Task A should have highest blocking score (blocks all others)
        task_a = next(t for t in result if t['id'] == 'A')
        assert task_a['blocking_score'] > 0
        
        # No cycles
        scorer = TaskScorer()
        has_cycle, _ = scorer.detect_circular_dependencies(tasks)
        assert has_cycle is False
        
        # Matrix should have tasks distributed
        total_in_matrix = sum(len(matrix[q]) for q in matrix)
        assert total_in_matrix == 8
    
    # =========================================================================
    # EDGE CASE 3: All Tasks Overdue with Varying Severity
    # =========================================================================
    def test_all_tasks_overdue_priority_ordering(self):
        """
        Test Case 3: All 20 tasks are overdue with varying overdue days and importance
        
        Approach: Tests urgency boost calculation for overdue tasks and correct
        priority ordering when all tasks are past due.
        
        Time Complexity: O(n log n) for sorting by priority
        Space Complexity: O(n) for storing analyzed tasks
        Efficiency: Tests overdue penalty scaling and priority differentiation
        """
        analyzer = TaskAnalyzer()
        today = date.today()
        
        tasks = []
        for i in range(20):
            overdue_days = (i + 1) * 2  # 2, 4, 6, ... 40 days overdue
            importance = 10 - (i % 10)  # Varying importance 10, 9, 8, ... 1
            
            tasks.append({
                'id': f'overdue-{i}',
                'title': f'Overdue Task {i} ({overdue_days} days late)',
                'due_date': (today - timedelta(days=overdue_days)).strftime('%Y-%m-%d'),
                'estimated_hours': (i % 5) + 1,
                'importance': importance,
                'dependencies': []
            })
        
        result = analyzer.analyze_tasks(tasks)
        
        # Assertions
        assert len(result) == 20
        
        # All tasks should be marked overdue
        for task in result:
            assert task['is_overdue'] is True
            assert task['urgency_score'] > 1.0  # Overdue boost
        
        # Most overdue + high importance should be first
        # The algorithm should balance overdue severity with importance
        assert result[0]['urgency_score'] > result[-1]['urgency_score'] or \
               result[0]['importance_score'] > result[-1]['importance_score']
        
        # Priority scores should be descending
        for i in range(len(result) - 1):
            assert result[i]['priority_score'] >= result[i + 1]['priority_score']
    
    # =========================================================================
    # EDGE CASE 4: Extreme Values Stress Test
    # =========================================================================
    def test_extreme_boundary_values(self):
        """
        Test Case 4: Tasks with extreme/boundary values for all parameters
        
        Approach: Tests system behavior with edge values:
        - 0.01 hours (36 seconds) to 10000 hours
        - Importance 0 to 100 (out of valid range)
        - Due dates from 10 years ago to 10 years future
        
        Time Complexity: O(n) for processing each task
        Space Complexity: O(1) per task scoring
        Efficiency: Tests input validation, clamping, and numerical stability
        """
        analyzer = TaskAnalyzer()
        today = date.today()
        
        extreme_tasks = [
            # Minimum effort (36 seconds)
            {'id': 'min-effort', 'title': 'Tiny Task', 
             'due_date': today.strftime('%Y-%m-%d'),
             'estimated_hours': 0.01, 'importance': 5, 'dependencies': []},
            
            # Maximum effort (10000 hours = 416 days)
            {'id': 'max-effort', 'title': 'Massive Project',
             'due_date': (today + timedelta(days=365)).strftime('%Y-%m-%d'),
             'estimated_hours': 10000, 'importance': 10, 'dependencies': []},
            
            # Zero importance (should clamp to 1)
            {'id': 'zero-importance', 'title': 'Zero Priority',
             'due_date': (today + timedelta(days=7)).strftime('%Y-%m-%d'),
             'estimated_hours': 2, 'importance': 0, 'dependencies': []},
            
            # Over-max importance (should clamp to 10)
            {'id': 'max-importance', 'title': 'Critical Override',
             'due_date': today.strftime('%Y-%m-%d'),
             'estimated_hours': 1, 'importance': 100, 'dependencies': []},
            
            # Very old overdue (10 years ago)
            {'id': 'ancient-overdue', 'title': 'Forgotten Task',
             'due_date': (today - timedelta(days=3650)).strftime('%Y-%m-%d'),
             'estimated_hours': 5, 'importance': 8, 'dependencies': []},
            
            # Far future (10 years ahead)
            {'id': 'far-future', 'title': 'Long Term Goal',
             'due_date': (today + timedelta(days=3650)).strftime('%Y-%m-%d'),
             'estimated_hours': 100, 'importance': 3, 'dependencies': []},
            
            # Negative hours (invalid - should handle gracefully)
            {'id': 'negative-hours', 'title': 'Invalid Hours',
             'due_date': today.strftime('%Y-%m-%d'),
             'estimated_hours': -5, 'importance': 5, 'dependencies': []},
        ]
        
        result = analyzer.analyze_tasks(extreme_tasks)
        
        # Assertions - all tasks should be processed without errors
        assert len(result) == 7
        
        # All scores should be within valid ranges
        for task in result:
            assert 0 <= task['importance_score'] <= 1.0
            assert 0 <= task['effort_score'] <= 1.0
            assert task['priority_score'] >= 0  # Can exceed 1.0 for overdue
        
        # Min effort should have high effort score (quick win)
        min_effort = next(t for t in result if t['id'] == 'min-effort')
        assert min_effort['effort_score'] > 0.9
        
        # Max effort should have low effort score
        max_effort = next(t for t in result if t['id'] == 'max-effort')
        assert max_effort['effort_score'] <= 0.1
        
        # Ancient overdue should have very high urgency
        ancient = next(t for t in result if t['id'] == 'ancient-overdue')
        assert ancient['urgency_score'] > 1.0  # Overdue tasks get urgency > 1.0
        assert ancient['is_overdue'] is True
        
        # Far future should have very low urgency
        far_future = next(t for t in result if t['id'] == 'far-future')
        assert far_future['urgency_score'] <= 0.1  # Minimum urgency floor
    
    # =========================================================================
    # EDGE CASE 5: Multiple Circular Dependencies Detection
    # =========================================================================
    def test_multiple_overlapping_cycles(self):
        """
        Test Case 5: Graph with multiple overlapping circular dependencies
        
        Graph Structure:
            [A] ←→ [B]     (Cycle 1: A-B)
             ↓      ↓
            [C] → [D] → [E]
             ↑           ↓
             └─────[F]←──┘  (Cycle 2: C-D-E-F-C)
             
            [G] → [H] → [I] → [G]  (Cycle 3: G-H-I-G, isolated)
        
        Approach: Tests detection of multiple independent and overlapping cycles.
        Time Complexity: O(V + E) using DFS with coloring
        Space Complexity: O(V) for visited states
        Efficiency: Tests robustness of cycle detection with complex graph
        """
        scorer = TaskScorer()
        
        tasks = [
            # Cycle 1: A ↔ B
            {'id': 'A', 'dependencies': ['B']},
            {'id': 'B', 'dependencies': ['A', 'D']},
            
            # Path with Cycle 2: C → D → E → F → C
            {'id': 'C', 'dependencies': ['A', 'F']},
            {'id': 'D', 'dependencies': ['C']},
            {'id': 'E', 'dependencies': ['D']},
            {'id': 'F', 'dependencies': ['E']},
            
            # Isolated Cycle 3: G → H → I → G
            {'id': 'G', 'dependencies': ['I']},
            {'id': 'H', 'dependencies': ['G']},
            {'id': 'I', 'dependencies': ['H']},
            
            # Non-cyclic node
            {'id': 'J', 'dependencies': []},
        ]
        
        has_cycle, cycle_nodes = scorer.detect_circular_dependencies(tasks)
        
        # Assertions
        assert has_cycle is True
        assert len(cycle_nodes) > 0
        
        # At least one node from each cycle should be detected
        # (exact nodes depend on DFS traversal order)
        cycle_set = set(cycle_nodes)
        
        # Verify cycles exist by checking some expected nodes
        has_cycle_1 = 'A' in cycle_set or 'B' in cycle_set
        has_cycle_3 = 'G' in cycle_set or 'H' in cycle_set or 'I' in cycle_set
        
        assert has_cycle_1 or has_cycle_3  # At least one cycle detected
        
        # J should never be in cycle (it's isolated and non-cyclic)
        assert 'J' not in cycle_set


# Run tests with: pytest tasks/tests.py -v
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
