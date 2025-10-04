"""
UserProfile: Main class for user profile management

Provides high-level API for extracting and managing user profiles from conversations.
"""

import logging
from typing import Dict, Any, List, Optional

from mem0.configs.base import MemoryConfig
from mem0.user_profile.database import PostgresManager, MongoDBManager
from mem0.user_profile.profile_manager import ProfileManager
from mem0.utils.factory import LlmFactory

logger = logging.getLogger(__name__)


class UserProfile:
    """
    UserProfile main class

    Provides API for:
    - Extracting user profile from conversation messages
    - Updating user profile with evidence-based approach
    - Retrieving user profile data

    Usage:
        from mem0 import Memory
        from mem0.user_profile import UserProfile

        # Initialize with the same config as Memory
        config = MemoryConfig()
        user_profile = UserProfile(config)

        # Update profile from messages
        result = user_profile.set_profile(
            user_id="user123",
            messages=[
                {"role": "user", "content": "我叫张三，住在北京"},
                {"role": "assistant", "content": "你好张三！"}
            ]
        )

        # Get profile
        profile = user_profile.get_profile(user_id="user123")
    """

    def __init__(self, config: MemoryConfig):
        """
        Initialize UserProfile

        Args:
            config: MemoryConfig instance with user_profile settings

        Architecture Note:
            - basic_info (PostgreSQL): Conversation-extracted reference data, NON-authoritative
            - additional_profile (MongoDB): Core value - interests, skills, personality
            - See discuss/19-manual_data_decision.md for architectural decisions
        """
        self.config = config

        # Initialize database managers
        self.postgres = PostgresManager(config.user_profile.postgres)
        self.mongodb = MongoDBManager(config.user_profile.mongodb)

        # Initialize LLM (shared with Memory module)
        self.llm = LlmFactory.create(
            config.llm.provider,
            config.llm.config,
        )

        # Initialize ProfileManager
        self.profile_manager = ProfileManager(
            llm=self.llm,
            postgres=self.postgres,
            mongodb=self.mongodb,
        )

        logger.info("UserProfile initialized successfully")

    def set_profile(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        manual_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extract and update user profile from conversation messages

        This method runs the complete pipeline:
        1. Extract profile information from messages using LLM
        2. Query existing profile data
        3. Decide ADD/UPDATE/DELETE operations using LLM
        4. Execute database operations

        Args:
            user_id: User ID (required)
            messages: List of message dicts with 'role' and 'content'
                Example:
                [
                    {"role": "user", "content": "我叫李明，今年30岁"},
                    {"role": "assistant", "content": "你好李明！"},
                    {"role": "user", "content": "我喜欢踢足球"}
                ]
            manual_data: Optional dict of manually provided basic_info that takes priority
                Example: {"name": "李明", "birthday": "1990-01-01"}

        Returns:
            Result dict with status and details:
            {
                "success": True,
                "basic_info_updated": True,
                "additional_profile_updated": True,
                "operations_performed": {
                    "added": 2,
                    "updated": 1,
                    "deleted": 0
                },
                "errors": []
            }

        Raises:
            ValueError: If user_id is not provided or messages is empty
        """
        # Validate input
        if not user_id:
            raise ValueError("user_id is required")

        if not messages or not isinstance(messages, list):
            raise ValueError("messages must be a non-empty list")

        # Run pipeline
        try:
            result = self.profile_manager.update_profile(user_id, messages)
            return result
        except Exception as e:
            logger.error(f"Failed to set profile for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_profile(
        self,
        user_id: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get user profile data

        Args:
            user_id: User ID (required)
            options: Query options (optional)
                - fields: List of field names to return from additional_profile
                  Example: {"fields": ["interests", "skills"]}
                  If None, returns all fields
                - evidence_limit: Control evidence return behavior (default 5):
                  * 0: Remove all evidence (return empty arrays)
                  * Positive N: Return latest N evidence items
                  * -1: Return all evidence
                  Example: {"evidence_limit": 0}, {"evidence_limit": 10}, {"evidence_limit": -1}

        Returns:
            Profile dict with basic_info and additional_profile:
            {
                "user_id": "user123",
                "basic_info": {
                    "name": "张三",
                    "current_city": "北京",
                    ...
                },
                "additional_profile": {
                    "interests": [...],
                    "skills": [...],
                    ...
                }
            }

        Raises:
            ValueError: If user_id is not provided
        """
        # Validate input
        if not user_id:
            raise ValueError("user_id is required")

        try:
            # Apply default evidence_limit if not specified
            if options is None:
                options = {}
            if 'evidence_limit' not in options:
                options['evidence_limit'] = 5  # Default to 5

            # Query basic_info
            basic_info = self.postgres.get(user_id) or {}

            # Query additional_profile with options
            additional_profile = self.mongodb.get(user_id, options) or {}

            return {
                "user_id": user_id,
                "basic_info": basic_info,
                "additional_profile": additional_profile,
            }
        except Exception as e:
            logger.error(f"Failed to get profile for user {user_id}: {e}")
            raise

    def get_missing_fields(self, user_id: str, source: str = "both") -> Dict[str, Any]:
        """
        Get missing fields in user profile

        Args:
            user_id: User ID (required)
            source: Which source to check - "pg", "mongo", or "both" (default)

        Returns:
            Result dict with missing fields:
            {
                "user_id": "user123",
                "missing_fields": {
                    "basic_info": ["hometown", "gender", "birthday"],
                    "additional_profile": ["personality", "learning_preferences"]
                }
            }

        Raises:
            ValueError: If user_id is not provided or source is invalid
        """
        # Validate input
        if not user_id:
            raise ValueError("user_id is required")

        if source not in ["pg", "mongo", "both"]:
            raise ValueError("source must be 'pg', 'mongo', or 'both'")

        try:
            result = {
                "user_id": user_id,
                "missing_fields": {}
            }

            # Check PostgreSQL basic_info
            if source in ["pg", "both"]:
                missing_basic = self.postgres.get_missing_fields(user_id)
                result["missing_fields"]["basic_info"] = missing_basic

            # Check MongoDB additional_profile
            if source in ["mongo", "both"]:
                missing_additional = self.mongodb.get_missing_fields(user_id)
                result["missing_fields"]["additional_profile"] = missing_additional

            return result
        except Exception as e:
            logger.error(f"Failed to get missing fields for user {user_id}: {e}")
            raise

    def delete_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Delete user profile completely

        Args:
            user_id: User ID (required)

        Returns:
            Result dict:
            {
                "success": True,
                "basic_info_deleted": True,
                "additional_profile_deleted": True
            }

        Raises:
            ValueError: If user_id is not provided
        """
        # Validate input
        if not user_id:
            raise ValueError("user_id is required")

        try:
            # Delete from PostgreSQL
            basic_info_deleted = self.postgres.delete(user_id)

            # Delete from MongoDB
            additional_profile_deleted = self.mongodb.delete(user_id)

            return {
                "success": True,
                "basic_info_deleted": basic_info_deleted,
                "additional_profile_deleted": additional_profile_deleted,
            }
        except Exception as e:
            logger.error(f"Failed to delete profile for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def initialize_databases(self):
        """
        Initialize database tables/collections

        Creates:
        - PostgreSQL: user_profile.user_profile table
        - MongoDB: user_additional_profile collection with indexes

        This is typically called once during setup.
        """
        try:
            logger.info("Initializing UserProfile databases...")

            # Initialize PostgreSQL table
            self.postgres.create_table()
            logger.info("PostgreSQL table created")

            # Initialize MongoDB collection
            self.mongodb.create_collection()
            logger.info("MongoDB collection created")

            logger.info("UserProfile databases initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize databases: {e}")
            raise

    def close(self):
        """Close database connections"""
        try:
            self.postgres.close()
            self.mongodb.close()
            logger.info("UserProfile connections closed")
        except Exception as e:
            logger.error(f"Failed to close connections: {e}")
            raise
