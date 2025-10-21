"""
Integration tests for PalServer cold start feature

Tests the complete cold start flow:
1. fetch_child_summary() HTTP client
2. UserProfile._convert_palserver_data() data conversion
3. UserProfile.get_profile() cold start integration
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from mem0.user_profile.palserver_client import fetch_child_summary


class TestPalServerClient(unittest.TestCase):
    """Test PalServer HTTP client"""

    def setUp(self):
        self.base_url = "http://localhost:8099/pal"
        self.child_id = "12345"

    @patch('mem0.user_profile.palserver_client.requests.get')
    def test_fetch_success(self, mock_get):
        """Test successful fetch from PalServer"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "code": "CHILD_INFO_RETRIEVED",
            "message": "孩子信息获取成功",
            "data": {
                "id": 12345,
                "childName": "小明",
                "age": 8,
                "gender": 1,
                "personalityTraits": "开朗,善良,勇敢",
                "hobbies": "篮球,音乐,阅读"
            }
        }
        mock_get.return_value = mock_response

        result = fetch_child_summary(self.child_id, self.base_url)

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 12345)
        self.assertEqual(result["childName"], "小明")
        mock_get.assert_called_once_with(
            f"{self.base_url}/child/{self.child_id}/summary",
            timeout=1.0
        )

    @patch('mem0.user_profile.palserver_client.requests.get')
    def test_fetch_timeout(self, mock_get):
        """Test timeout handling (1 second)"""
        import requests
        mock_get.side_effect = requests.Timeout("Connection timeout")

        result = fetch_child_summary(self.child_id, self.base_url)

        self.assertIsNone(result)

    @patch('mem0.user_profile.palserver_client.requests.get')
    def test_fetch_http_error(self, mock_get):
        """Test HTTP error handling (404, 500, etc.)"""
        import requests
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = fetch_child_summary(self.child_id, self.base_url)

        self.assertIsNone(result)

    @patch('mem0.user_profile.palserver_client.requests.get')
    def test_fetch_success_false(self, mock_get):
        """Test when PalServer returns success=False"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": False,
            "message": "Child not found"
        }
        mock_get.return_value = mock_response

        result = fetch_child_summary(self.child_id, self.base_url)

        self.assertIsNone(result)

    @patch('mem0.user_profile.palserver_client.requests.get')
    def test_fetch_missing_data_field(self, mock_get):
        """Test when response is missing 'data' field"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "OK"
            # Missing 'data' field
        }
        mock_get.return_value = mock_response

        result = fetch_child_summary(self.child_id, self.base_url)

        self.assertIsNone(result)

    def test_fetch_missing_params(self):
        """Test with missing required parameters"""
        result = fetch_child_summary("", self.base_url)
        self.assertIsNone(result)

        result = fetch_child_summary(self.child_id, "")
        self.assertIsNone(result)


class TestDataConversion(unittest.TestCase):
    """Test PalServer data to MyMem0 format conversion"""

    def setUp(self):
        """Create a mock UserProfile instance for testing conversion logic"""
        from mem0.user_profile.main import UserProfile

        # Create UserProfile instance with mocked database managers
        with patch('mem0.user_profile.main.PostgresManager'), \
             patch('mem0.user_profile.main.MongoDBManager'), \
             patch('mem0.user_profile.main.LlmFactory'):

            from mem0.configs.base import MemoryConfig
            config = MemoryConfig()
            self.user_profile = UserProfile(config)

    def test_convert_full_data(self):
        """Test conversion with complete data"""
        child_info = {
            "id": 12345,
            "childName": "小明",
            "age": 8,
            "gender": 1,
            "personalityTraits": "开朗,善良,勇敢",
            "hobbies": "篮球,音乐,阅读"
        }

        basic_info, additional_profile = self.user_profile._convert_palserver_data(child_info)

        # Check basic_info
        self.assertEqual(basic_info["nickname"], "小明")
        self.assertEqual(basic_info["gender"], "male")
        self.assertNotIn("age", basic_info)  # Age should be ignored

        # Check additional_profile
        self.assertIn("personality", additional_profile)
        self.assertEqual(len(additional_profile["personality"]), 3)
        self.assertEqual(additional_profile["personality"][0]["name"], "开朗")
        self.assertEqual(additional_profile["personality"][0]["degree"], 3)
        self.assertEqual(
            additional_profile["personality"][0]["evidence"][0]["text"],
            "Initial profile from user registration"
        )

        self.assertIn("interests", additional_profile)
        self.assertEqual(len(additional_profile["interests"]), 3)
        self.assertEqual(additional_profile["interests"][0]["name"], "篮球")
        self.assertEqual(additional_profile["interests"][0]["degree"], 3)

    def test_convert_gender_mapping(self):
        """Test gender value mapping (1->male, 2->female, other->unknown)"""
        # Test male
        basic_info, _ = self.user_profile._convert_palserver_data({"gender": 1})
        self.assertEqual(basic_info["gender"], "male")

        # Test female
        basic_info, _ = self.user_profile._convert_palserver_data({"gender": 2})
        self.assertEqual(basic_info["gender"], "female")

        # Test unknown
        basic_info, _ = self.user_profile._convert_palserver_data({"gender": 99})
        self.assertEqual(basic_info["gender"], "unknown")

        # Test None (should not set gender)
        basic_info, _ = self.user_profile._convert_palserver_data({"gender": None})
        self.assertNotIn("gender", basic_info)

    def test_convert_empty_fields(self):
        """Test handling of empty/null fields"""
        # Test empty strings
        basic_info, additional_profile = self.user_profile._convert_palserver_data({
            "childName": "",
            "personalityTraits": "",
            "hobbies": ""
        })

        self.assertNotIn("nickname", basic_info)
        self.assertNotIn("personality", additional_profile)
        self.assertNotIn("interests", additional_profile)

        # Test None values
        basic_info, additional_profile = self.user_profile._convert_palserver_data({
            "childName": None,
            "personalityTraits": None,
            "hobbies": None
        })

        self.assertNotIn("nickname", basic_info)
        self.assertNotIn("personality", additional_profile)
        self.assertNotIn("interests", additional_profile)

    def test_convert_whitespace_handling(self):
        """Test trimming whitespace in comma-separated values"""
        child_info = {
            "personalityTraits": " 开朗 , 善良 , 勇敢 ",
            "hobbies": "篮球,  音乐  ,阅读"
        }

        _, additional_profile = self.user_profile._convert_palserver_data(child_info)

        # Check trimmed values
        self.assertEqual(additional_profile["personality"][0]["name"], "开朗")
        self.assertEqual(additional_profile["personality"][1]["name"], "善良")
        self.assertEqual(additional_profile["interests"][1]["name"], "音乐")


class TestColdStartIntegration(unittest.TestCase):
    """Test end-to-end cold start integration"""

    @patch('mem0.user_profile.main.LlmFactory')
    @patch('mem0.user_profile.main.MongoDBManager')
    @patch('mem0.user_profile.main.PostgresManager')
    @patch('mem0.user_profile.main.fetch_child_summary')  # Patch where it's imported, not where it's defined
    def test_cold_start_user_not_exists(self, mock_fetch, mock_pg, mock_mongo, mock_llm):
        """Test cold start when user doesn't exist"""
        from mem0.user_profile.main import UserProfile
        from mem0.configs.base import MemoryConfig

        # Mock PalServer response
        mock_fetch.return_value = {
            "id": 12345,
            "childName": "小明",
            "gender": 1,
            "personalityTraits": "开朗,善良",
            "hobbies": "篮球,音乐"
        }

        # Mock database managers
        mock_pg_instance = mock_pg.return_value
        mock_pg_instance.get.side_effect = [None, {"nickname": "小明", "gender": "male"}]  # First None, then data after cold start
        mock_pg_instance.upsert.return_value = True

        mock_mongo_instance = mock_mongo.return_value
        mock_mongo_instance.get.side_effect = [None, {}]  # First None, then empty dict after cold start
        mock_mongo_instance.add_item.return_value = True

        # Initialize UserProfile with PalServer URL
        config = MemoryConfig()
        user_profile = UserProfile(config, palserver_base_url="http://localhost:8099/pal")

        # Call get_profile (should trigger cold start)
        result = user_profile.get_profile("12345")

        # Verify fetch_child_summary was called with correct params
        mock_fetch.assert_called_once_with("12345", "http://localhost:8099/pal")

        # Verify postgres.upsert was called with converted data
        mock_pg_instance.upsert.assert_called_once()
        upsert_call_args = mock_pg_instance.upsert.call_args
        self.assertEqual(upsert_call_args[0][0], "12345")  # user_id
        self.assertEqual(upsert_call_args[0][1]["nickname"], "小明")
        self.assertEqual(upsert_call_args[0][1]["gender"], "male")

        # Verify mongodb.add_item was called (2 personality + 2 interests = 4 calls)
        self.assertEqual(mock_mongo_instance.add_item.call_count, 4)

        # Verify result contains user_id
        self.assertEqual(result["user_id"], "12345")

    @patch('mem0.user_profile.main.LlmFactory')
    @patch('mem0.user_profile.main.MongoDBManager')
    @patch('mem0.user_profile.main.PostgresManager')
    @patch('mem0.user_profile.main.fetch_child_summary')  # Patch where it's imported
    def test_cold_start_disabled(self, mock_fetch, mock_pg, mock_mongo, mock_llm):
        """Test that cold start doesn't run when PalServer URL is not configured"""
        from mem0.user_profile.main import UserProfile
        from mem0.configs.base import MemoryConfig

        # Mock database returns None
        mock_pg_instance = mock_pg.return_value
        mock_pg_instance.get.return_value = None

        mock_mongo_instance = mock_mongo.return_value
        mock_mongo_instance.get.return_value = None

        # Initialize without palserver_base_url
        config = MemoryConfig()
        user_profile = UserProfile(config, palserver_base_url=None)

        # Call get_profile
        result = user_profile.get_profile("12345")

        # Verify fetch_child_summary was NOT called (cold start disabled)
        mock_fetch.assert_not_called()

        # Verify result is empty
        self.assertEqual(result["user_id"], "12345")
        self.assertEqual(result["basic_info"], {})
        self.assertEqual(result["additional_profile"], {})


if __name__ == '__main__':
    unittest.main()
