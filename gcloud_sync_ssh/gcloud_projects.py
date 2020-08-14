from .util.cmd import cmd


def fetch_projects_data():
    projects = cmd("gcloud --quiet projects list", structured=True)
    return projects
