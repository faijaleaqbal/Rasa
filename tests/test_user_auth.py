import os
import unittest
from unittest.mock import patch

from actions.commands import handle_slash_command
from actions import db


class TestUserAuthorization(unittest.TestCase):
    """Tests user management commands and access control."""

    def test_user_authorization_lifecycle(self):
        target_uid = "9876543210"
        admin_uid = "1122334455"

        with patch.dict(os.environ, {"ALLOWED_TELEGRAM_USER_ID": admin_uid}):
            # Verify admin check
            self.assertTrue(db.is_admin_user(admin_uid))
            self.assertFalse(db.is_admin_user(target_uid))

            # Initially target is not authorized
            db.remove_authorized_user(target_uid)
            self.assertFalse(db.is_user_authorized(target_uid))

            # Non-admin attempt to add user -> Denied
            res_denied = handle_slash_command(f"/adduser {target_uid} Bob", target_uid, "chat_1")
            self.assertTrue(res_denied["handled"])
            self.assertIn("Access Denied", res_denied["text"])

            # Admin adds user -> Allowed
            res_add = handle_slash_command(f"/adduser {target_uid} Bob", admin_uid, "chat_1")
            self.assertTrue(res_add["handled"])
            self.assertIn("Authorized", res_add["text"])

            # Verify user is authorized in DB
            self.assertTrue(db.is_user_authorized(target_uid))

            # List authorized users
            res_list = handle_slash_command("/users", admin_uid, "chat_1")
            self.assertTrue(res_list["handled"])
            self.assertIn(target_uid, res_list["text"])

            # Admin removes user
            res_remove = handle_slash_command(f"/removeuser {target_uid}", admin_uid, "chat_1")
            self.assertTrue(res_remove["handled"])
            self.assertIn("Revoked", res_remove["text"])

            # Verify user is no longer authorized
            self.assertFalse(db.is_user_authorized(target_uid))

    def test_admin_cannot_be_removed(self):
        admin_uid = "1122334455"
        with patch.dict(os.environ, {"ALLOWED_TELEGRAM_USER_ID": admin_uid}):
            res_remove = handle_slash_command(f"/removeuser {admin_uid}", admin_uid, "chat_1")
            self.assertTrue(res_remove["handled"])
            self.assertIn("Cannot remove primary administrator", res_remove["text"])


if __name__ == "__main__":
    unittest.main()
