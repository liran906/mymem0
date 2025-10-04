"""
ProfileManager: Core pipeline for UserProfile extraction and updates

Implements the two-stage LLM pipeline:
1. Extract profile information from messages
2. Decide ADD/UPDATE/DELETE operations based on existing data
3. Execute database operations
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from mem0.user_profile.database import PostgresManager, MongoDBManager
from mem0.user_profile.prompts import EXTRACT_PROFILE_PROMPT, UPDATE_PROFILE_PROMPT
from mem0.user_profile.utils import (
    generate_uuid,
    get_current_timestamp,
    map_uuids_to_ids,
    reverse_id_mapping,
    merge_evidence,
    validate_degree,
    format_messages_for_llm,
)

logger = logging.getLogger(__name__)


class ProfileManager:
    """
    Core pipeline manager for UserProfile

    Handles the complete flow:
    1. Stage 1: LLM extracts profile info from messages
    2. Stage 2: Query existing data and map UUIDs
    3. Stage 3: LLM decides ADD/UPDATE/DELETE operations
    4. Stage 4: Execute database operations
    """

    def __init__(
        self,
        llm: Any,
        postgres: PostgresManager,
        mongodb: MongoDBManager,
    ):
        """
        Initialize ProfileManager

        Args:
            llm: LLM instance for making calls
            postgres: PostgresManager instance
            mongodb: MongoDBManager instance
        """
        self.llm = llm
        self.postgres = postgres
        self.mongodb = mongodb

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with prompt

        Args:
            prompt: Prompt string

        Returns:
            LLM response string
        """
        try:
            # Use the LLM's generate_response method
            response = self.llm.generate_response(
                messages=[{"role": "user", "content": prompt}]
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON response from LLM

        Args:
            response: LLM response string

        Returns:
            Parsed dict or None if parsing fails
        """
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {response}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return None

    def extract_profile(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """
        Stage 1: Extract profile information from messages using LLM

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Extracted profile dict with basic_info and additional_profile
        """
        try:
            # Format messages for prompt
            formatted_messages = format_messages_for_llm(messages)
            current_time = get_current_timestamp()

            # Build prompt
            prompt = EXTRACT_PROFILE_PROMPT.format(
                messages=formatted_messages,
                current_time=current_time,
            )

            # Call LLM
            logger.info("Stage 1: Extracting profile information from messages")
            response = self._call_llm(prompt)

            # Parse response
            extracted_data = self._parse_json_response(response)

            if not extracted_data:
                logger.warning("Failed to extract profile information")
                return None

            logger.info(f"Stage 1 complete: Extracted {len(extracted_data.get('additional_profile', {}))} fields")
            return extracted_data

        except Exception as e:
            logger.error(f"Stage 1 failed: {e}")
            return None

    def query_existing_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Stage 2: Query existing profile data and prepare for LLM

        Args:
            user_id: User ID

        Returns:
            Dict with basic_info and additional_profile (with integer IDs mapped)
        """
        try:
            logger.info(f"Stage 2: Querying existing profile for user {user_id}")

            # Query basic_info from PostgreSQL
            basic_info = self.postgres.get(user_id) or {}

            # Query additional_profile from MongoDB
            additional_profile = self.mongodb.get(user_id) or {}

            # Map UUIDs to integer IDs to prevent LLM hallucinations
            if additional_profile:
                additional_profile, id_mapping = map_uuids_to_ids(additional_profile)
            else:
                id_mapping = {}

            existing_profile = {
                "basic_info": basic_info,
                "additional_profile": additional_profile,
            }

            logger.info(f"Stage 2 complete: Found existing profile with {len(id_mapping)} items")
            return existing_profile, id_mapping

        except Exception as e:
            logger.error(f"Stage 2 failed: {e}")
            return {"basic_info": {}, "additional_profile": {}}, {}

    def decide_operations(
        self,
        extracted_info: Dict[str, Any],
        existing_profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Stage 3: LLM decides what operations to perform

        Args:
            extracted_info: Extracted profile information
            existing_profile: Existing profile data (with integer IDs)

        Returns:
            Operations dict with ADD/UPDATE/DELETE decisions
        """
        try:
            logger.info("Stage 3: Deciding operations (ADD/UPDATE/DELETE)")

            # Build prompt
            prompt = UPDATE_PROFILE_PROMPT.format(
                extracted_info=json.dumps(extracted_info, ensure_ascii=False, indent=2),
                existing_profile=json.dumps(existing_profile, ensure_ascii=False, indent=2),
            )

            # Call LLM
            response = self._call_llm(prompt)

            # Parse response
            operations = self._parse_json_response(response)

            if not operations:
                logger.warning("Failed to decide operations")
                return None

            logger.info(f"Stage 3 complete: Decided operations")
            return operations

        except Exception as e:
            logger.error(f"Stage 3 failed: {e}")
            return None

    def execute_operations(
        self,
        user_id: str,
        operations: Dict[str, Any],
        id_mapping: Dict[int, str],
    ) -> Dict[str, Any]:
        """
        Stage 4: Execute database operations

        Args:
            user_id: User ID
            operations: Operations dict from Stage 3
            id_mapping: Mapping of integer IDs to UUIDs

        Returns:
            Result dict with success status and details
        """
        try:
            logger.info(f"Stage 4: Executing operations for user {user_id}")

            result = {
                "success": True,
                "basic_info_updated": False,
                "additional_profile_updated": False,
                "operations_performed": {
                    "added": 0,
                    "updated": 0,
                    "deleted": 0,
                },
                "errors": [],
            }

            # Execute basic_info update (simple UPSERT)
            if operations.get("basic_info"):
                try:
                    self.postgres.upsert(user_id, operations["basic_info"])
                    result["basic_info_updated"] = True
                    logger.info("Basic info updated successfully")
                except Exception as e:
                    error_msg = f"Failed to update basic_info: {e}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
                    result["success"] = False

            # Execute additional_profile operations
            additional_profile = operations.get("additional_profile", {})

            if additional_profile:
                # Query current additional_profile
                current_profile = self.mongodb.get(user_id) or {}

                # Process each field (interests, skills, personality, etc.)
                for field_name, items in additional_profile.items():
                    if not isinstance(items, list):
                        continue

                    # Get current field data
                    current_field = current_profile.get(field_name, [])

                    # Process each item
                    for item in items:
                        event = item.get("event")
                        item_id = item.get("id")

                        try:
                            if event == "ADD":
                                # Generate new UUID for the item
                                new_id = generate_uuid()
                                item["id"] = new_id

                                # Remove event field before adding
                                item_copy = {k: v for k, v in item.items() if k != "event"}

                                # Add to current field
                                current_field.append(item_copy)
                                result["operations_performed"]["added"] += 1
                                logger.info(f"Added new item to {field_name}: {new_id}")

                            elif event == "UPDATE":
                                # Map integer ID back to UUID
                                if item_id is not None:
                                    int_id = int(item_id) if isinstance(item_id, str) else item_id
                                    if int_id in id_mapping:
                                        uuid = id_mapping[int_id]

                                        # Find and update the item
                                        for existing_item in current_field:
                                            if existing_item.get("id") == uuid:
                                                # Merge evidence
                                                new_evidence = item.get("evidence", [])
                                                existing_evidence = existing_item.get("evidence", [])
                                                merged_evidence = merge_evidence(existing_evidence, new_evidence)

                                                # Update fields
                                                existing_item.update({
                                                    k: v for k, v in item.items()
                                                    if k not in ["id", "event"]
                                                })
                                                existing_item["evidence"] = merged_evidence

                                                # Validate degree
                                                if "degree" in existing_item:
                                                    existing_item["degree"] = validate_degree(existing_item["degree"])

                                                result["operations_performed"]["updated"] += 1
                                                logger.info(f"Updated item in {field_name}: {uuid}")
                                                break

                            elif event == "DELETE":
                                # Map integer ID back to UUID
                                if item_id is not None:
                                    int_id = int(item_id) if isinstance(item_id, str) else item_id
                                    if int_id in id_mapping:
                                        uuid = id_mapping[int_id]

                                        # Remove the item
                                        current_field = [
                                            item for item in current_field
                                            if item.get("id") != uuid
                                        ]
                                        result["operations_performed"]["deleted"] += 1
                                        logger.info(f"Deleted item from {field_name}: {uuid}")

                        except Exception as e:
                            error_msg = f"Failed to {event} item in {field_name}: {e}"
                            logger.error(error_msg)
                            result["errors"].append(error_msg)

                    # Update field in current profile
                    current_profile[field_name] = current_field

                # Upsert entire additional_profile
                try:
                    self.mongodb.upsert(user_id, current_profile)
                    result["additional_profile_updated"] = True
                    logger.info("Additional profile updated successfully")
                except Exception as e:
                    error_msg = f"Failed to update additional_profile: {e}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
                    result["success"] = False

            logger.info(f"Stage 4 complete: {result['operations_performed']}")
            return result

        except Exception as e:
            logger.error(f"Stage 4 failed: {e}")
            return {
                "success": False,
                "errors": [str(e)],
            }

    def update_profile(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Complete pipeline: Extract, decide, and execute profile updates

        Args:
            user_id: User ID
            messages: Conversation messages

        Returns:
            Result dict with status and details
        """
        try:
            # Stage 1: Extract profile info
            extracted_info = self.extract_profile(messages)
            if not extracted_info:
                return {
                    "success": False,
                    "error": "Failed to extract profile information",
                }

            # Stage 2: Query existing profile
            existing_profile, id_mapping = self.query_existing_profile(user_id)

            # Stage 3: Decide operations
            operations = self.decide_operations(extracted_info, existing_profile)
            if not operations:
                return {
                    "success": False,
                    "error": "Failed to decide operations",
                }

            # Stage 4: Execute operations
            result = self.execute_operations(user_id, operations, id_mapping)

            return result

        except Exception as e:
            logger.error(f"Profile update pipeline failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
