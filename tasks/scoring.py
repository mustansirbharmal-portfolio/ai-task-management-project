"""
Priority Scoring Algorithm for Task Analyzer.

This module implements a sophisticated task prioritization system that considers:
- Urgency: How soon the task is due (with overdue handling)
- Importance: User-provided rating (1-10 scale)
- Effort/Easiness: Lower effort tasks as "quick wins"
- Dependencies: Tasks that block others get priority boost
- Date Intelligence: Weekends/holidays consideration for corporate tasks
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict
import math


class TaskScorer:
    """
    Core scoring engine for task prioritization.
    
    The algorithm normalizes all factors to 0-1 scale and combines them
    using configurable weights. Default weights are balanced but can be
    adjusted based on user preferences or learning system feedback.
    """
    
    # Default weights for balanced scoring
    DEFAULT_WEIGHTS = {
        'urgency_weight': 0.30,
        'importance_weight': 0.30,
        'effort_weight': 0.20,
        'blocking_weight': 0.20
    }
    
    # Strategy-specific weight presets
    STRATEGY_WEIGHTS = {
        'fastest_wins': {
            'urgency_weight': 0.15,
            'importance_weight': 0.15,
            'effort_weight': 0.60,
            'blocking_weight': 0.10
        },
        'high_impact': {
            'urgency_weight': 0.15,
            'importance_weight': 0.60,
            'effort_weight': 0.10,
            'blocking_weight': 0.15
        },
        'deadline_driven': {
            'urgency_weight': 0.60,
            'importance_weight': 0.20,
            'effort_weight': 0.10,
            'blocking_weight': 0.10
        },
        'smart_balance': {
            'urgency_weight': 0.30,
            'importance_weight': 0.30,
            'effort_weight': 0.20,
            'blocking_weight': 0.20
        }
    }
    
    # Overdue bonus - adds significant weight to past-due tasks
    OVERDUE_BONUS = 0.3
    
    # Maximum days to consider for urgency calculation
    MAX_URGENCY_DAYS = 30
    
    # Maximum hours for effort normalization
    MAX_EFFORT_HOURS = 40
    
    def __init__(self, weights: Optional[Dict] = None, strategy: str = 'smart_balance'):
        """
        Initialize scorer with weights.
        
        Args:
            weights: Custom weights dict or None for strategy defaults
            strategy: Sorting strategy name
        """
        if weights and weights.get('custom_weights_enabled', False):
            self.weights = {
                'urgency_weight': weights.get('urgency_weight', 0.3),
                'importance_weight': weights.get('importance_weight', 0.3),
                'effort_weight': weights.get('effort_weight', 0.2),
                'blocking_weight': weights.get('blocking_weight', 0.2)
            }
        else:
            self.weights = self.STRATEGY_WEIGHTS.get(strategy, self.DEFAULT_WEIGHTS).copy()
    
    def calculate_urgency_score(
        self, 
        due_date_str: str, 
        consider_weekends: bool = True,
        is_corporate: bool = True,
        is_urgent_task: bool = False
    ) -> Tuple[float, bool, int]:
        """
        Calculate urgency score based on due date.
        
        Args:
            due_date_str: Due date in YYYY-MM-DD format
            consider_weekends: Whether to exclude weekends from calculation
            is_corporate: Whether this is a corporate task
            is_urgent_task: Whether task is marked as urgent (ignores weekends)
        
        Returns:
            Tuple of (urgency_score, is_overdue, days_until_due)
        """
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            # Invalid date, treat as medium urgency
            return 0.5, False, 7
        
        today = date.today()
        
        # Calculate working days if corporate and not urgent
        if consider_weekends and is_corporate and not is_urgent_task:
            days_until_due = self._count_working_days(today, due_date)
        else:
            days_until_due = (due_date - today).days
        
        is_overdue = days_until_due < 0
        
        if is_overdue:
            # Overdue tasks get maximum urgency + bonus
            # More overdue = higher score (capped at 1.0 + bonus)
            overdue_days = abs(days_until_due)
            urgency = 1.0 + min(self.OVERDUE_BONUS, overdue_days * 0.05)
        elif days_until_due == 0:
            # Due today - maximum urgency
            urgency = 1.0
        elif days_until_due <= self.MAX_URGENCY_DAYS:
            # Linear decay: closer due date = higher urgency
            urgency = 1.0 - (days_until_due / self.MAX_URGENCY_DAYS)
        else:
            # Far future tasks get minimum urgency
            urgency = 0.1
        
        return round(urgency, 3), is_overdue, days_until_due
    
    def _count_working_days(self, start_date: date, end_date: date) -> int:
        """
        Count working days between two dates (excluding weekends).
        """
        if end_date < start_date:
            # Overdue - count negative working days
            return -self._count_working_days(end_date, start_date)
        
        working_days = 0
        current = start_date
        
        while current < end_date:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                working_days += 1
            current += timedelta(days=1)
        
        return working_days
    
    def calculate_importance_score(self, importance: int) -> float:
        """
        Normalize importance from 1-10 scale to 0-1.
        
        Args:
            importance: User rating 1-10
        
        Returns:
            Normalized importance score 0-1
        """
        # Clamp to valid range
        importance = max(1, min(10, importance))
        # Normalize to 0-1 (1 -> 0.1, 10 -> 1.0)
        return round(importance / 10.0, 3)
    
    def calculate_effort_score(self, estimated_hours: float) -> float:
        """
        Calculate effort score (higher = easier/quicker task).
        
        Lower effort tasks get higher scores as "quick wins".
        
        Args:
            estimated_hours: Estimated time to complete
        
        Returns:
            Effort score 0-1 (1 = very quick, 0 = very long)
        """
        # Clamp to reasonable range
        hours = max(0.1, min(self.MAX_EFFORT_HOURS, estimated_hours))
        
        # Inverse relationship: fewer hours = higher score
        # Using logarithmic scale for better distribution
        # 0.5 hours -> ~0.95, 8 hours -> ~0.5, 40 hours -> ~0.1
        score = 1.0 - (math.log(hours + 1) / math.log(self.MAX_EFFORT_HOURS + 1))
        
        return round(max(0.1, score), 3)
    
    def calculate_blocking_score(self, task_id: str, all_tasks: List[Dict]) -> float:
        """
        Calculate how many other tasks depend on this task.
        
        Tasks that block many others get higher priority.
        
        Args:
            task_id: ID of the task to score
            all_tasks: List of all tasks with dependencies
        
        Returns:
            Blocking score 0-1
        """
        if not all_tasks:
            return 0.0
        
        # Count how many tasks depend on this one
        blocked_count = 0
        for task in all_tasks:
            dependencies = task.get('dependencies', [])
            if task_id in dependencies:
                blocked_count += 1
        
        if blocked_count == 0:
            return 0.0
        
        # Normalize by total tasks (excluding self)
        max_possible = len(all_tasks) - 1
        if max_possible <= 0:
            return 0.0
        
        # Use sqrt for diminishing returns on very high blocking counts
        score = math.sqrt(blocked_count / max_possible)
        
        return round(min(1.0, score), 3)
    
    def calculate_priority_score(
        self,
        urgency: float,
        importance: float,
        effort: float,
        blocking: float
    ) -> float:
        """
        Calculate final priority score using weighted combination.
        
        Args:
            urgency: Urgency score 0-1+
            importance: Importance score 0-1
            effort: Effort score 0-1
            blocking: Blocking score 0-1
        
        Returns:
            Final priority score
        """
        score = (
            self.weights['urgency_weight'] * urgency +
            self.weights['importance_weight'] * importance +
            self.weights['effort_weight'] * effort +
            self.weights['blocking_weight'] * blocking
        )
        
        return round(score, 3)
    
    def get_priority_level(self, score: float) -> str:
        """
        Convert numeric score to priority level.
        
        Args:
            score: Priority score
        
        Returns:
            'High', 'Medium', or 'Low'
        """
        if score >= 0.7:
            return 'High'
        elif score >= 0.4:
            return 'Medium'
        else:
            return 'Low'
    
    def generate_score_explanation(
        self,
        urgency: float,
        importance: float,
        effort: float,
        blocking: float,
        is_overdue: bool,
        days_until_due: int
    ) -> str:
        """
        Generate human-readable explanation of the score.
        """
        explanations = []
        
        # Urgency explanation
        if is_overdue:
            explanations.append(f"⚠️ OVERDUE by {abs(days_until_due)} days")
        elif days_until_due == 0:
            explanations.append("📅 Due TODAY")
        elif days_until_due <= 3:
            explanations.append(f"📅 Due in {days_until_due} days (urgent)")
        elif days_until_due <= 7:
            explanations.append(f"📅 Due in {days_until_due} days")
        else:
            explanations.append(f"📅 Due in {days_until_due} days (not urgent)")
        
        # Importance explanation
        if importance >= 0.8:
            explanations.append("⭐ High importance")
        elif importance >= 0.5:
            explanations.append("⭐ Medium importance")
        else:
            explanations.append("⭐ Low importance")
        
        # Effort explanation
        if effort >= 0.7:
            explanations.append("⚡ Quick win (low effort)")
        elif effort <= 0.3:
            explanations.append("⏱️ Significant effort required")
        
        # Blocking explanation
        if blocking > 0:
            explanations.append(f"🔗 Blocks other tasks")
        
        return " | ".join(explanations)
    
    def detect_circular_dependencies(self, tasks: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Detect circular dependencies using DFS.
        
        Args:
            tasks: List of tasks with dependencies
        
        Returns:
            Tuple of (has_cycle, list of task IDs in cycle)
        """
        # Build adjacency list
        graph = defaultdict(list)
        task_ids = set()
        
        for task in tasks:
            task_id = task.get('id', '')
            task_ids.add(task_id)
            for dep in task.get('dependencies', []):
                graph[dep].append(task_id)  # dep -> task (dep must be done first)
        
        # DFS for cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in task_ids}
        cycle_nodes = []
        
        def dfs(node: str, path: List[str]) -> bool:
            if node not in color:
                return False
            
            if color[node] == GRAY:
                # Found cycle
                cycle_start = path.index(node)
                cycle_nodes.extend(path[cycle_start:])
                return True
            
            if color[node] == BLACK:
                return False
            
            color[node] = GRAY
            path.append(node)
            
            for neighbor in graph[node]:
                if dfs(neighbor, path):
                    return True
            
            path.pop()
            color[node] = BLACK
            return False
        
        for task_id in task_ids:
            if color[task_id] == WHITE:
                if dfs(task_id, []):
                    return True, list(set(cycle_nodes))
        
        return False, []
    
    def topological_sort(self, tasks: List[Dict]) -> List[Dict]:
        """
        Sort tasks respecting dependencies (topological order).
        
        Args:
            tasks: List of tasks with dependencies
        
        Returns:
            Topologically sorted list of tasks
        """
        # Build graph and in-degree count
        task_map = {t.get('id', ''): t for t in tasks}
        in_degree = defaultdict(int)
        graph = defaultdict(list)
        
        for task in tasks:
            task_id = task.get('id', '')
            for dep in task.get('dependencies', []):
                if dep in task_map:
                    graph[dep].append(task_id)
                    in_degree[task_id] += 1
        
        # Start with tasks that have no dependencies
        queue = [t for t in tasks if in_degree[t.get('id', '')] == 0]
        result = []
        
        while queue:
            # Sort queue by priority score (highest first)
            queue.sort(key=lambda t: t.get('priority_score', 0), reverse=True)
            task = queue.pop(0)
            result.append(task)
            
            task_id = task.get('id', '')
            for dependent in graph[task_id]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    result.append(task_map[dependent])
        
        # Handle any remaining tasks (in case of cycles)
        remaining = [t for t in tasks if t not in result]
        remaining.sort(key=lambda t: t.get('priority_score', 0), reverse=True)
        result.extend(remaining)
        
        return result


class TaskAnalyzer:
    """
    High-level task analysis orchestrator.
    """
    
    def __init__(
        self,
        strategy: str = 'smart_balance',
        weights: Optional[Dict] = None,
        consider_weekends: bool = True
    ):
        """
        Initialize analyzer.
        
        Args:
            strategy: Sorting strategy
            weights: Custom weights (if enabled)
            consider_weekends: Whether to consider weekends in urgency
        """
        self.scorer = TaskScorer(weights=weights, strategy=strategy)
        self.consider_weekends = consider_weekends
        self.strategy = strategy
    
    def analyze_tasks(
        self,
        tasks: List[Dict],
        task_classifications: Optional[Dict[str, Dict]] = None
    ) -> List[Dict]:
        """
        Analyze and score a list of tasks.
        
        Args:
            tasks: List of task dictionaries
            task_classifications: Optional AI classifications for date intelligence
        
        Returns:
            List of analyzed tasks with scores, sorted by priority
        """
        if not tasks:
            return []
        
        # Check for circular dependencies
        has_cycle, cycle_nodes = self.scorer.detect_circular_dependencies(tasks)
        
        analyzed_tasks = []
        
        for task in tasks:
            task_id = task.get('id', '')
            
            # Get AI classification if available
            classification = (task_classifications or {}).get(task_id, {})
            is_corporate = classification.get('is_corporate', True)
            is_urgent_task = classification.get('is_urgent', False)
            
            # Calculate individual scores
            urgency, is_overdue, days_until_due = self.scorer.calculate_urgency_score(
                task.get('due_date', ''),
                consider_weekends=self.consider_weekends,
                is_corporate=is_corporate,
                is_urgent_task=is_urgent_task
            )
            
            importance = self.scorer.calculate_importance_score(
                task.get('importance', 5)
            )
            
            effort = self.scorer.calculate_effort_score(
                task.get('estimated_hours', 4)
            )
            
            blocking = self.scorer.calculate_blocking_score(task_id, tasks)
            
            # Calculate final priority score
            priority_score = self.scorer.calculate_priority_score(
                urgency, importance, effort, blocking
            )
            
            # Generate explanation
            explanation = self.scorer.generate_score_explanation(
                urgency, importance, effort, blocking, is_overdue, days_until_due
            )
            
            # Build analyzed task
            analyzed_task = {
                'id': task_id,
                'title': task.get('title', ''),
                'due_date': task.get('due_date', ''),
                'estimated_hours': task.get('estimated_hours', 0),
                'importance': task.get('importance', 5),
                'dependencies': task.get('dependencies', []),
                'priority_score': priority_score,
                'urgency_score': urgency,
                'importance_score': importance,
                'effort_score': effort,
                'blocking_score': blocking,
                'priority_level': self.scorer.get_priority_level(priority_score),
                'score_explanation': explanation,
                'is_overdue': is_overdue,
                'days_until_due': days_until_due,
                'is_corporate': is_corporate,
                'is_urgent_task': is_urgent_task,
                'in_dependency_cycle': task_id in cycle_nodes
            }
            
            analyzed_tasks.append(analyzed_task)
        
        # Sort by priority score (respecting dependencies if smart_balance)
        if self.strategy == 'smart_balance':
            analyzed_tasks = self.scorer.topological_sort(analyzed_tasks)
        else:
            analyzed_tasks.sort(key=lambda t: t['priority_score'], reverse=True)
        
        return analyzed_tasks
    
    def get_top_suggestions(self, analyzed_tasks: List[Dict], count: int = 3) -> List[Dict]:
        """
        Get top N task suggestions.
        
        Args:
            analyzed_tasks: List of analyzed tasks
            count: Number of suggestions to return
        
        Returns:
            Top N tasks by priority
        """
        # Filter out tasks with unmet dependencies
        available_tasks = []
        completed_ids = set()  # In real app, this would come from task status
        
        for task in analyzed_tasks:
            deps = task.get('dependencies', [])
            # For now, include all tasks but prioritize those without deps
            if not deps or all(d in completed_ids for d in deps):
                available_tasks.append(task)
        
        # If no tasks without dependencies, return top scored anyway
        if not available_tasks:
            available_tasks = analyzed_tasks
        
        return available_tasks[:count]
    
    def get_eisenhower_matrix(self, analyzed_tasks: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize tasks into Eisenhower Matrix quadrants.
        
        Args:
            analyzed_tasks: List of analyzed tasks
        
        Returns:
            Dict with quadrant names as keys and task lists as values
        """
        matrix = {
            'do_now': [],      # Urgent + Important
            'schedule': [],    # Not Urgent + Important
            'delegate': [],    # Urgent + Not Important
            'drop': []         # Not Urgent + Not Important
        }
        
        for task in analyzed_tasks:
            urgency = task.get('urgency_score', 0)
            importance = task.get('importance_score', 0)
            
            is_urgent = urgency >= 0.6 or task.get('is_overdue', False)
            is_important = importance >= 0.6
            
            if is_urgent and is_important:
                matrix['do_now'].append(task)
            elif not is_urgent and is_important:
                matrix['schedule'].append(task)
            elif is_urgent and not is_important:
                matrix['delegate'].append(task)
            else:
                matrix['drop'].append(task)
        
        return matrix
