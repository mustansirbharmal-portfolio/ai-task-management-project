"""
Azure Cosmos DB service for task storage.
"""

import os
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from django.conf import settings
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CosmosDBService:
    """Service class for Cosmos DB operations."""
    
    def __init__(self):
        """Initialize Cosmos DB client."""
        self.endpoint = settings.COSMOS_ENDPOINT
        self.key = settings.COSMOS_KEY
        self.database_name = settings.COSMOS_DATABASE_NAME
        self.container_name = settings.COSMOS_CONTAINER_NAME
        
        self.client = None
        self.database = None
        self.container = None
        
        if self.endpoint and self.key:
            try:
                self.client = CosmosClient(self.endpoint, self.key)
                self._initialize_database()
            except Exception as e:
                logger.error(f"Failed to initialize Cosmos DB: {e}")
    
    def _initialize_database(self):
        """Initialize database and container."""
        try:
            # Create database if not exists
            self.database = self.client.create_database_if_not_exists(
                id=self.database_name
            )
            
            # Create container if not exists
            self.container = self.database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/type"),
                offer_throughput=400
            )
            logger.info("Cosmos DB initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Cosmos DB: {e}")
    
    def save_task(self, task_data: dict) -> dict:
        """Save a task to Cosmos DB."""
        if not self.container:
            logger.warning("Cosmos DB not available, task not persisted")
            return task_data
        
        try:
            task_data['type'] = 'task'
            task_data['created_at'] = datetime.utcnow().isoformat()
            task_data['updated_at'] = datetime.utcnow().isoformat()
            
            if 'id' not in task_data:
                task_data['id'] = str(uuid.uuid4())
            
            result = self.container.upsert_item(task_data)
            return result
        except Exception as e:
            logger.error(f"Error saving task: {e}")
            return task_data
    
    def get_task(self, task_id: str) -> dict:
        """Get a task by ID."""
        if not self.container:
            return None
        
        try:
            query = f"SELECT * FROM c WHERE c.id = '{task_id}' AND c.type = 'task'"
            items = list(self.container.query_items(query, enable_cross_partition_query=True))
            return items[0] if items else None
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None
    
    def get_all_tasks(self) -> list:
        """Get all tasks."""
        if not self.container:
            return []
        
        try:
            query = "SELECT * FROM c WHERE c.type = 'task'"
            items = list(self.container.query_items(query, enable_cross_partition_query=True))
            return items
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return []
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if not self.container:
            return False
        
        try:
            self.container.delete_item(item=task_id, partition_key='task')
            return True
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False
    
    def save_user_weights(self, user_id: str, weights: dict) -> dict:
        """Save user weights configuration."""
        if not self.container:
            return weights
        
        try:
            weights_data = {
                'id': f"weights_{user_id}",
                'type': 'user_weights',
                'user_id': user_id,
                'weights': weights,
                'updated_at': datetime.utcnow().isoformat()
            }
            result = self.container.upsert_item(weights_data)
            return result
        except Exception as e:
            logger.error(f"Error saving weights: {e}")
            return weights
    
    def get_user_weights(self, user_id: str) -> dict:
        """Get user weights configuration."""
        if not self.container:
            return None
        
        try:
            query = f"SELECT * FROM c WHERE c.id = 'weights_{user_id}' AND c.type = 'user_weights'"
            items = list(self.container.query_items(query, enable_cross_partition_query=True))
            return items[0]['weights'] if items else None
        except Exception as e:
            logger.error(f"Error getting weights: {e}")
            return None
    
    def save_feedback(self, feedback_data: dict) -> dict:
        """Save user feedback."""
        if not self.container:
            return feedback_data
        
        try:
            feedback_data['type'] = 'feedback'
            feedback_data['id'] = str(uuid.uuid4())
            feedback_data['created_at'] = datetime.utcnow().isoformat()
            
            result = self.container.upsert_item(feedback_data)
            return result
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
            return feedback_data
    
    def get_feedback_stats(self) -> dict:
        """Get feedback statistics for learning system."""
        if not self.container:
            return {'helpful': 0, 'not_helpful': 0, 'feedbacks': []}
        
        try:
            query = "SELECT * FROM c WHERE c.type = 'feedback'"
            items = list(self.container.query_items(query, enable_cross_partition_query=True))
            
            helpful_count = sum(1 for item in items if item.get('helpful', False))
            not_helpful_count = len(items) - helpful_count
            
            return {
                'helpful': helpful_count,
                'not_helpful': not_helpful_count,
                'feedbacks': items[-50:]  # Last 50 feedbacks
            }
        except Exception as e:
            logger.error(f"Error getting feedback stats: {e}")
            return {'helpful': 0, 'not_helpful': 0, 'feedbacks': []}


# Singleton instance
cosmos_service = CosmosDBService()
