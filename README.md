# gcloud_sync_ssh

An improved version of `gcloud compute config-ssh`, a convenient way to setup connectivity to your virtual machines hosted within GCP.

This tools has some benefits:
* Can work on several projects at once
* Only sets up connectivity by setting Hostnames in SSH config.
  * No side effects in project or instance metadata (madness!)
  * Works quite faster because updating project metadata is _slow_
* Can generate user-specified SSH config for all hosts
  * Host specific config is not handled by the tool. Edit your configuration instead.
* Can remove stopped ('terminated', in GCP parlance) instances from config
* Generates smallest possible diff by preserving casing, separators and whitespace
  * Smallest diff = highest review impact.


And some drawbacks:
* If the instance is not configured to let you in, this tool will _not_ fix that.

## Install

- `pipx install gcloud_sync_ssh`

Use manually. I run mine in an hourly cron, and occasionally manually.

## Run from sourcep

- Clone it
- (Optionally, create a virtualenv you preferred way)
- `pip install -r requirements.txt`
- `python -m gcloud_sync_ssh`

## Usage

- `gcloud_sync_ssh --help`

## Examples

## Limitations

* SSH kwarg assignments that accept multiple values, like `DynamicForward` or `SendEnv`, are not supported. (TODO: accept multiple `-kw` opts and set them correctly)
* Only works with one account at a time (TODO: Support iterating through all accounts exposed by `gcloud auth list`)
* Can only be setup through commandline options (TODO: Support configuration file on top of gazillion command line options)
* Is single-threaded synchronous (TODO: Support parallelism with either threads or async)
* Formatting of new hosts is not _exactly_ the same as what `gcloud compute config-ssh` does. Notably, it has consistent space delimiting instead of having `=` on some lines and ` ` on others. (Probably won't fix)
* Doesn't remove _deleted_ instances, just _stopped_ ones. (TODO: Support removing deleted instances as well)

### Alternatives

Using this script to setup connectivity should work well enough for ~hundreds of instances whose external IPs change ~daily. I use it for ~dozens of instances whose IPs change ~daily.

If your external IPs change very frequently, or if you have thousands of instance, this tool can still be a useful crutch, but you may want to look into alternatives.

Here are my thoughts on the subject, ordered by effort required.

* Setup a shared private subnetwork between your instances, and you'll get DNS with `.internal` TLD for free. A jumpbox is a way to get access to your instances. [ XXX Other ways ? ]
* Use some form of service registration/discovery. Hashicorp Consul comes to mind.
* Use Google Logging to process instance startup/showdown logs. Tap those into Pub/Sub. Write a lambda function that produces a `hosts` file or a SSH config file. Store that in Storage at a well known URI. Download it every minute on all your machines.
* Same as above, but generate a zone file and feed that to a DNS server you control.
* Move all your things to K8s and welcome your new YAML overlords.

## Contributing

Grab a TODO, an issue or bring your own issue to solve.

### Testing


## License
