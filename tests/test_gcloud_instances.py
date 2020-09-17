from subprocess import CalledProcessError

import pytest

from gcloud_sync_ssh.gcloud_instances import build_host_dict


def test_simple_host_dict(stubbed_gcloud_ctx, raise_on_gcloud_instance_sync):
    stubbed_gcloud_ctx.seed_db("instances", "instances_1")
    res = build_host_dict("stub-project-1", [])
    assert len(res) == 2
    assert "stubbed_instance_0.us-central1-b.stub-project-1" in res
    assert "stubbed_instance_1.us-central1-b.stub-project-1" in res

    si0 = res["stubbed_instance_0.us-central1-b.stub-project-1"]
    assert si0["ip"] is None
    assert si0["status"] == "TERMINATED"
    assert int(si0["id"]) == 1

    si1 = res["stubbed_instance_1.us-central1-b.stub-project-1"]
    assert si1["ip"] == "127.127.127.3"
    assert si1["status"] == "RUNNING"
    assert int(si1["id"]) == 2


def test_crash_behavior_usual(stubbed_gcloud_ctx):
    assert build_host_dict("crashme", []) == {}


def test_crash_behavior_testmode(stubbed_gcloud_ctx, raise_on_gcloud_instance_sync):
    with pytest.raises(CalledProcessError):
        build_host_dict("crashme", [])


def test_no_instances(caplog, stubbed_gcloud_ctx, raise_on_gcloud_instance_sync):
    stubbed_gcloud_ctx.seed_db("instances", "instances_1")
    res = build_host_dict("undefined-project", [])
    assert len(res) == 0
    assert len(caplog.records) == 2
    assert "No instances" in caplog.records[1].message


def test_instance_globbing(stubbed_gcloud_ctx, raise_on_gcloud_instance_sync):
    stubbed_gcloud_ctx.seed_db("instances", "instances_1")
    res = build_host_dict("stub-project-1", ["stubbed_instance_0*"])
    assert len(res) == 1


@pytest.mark.skip(reason="I have yet to make realistic stubs for this")
def test_multiple_external_ips(stubbed_gcloud_ctx, raise_on_gcloud_instance_sync):
    pass
