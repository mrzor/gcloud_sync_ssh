import json
import os
import subprocess

from loguru import logger


# NB: I want this to be compatible with Python 3.6+
def cmd(args, check=True, pipe=True, cwd=None,
        encoding="UTF-8", debuglog=True, structured=False):
    """A helper to run subprocess commands.

       pipe=True will 'swallow' stdout/stderr in memory
       (and can later be check using res.stdout/res.stderr)

       pipe=False will reuse current process stderr/stdin

       structured=True adds `--format=json` to the arguments and returns the parsed
       JSON output instead of the subprocess result."""

    if isinstance(args, str):
        args = args.split(" ")

    if structured:
        args.append("--format=json")

    args_str = ' '.join(args)

    # This can be elegantly replaced by capture_output=pipe in Python 3.7+
    stdout, stderr = None, None
    if pipe:
        stdout, stderr = subprocess.PIPE, subprocess.PIPE

    if debuglog:
        logger.debug(f"cmd: {args_str}")

    res = subprocess.run(args, stdout=stdout, stderr=stderr,
                         cwd=cwd, env=os.environ, encoding=encoding)
    if check:
        if res.returncode != 0:
            if pipe and encoding:
                logger.error(f"cmd `{args_str}` exit code {res.returncode}\n{res.stderr}")
            else:
                logger.error(f"cmd `{args_str}` exit code {res.returncode}")
        res.check_returncode()

    if structured and pipe:
        return json.loads(res.stdout)

    return res
