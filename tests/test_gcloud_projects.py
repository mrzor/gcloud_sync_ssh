from gcloud_sync_ssh.gcloud_projects import fetch_projects_data


def test_simple_fetch(stubbed_gcloud_ctx):
    stubbed_gcloud_ctx.seed_db("projects", "projects_1")
    res = fetch_projects_data()
    assert len(res) == 3
    assert type(res) == list
