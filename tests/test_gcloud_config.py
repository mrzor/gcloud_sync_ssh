from gcloud_sync_ssh.gcloud_config import gcloud_config_get


def test_gcloud_config_get(stubbed_gcloud_ctx):
    # Stub config
    with stubbed_gcloud_ctx.db("config") as db:
        db.update({"a": ["a1", "a2", "a4"],
                   "b": {"b1": 1, "b2": 3},
                   "d": "",
                   "e": []})

    # Run some tests
    retrieved_a = gcloud_config_get("a")
    assert type(retrieved_a) == list
    assert retrieved_a[0] == "a1"

    retrieved_b = gcloud_config_get("b")
    assert type(retrieved_b) == dict
    assert retrieved_b["b2"] == 3

    retrieved_c = gcloud_config_get("c")
    assert retrieved_c is None
