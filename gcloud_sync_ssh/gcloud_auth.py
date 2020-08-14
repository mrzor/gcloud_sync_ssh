import json

from loguru import logger

from .gcloud_config import gcloud_config_get
from .util.cmd import cmd


class _GCloudSavedAuth(object):
    """A ContextManager that will save currently used gcloud authentication upon entering
and restore the saved authentication upon exiting."""
    def __enter__(self):
        # Load currently used authentication
        # res = cmd("gcloud auth list --format=json")
        # res_data = json.loads(res.stdout)
        # active_accounts = [account for account in res_data if account["status"] == "ACTIVE"]
        # assert len(active_accounts) <= 1
        self.previously_used_account = gcloud_config_get("core/account") or ""
        logger.trace(f"Memorizing in-use account '{self.previously_used_account}'")

    def __exit__(self, type, value, traceback):
        # Restore previously used authentication
        cmd(["gcloud", "config", "set", "account", self.previously_used_account])
        logger.trace(f"Restored previously used account '{self.previously_used_account}'")


class GCloudServiceAccountAuth(_GCloudSavedAuth):
    """A ContextManager used to change the gcloud authentication to a specific
       service account. The previously used authentication is restored upon exiting.

       See: gcloud auth activate-service-account --help"""
    def __init__(self, service_account_key_path):
        self.service_account_key_path = service_account_key_path

    def __enter__(self):
        # Read service account identifier from file
        with open(self.service_account_key_path, "r") as f:
            service_account_data = json.load(f)
            self.service_account_identifier = service_account_data["client_email"]

        super().__enter__()  # Save current auth

        # Activate service account
        cmd(["gcloud", "auth", "activate-service-account",
             f"--key-file={self.service_account_key_path}"])
        logger.trace(f"Authenticated with '{self.service_account_key_path}'")


class GCloudAccountIdAuth(_GCloudSavedAuth):
    """A ContextManager used to change the gcloud authentication to a specific account-id.
       The user will be prompter / a browser might be opened if gcloud doesn't have cached
       credentials for this account.

       See: gcloud auth login --help"""
    def __init__(self, account_id):
        self.account_id = account_id

    def __enter__(self):
        super().__enter__()  # Save current auth
        cmd(["gcloud", "auth", "login", self.account_id])  # Activate new auth
