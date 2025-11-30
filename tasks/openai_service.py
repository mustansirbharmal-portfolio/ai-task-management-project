"""
Azure OpenAI service for task intelligence.
"""

import os
from openai import AzureOpenAI
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service class for Azure OpenAI operations."""
    
    def __init__(self):
        """Initialize Azure OpenAI client."""
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.api_version = settings.AZURE_OPENAI_API_VERSION
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME
        
        self.client = None
        
        if self.endpoint and self.api_key:
            try:
                self.client = AzureOpenAI(
                    azure_endpoint=self.endpoint,
                    api_key=self.api_key,
                    api_version=self.api_version
                )
                logger.info("Azure OpenAI initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Azure OpenAI: {e}")
    
    def analyze_task_type(self, task_title: str, task_description: str = "") -> dict:
        """
        Analyze if a task is corporate/business or personal/urgent.
        Returns classification for date intelligence.
        """
        if not self.client:
            logger.warning("OpenAI not available, using default classification")
            return {
                'is_corporate': True,
                'is_urgent': False,
                'should_consider_weekends': True,
                'reasoning': 'Default classification (OpenAI unavailable)'
            }
        
        try:
            prompt = f"""Analyze the following task and determine:
1. Is this a corporate/business task or a personal task?
2. Is this an urgent task that should be worked on regardless of weekends/holidays?

Task Title: {task_title}
{f'Task Description: {task_description}' if task_description else ''}

Respond in JSON format:
{{
    "is_corporate": true/false,
    "is_urgent": true/false,
    "should_consider_weekends": true/false,
    "reasoning": "brief explanation"
}}

Rules:
- Corporate tasks typically involve work, business, clients, meetings, deadlines, projects
- Personal tasks involve home, family, hobbies, personal errands
- Urgent tasks (like "fix critical bug", "emergency", "ASAP") should ignore weekends
- Corporate non-urgent tasks should consider weekends (don't count weekend days in urgency)
"""
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a task classification assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON from response
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0]
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0]
            
            result = json.loads(result_text)
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing task type: {e}")
            return {
                'is_corporate': True,
                'is_urgent': False,
                'should_consider_weekends': True,
                'reasoning': f'Error in analysis: {str(e)}'
            }
    
    def adjust_weights_from_feedback(self, current_weights: dict, feedback_data: list) -> dict:
        """
        Use AI to suggest weight adjustments based on user feedback.
        """
        if not self.client:
            return self._heuristic_weight_adjustment(current_weights, feedback_data)
        
        try:
            # Prepare feedback summary
            helpful_tasks = [f for f in feedback_data if f.get('helpful', False)]
            not_helpful_tasks = [f for f in feedback_data if not f.get('helpful', False)]
            
            prompt = f"""Based on user feedback on task suggestions, recommend weight adjustments.

Current weights:
- Urgency: {current_weights.get('urgency_weight', 0.3)}
- Importance: {current_weights.get('importance_weight', 0.3)}
- Effort (quick wins): {current_weights.get('effort_weight', 0.2)}
- Blocking (dependencies): {current_weights.get('blocking_weight', 0.2)}

Feedback summary:
- {len(helpful_tasks)} suggestions marked as helpful
- {len(not_helpful_tasks)} suggestions marked as not helpful

Recent helpful task characteristics:
{json.dumps([{'urgency': t.get('urgency_score'), 'importance': t.get('importance_score'), 'effort': t.get('effort_score')} for t in helpful_tasks[:5]], indent=2) if helpful_tasks else 'None'}

Recent not-helpful task characteristics:
{json.dumps([{'urgency': t.get('urgency_score'), 'importance': t.get('importance_score'), 'effort': t.get('effort_score')} for t in not_helpful_tasks[:5]], indent=2) if not_helpful_tasks else 'None'}

Suggest new weights that sum to 1.0. Respond in JSON:
{{
    "urgency_weight": 0.X,
    "importance_weight": 0.X,
    "effort_weight": 0.X,
    "blocking_weight": 0.X,
    "reasoning": "explanation"
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a machine learning optimization assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0]
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0]
            
            result = json.loads(result_text)
            
            # Validate weights sum to 1
            total = result['urgency_weight'] + result['importance_weight'] + \
                    result['effort_weight'] + result['blocking_weight']
            
            if abs(total - 1.0) > 0.01:
                # Normalize
                result['urgency_weight'] /= total
                result['importance_weight'] /= total
                result['effort_weight'] /= total
                result['blocking_weight'] /= total
            
            return result
            
        except Exception as e:
            logger.error(f"Error adjusting weights with AI: {e}")
            return self._heuristic_weight_adjustment(current_weights, feedback_data)
    
    def _heuristic_weight_adjustment(self, current_weights: dict, feedback_data: list) -> dict:
        """
        Simple heuristic weight adjustment without AI.
        """
        weights = {
            'urgency_weight': current_weights.get('urgency_weight', 0.3),
            'importance_weight': current_weights.get('importance_weight', 0.3),
            'effort_weight': current_weights.get('effort_weight', 0.2),
            'blocking_weight': current_weights.get('blocking_weight', 0.2)
        }
        
        adjustment = 0.02  # Small adjustment per feedback
        
        for feedback in feedback_data[-10:]:  # Last 10 feedbacks
            if feedback.get('helpful', False):
                # Increase weights for high-scoring factors
                if feedback.get('urgency_score', 0) > 0.7:
                    weights['urgency_weight'] += adjustment
                if feedback.get('importance_score', 0) > 0.7:
                    weights['importance_weight'] += adjustment
                if feedback.get('effort_score', 0) > 0.7:
                    weights['effort_weight'] += adjustment
            else:
                # Decrease weights for high-scoring factors that weren't helpful
                if feedback.get('urgency_score', 0) > 0.7:
                    weights['urgency_weight'] -= adjustment
                if feedback.get('importance_score', 0) > 0.7:
                    weights['importance_weight'] -= adjustment
                if feedback.get('effort_score', 0) > 0.7:
                    weights['effort_weight'] -= adjustment
        
        # Ensure weights are positive and sum to 1
        for key in weights:
            weights[key] = max(0.05, weights[key])
        
        total = sum(weights.values())
        for key in weights:
            weights[key] = round(weights[key] / total, 3)
        
        weights['reasoning'] = 'Heuristic adjustment based on feedback patterns'
        
        return weights


# Singleton instance
openai_service = OpenAIService()
