from .util.cmd import cmd


def gcloud_config_get(key):
    """Retrieves a configuration value using gcloud config get-value"""
    res = cmd(["gcloud", "config", "get-value", key], structured=True)
    return res
