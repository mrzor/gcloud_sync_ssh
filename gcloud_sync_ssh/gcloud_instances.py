from subprocess import CalledProcessError

from loguru import logger

from .util.cmd import cmd
from .util.globbing import matches_any


def _instance_zone(instance_data):
    """Removes most of a zone URI and returns the 'canonical' zone identifier situated
at the very end of the URI path.."""
    zone = instance_data.get('zone', None)
    if not zone:
        return None

    if '/' in zone:
        zone = zone[zone.rindex("/") + 1:]

    return zone


def _instance_hostname(project_id, instance_data):
    """Returns instance hostname following `gcloud compute config-ssh` conventions."""
    return f"{instance_data['name']}.{_instance_zone(instance_data)}.{project_id}"


def _instance_ip(instance_data):
    ips = []

    for net_int in instance_data['networkInterfaces']:
        ips += [ac.get("natIP", None)for ac in net_int['accessConfigs']]
    ips = list(filter(None, ips))

    if len(ips) == 0:
        return None

    if len(ips) > 1:
        logger.warning(f"Instance {instance_data['name']} has several exteral IPs. "
                       "The first one will be arbitrarily used")

    ip = ips[0]  # We can probably do better than this. XXX cheat and see how gcloud does it
    return ip


# XXX I'm interested in other statuses as well to possibly differenciate between
#     deleted and stopped instances
def _fetch_instances_data(project_id):
    list_args = ["gcloud", "--quiet", "compute", "instances", "list"]
    if project_id:
        list_args.insert(2, f"--project={project_id}")

    try:
        instances = cmd(list_args, structured=True)
    except CalledProcessError:
        return []

    if len(instances) == 0:
        project_label = f"project {project_id}" if project_id else "active project"
        logger.warning(f"No running instances in {project_label}")

    return instances


def build_host_dict(project_id, instance_globs):
    """Builds a <instance-fake-hostname> => {ip: <instance_ip>, id: <instance_id} map
       for given project_id and globs"""
    result = {}

    for instance_data in _fetch_instances_data(project_id):
        if not matches_any(instance_data['name'], instance_globs):
            continue

        ip = _instance_ip(instance_data)
        if ip:
            minidata = {'ip': ip,
                        'id': instance_data['id'],
                        'status': instance_data['status']}
            result[_instance_hostname(project_id, instance_data)] = minidata

    return result
