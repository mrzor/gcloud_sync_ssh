import json

from gcloud_sync_ssh.gcloud_auth import GCloudAccountIdAuth, GCloudServiceAccountAuth


def test_login(stubbed_gcloud_ctx):
    # Stub config
    with stubbed_gcloud_ctx.db("config") as db:
        db.update({"accounts": ["test-a@gmail.com", "test-b@gmail.com"],
                   "account": "test-a@gmail.com"})

    # Do the auth
    with GCloudAccountIdAuth("test-b@gmail.com"):
        with stubbed_gcloud_ctx.db("config") as db:
            assert db["account"] == "test-b@gmail.com"

    # Ensure the initial account got restored
    with stubbed_gcloud_ctx.db("config") as db:
        assert db["account"] == "test-a@gmail.com"

    # Ensure we ran the expected amount of commands
    with stubbed_gcloud_ctx.db("cmd_log") as db:
        assert len(db) == 3


def test_service_account(stubbed_gcloud_ctx):
    sa_email = "dummy-sa@dummy-proj.iam.gserviceaccount.com"

    # Stub config
    with stubbed_gcloud_ctx.db("config") as db:
        db.update({"account": "test-before@gmail.com"})

    # Stub service account credentials
    with stubbed_gcloud_ctx.tmpfile("credentials.json") as f:
        f.write(json.dumps({"client_email": sa_email}))
        f.flush()

        # Do the auth
        with GCloudServiceAccountAuth(f.name):
            with stubbed_gcloud_ctx.db("config") as db:
                assert db["account"] == sa_email

    # Ensure the initial account got restored
    with stubbed_gcloud_ctx.db("config") as db:
        assert db["account"] == "test-before@gmail.com"

    # Ensure we ran the expected amount of commands
    with stubbed_gcloud_ctx.db("cmd_log") as db:
        assert len(db) == 3
