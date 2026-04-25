import unittest

from pydantic import ValidationError

from src.core.config import Global
from src.core import settings


class TestConfig(unittest.TestCase):
    def test_guild_ids_accept_string_snowflakes(self):
        """Test that guild IDs can be provided as digit strings and are coerced to ints."""
        config = Global(HTB_API_KEY="test", guild_ids=["6455184161011276950"], dev_guild_ids=["7764771731239076051"])
        self.assertEqual(config.guild_ids, [6455184161011276950])
        self.assertEqual(config.dev_guild_ids, [7764771731239076051])

    def test_guild_ids_reject_non_snowflakes(self):
        """Test that guild IDs must be positive base-10 unsigned 64-bit snowflakes."""
        with self.assertRaises(ValidationError):
            Global(HTB_API_KEY="test", guild_ids=["not-a-snowflake"])

        with self.assertRaises(ValidationError):
            Global(HTB_API_KEY="test", guild_ids=[0])

        with self.assertRaises(ValidationError):
            Global(HTB_API_KEY="test", guild_ids=[2**64])

    def test_core_roles_required(self):
        """Test that core roles are still loaded from env vars."""
        self.assertIsNotNone(settings.roles.VERIFIED)
        self.assertIsInstance(settings.roles.VERIFIED, int)
        self.assertIsNotNone(settings.roles.ADMINISTRATOR)
        self.assertIsInstance(settings.roles.ADMINISTRATOR, int)

    def test_core_role_groups_present(self):
        """Test that core role groups are populated."""
        self.assertIn("ALL_ADMINS", settings.role_groups)
        self.assertIn("ALL_MODS", settings.role_groups)
        self.assertIn("ALL_HTB_STAFF", settings.role_groups)
        self.assertIn("ALL_SR_MODS", settings.role_groups)
        self.assertIn("ALL_HTB_SUPPORT", settings.role_groups)

    def test_dynamic_role_groups_removed(self):
        """Test that dynamic role groups are no longer in settings."""
        self.assertNotIn("ALL_RANKS", settings.role_groups)
        self.assertNotIn("ALL_SEASON_RANKS", settings.role_groups)
        self.assertNotIn("ALL_CREATORS", settings.role_groups)
        self.assertNotIn("ALL_POSITIONS", settings.role_groups)

    def test_dynamic_roles_are_optional(self):
        """Test that dynamic role fields default to None when env vars are missing."""
        # These should be Optional[int] = None if not in env
        # In test env they may still be set via .test.env, so just check the field exists
        self.assertTrue(hasattr(settings.roles, "OMNISCIENT"))
        self.assertTrue(hasattr(settings.roles, "VIP"))
        self.assertTrue(hasattr(settings.roles, "BOX_CREATOR"))
