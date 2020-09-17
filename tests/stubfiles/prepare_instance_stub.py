#!/usr/bin/env python

import json
import re

import click


_INSTANCE_KEYS = ["creationTimestamp", "id", "machineType",
                  "name", "selfLink", "status", "zone", "networkInterfaces"]

_SELF_LINK_RE = re.compile(
    r"^(?P<prefix>https://www.googleapis.com/compute/v.?/projects/)"
    r"(?P<project>[^/]+)(?P<infix>/zones/us-central1-b/instances/)"
    r"(?P<instance>.+)$"
)
_PROJECT_RE = re.compile(r"^(?P<prefix>.+/projects/)(?P<project>[^/]+)(?P<suffix>.*)$")

_STUB_PROJECT_NAMES = {}
_STUB_IPS = {}
_STUB_IDS = {}


def _select_keys(dict, keys):
    # Clojure-inspired
    return {k: v for k, v in dict.items() if k in keys}


def _replace_project_references(instance_data, field):
    field_value = instance_data[field]
    match = _PROJECT_RE.match(field_value)
    assert match
    corrected_value = f"{match['prefix']}{_stub_project_name(match['project'])}{match['suffix']}"
    instance_data[field] = corrected_value


def _stub_project_name(real_project_name):
    if real_project_name not in _STUB_PROJECT_NAMES:
        _STUB_PROJECT_NAMES[real_project_name] = f"stub-project-{len(_STUB_PROJECT_NAMES) + 1}"
    return _STUB_PROJECT_NAMES[real_project_name]


def _stub_ip(real_ip):
    if real_ip not in _STUB_IPS:
        _STUB_IPS[real_ip] = f"127.127.127.{len(_STUB_IPS) + 1}"
    return _STUB_IPS[real_ip]


def _stub_id(real_id):
    if real_id not in _STUB_IDS:
        _STUB_IDS[real_id] = "{:0>19}".format(len(_STUB_IDS) + 1)
    return _STUB_IDS[real_id]


@click.command()
@click.argument("INPUT_FILE", required=True, type=click.File('r'))
def main(input_file):
    """
    Relatively simple script that strips out all un-necessary data from the output of an
    actual "gcloud compute instances list --format=json" call.

    Outputs pretty-formatted JSON to stdout.

    Use this to generate new stubs.
    """
    input_data = json.load(input_file)

    # Process input data and collect the results into result_data
    result_data = []
    for i, instance_data in enumerate(input_data):
        stub_instname = f"stubbed_instance_{i}"
        trimmed_data = _select_keys(instance_data, _INSTANCE_KEYS)

        # Fix id
        trimmed_data["id"] = _stub_id(trimmed_data["id"])

        # Fix self link
        sl_match = _SELF_LINK_RE.match(instance_data["selfLink"])
        assert sl_match
        trimmed_data["selfLink"] = sl_match['prefix'] + \
            _stub_project_name(sl_match["project"]) + \
            f"{sl_match['infix']}{stub_instname}"

        # Fix other top level links
        for field in ["zone", "machineType"]:
            _replace_project_references(trimmed_data, field)

        # Fix network links and IPs
        for nic in trimmed_data["networkInterfaces"]:
            nic.pop("fingerprint", None)
            for field in ["network", "subnetwork"]:
                _replace_project_references(nic, field)
            if "networkIP" in nic:
                nic["networkIP"] = _stub_ip(nic["networkIP"])
            for access_config in nic["accessConfigs"]:
                if "natIP" in access_config:
                    access_config["natIP"] = _stub_ip(access_config["natIP"])

        # Set name last (useful for error messages before that)
        trimmed_data["name"] = stub_instname

        # Collect
        result_data.append(trimmed_data)

    # Display items
    print(json.dumps(result_data, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
