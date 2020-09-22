# `gcloud_sync_ssh`

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

I've used it for a couple of months for my modest needs and it did the job flawlessly. YMMV - see 'Limitations' below.

## Install

#### With pipx

- `pipx install gcloud_sync_ssh`

#### Run from source

- Clone it
- Recommended: create a virtualenv with [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv
  - i.e. `pyenv virtualenv 3.6 gcloud_sync_ssh`
- `pip install -r requirements.txt`
  - N.B. This will install development dependencies as well
- `python -m gcloud_sync_ssh`

## Usage

- `gcloud_sync_ssh --help`

The tool works in four phases. It optionally changes the gcloud authentication context, then it enumerates projects and instances, then it updates your SSH config in memory and finally saves it after making a backup and showing you the diff.

#### Preliminary: Choose which config file to edit

By default, `gcloud_sync_ssh` edits the standard `~/.ssh/config`. This will be fine for most uses. It may be changed with `-c/--config`.

Some people prefer the tool to operate on an isolated file, like `~/.ssh/config.auto`. A few things to keep in mind if you go down that path:

- You need to `chmod 0600 ~/.ssh/config.auto` for SSH to read it
- You need to add `Include ~/.ssh/config.auto` to your existing `~/.ssh/config` _before_ any `Match` or `Host` block.
- Alternatively, use `ssh -F ~/.ssh/config.auto` instead of setting up the `Include`.

#### First phase: Authentication

First it will optionally change your `gcloud` authentication context as desired, using the
`--login` option for email accounts or `--service-account` option for service accounts.


If none of these options are specified, `gcloud_sync_ssh` will not touch modify your gcloud
authentication settings - and will function with your current settings.


Your current settings will be restored once the tools exits.


Be aware that authentication is a user-level setting. When using special authentication, avoid running `gcloud` while `gcloud_sync_ssh` is running. This also applies to other tools that piggy back on gcloud auth, like Terraform gcloud backend in application-default mode.

#### Second phase: Enumeration

You may select a project with the `--project` option. This option can be specified several times to select multiple projects. This option accepts `fnmatch`-style globbing (i.e. using `*`, `?` ...).

- Just one project : `--project my-project-name`
- A couple of projects: `--project project-web-1 --project-web-2`
- A bunch of projects: `--project 'project-web-*'` (Beware shell quoting rules for globbing characters)
- All projects : `--all-projects`

#### Third phase: Configuration updates

There are quite a few cases to consider.

##### Updates

The simplest case is updates : running instances already in your configuration, but the external IP changes.

Your configuration will be updated in place and nothing else will change. There are no options controlling this behavior.

##### Deletions

Then we have deletions:

- Instances in your configuration that have entered the `STOPPED` status will be removed from your configuration. You can disable this using the `-nrs|--no-remove-stopped` flag.
- Deleted instances (or instances that have otherwise vanished) will be removed from your SSH config _if and only if_ it's possible to attribute the instance to a project using its hostname i.e. its hostname terminates by `.<project-name>`. You can disable that using the `-nrv|--no-remove-vanished` flag.

##### Additions

Finally, we have additions. A new `Host` block will be added to your configuration for newly detected instances. The complexity comes from the many ways to specify how that block will be generated. There are two parts to this : the 'template' is the set of options that doesn't change from host to host, and the 'specifics' which are the couple of options that are allowed to vary.


The _`Host` template_ is computed as such:

1. The tool has builtin defaults. You can see them with `--no-inference --debug-template`.
2. The tool tries to _infer_ a template from your existing configuration. Any keyword-argument pair that is shared by _every_ `Host` block in your config is added to this template. The inferred values override the defaults. You can turn this off by passing the `--no-inference` flag. You can see the results of this stage by passing `-dt|--debug-template`.
3. You can specify additions to the template using the `-kw/--kwarg` option possibly several times.

Here is an exemple of a Host template that overrides defaults :

    $ gcloud_sync_ssh --debug-template --no-inference -kw IdentityFile=/secret/id_rsa -kw UserKnownHostsFile=/data/known_hosts
    2020-09-07 20:23:18.290 | INFO     | Displaying host template
        CheckHostIP no
        IdentitiesOnly yes
        IdentityFile /secret/id_rsa
        UserKnownHostsFile /data/known_hosts

    2020-09-07 20:23:18.291 | INFO     | Done displaying host template

The 'specifics' are:

- The `Hostname` kwarg, that will be set to the instance external IP (or first external IP, if there are several). This is the whole point of this tool, and it cannot be controlled by an option.
- The `HostKeyAlias` kwarg, that will be set to `compute.<instance_id>`. This is what `gcloud compute config-ssh` does. This will prevent warnings because of external IP changes. You can disable generating those with `-nk|--no-host-key-alias`.

#### Fourth phase: Configuration save

You don't have to blindly trust the tool. By default it will show you the diff and ask for approval before saving - while still saving a backup.

If you want to use it from `cron` or CI, this behavior might be counterproductive, so it can be disabled:

- Don't show diff and don't ask for approval: `--not-interactive`
- Don't save a backup: `--no-backup`

## Examples

## Limitations

* Only works with one account at a time (TODO: Support iterating through all accounts exposed by `gcloud auth list`)
* Can only be setup through commandline options (TODO: Support configuration file on top of gazillion command line options)
* Doesn't support "jump box" setups or VPN setups - where you connect to the private IP address of your instances. (TODO: Support that!)
* Is single-threaded synchronous (TODO: Support parallelism with either threads or async)
* Formatting of new hosts is not _exactly_ the same as what `gcloud compute config-ssh` does. Notably, it has consistent space delimiting instead of having `=` on some lines and ` ` on others. (Probably won't fix)
* There are no ways to setup 'specific' options other than the two builtins for new `Host`. (TODO: Accept Python plugins to allow arbitrarily complex schemes to add/edit SSH config per host)
* Vanishing/deleted instances can only be removed from your config if their hostname is suffixed by `.<project-name>`. This is the GCP default. I found no other way to attribute a Host in your SSH config to a given SSH project. Workaround: remove everything with `gcloud compute config-ssh --remove` then use `gcloud_sync_ssh` as usual. (TODO: Support `--overwrite` flag that removes everything in the config block before running)
* Instances in transitional states and suspended states are completely ignored by the tool.

The above are roughly sorted given how concerning they are to me. None are preventing me to achieve my goals with the tool - but some may hinder you.

### Alternatives

Using this script to setup connectivity should work well enough for ~hundreds of instances whose external IPs change ~daily. I use it for ~dozens of instances whose IPs change ~daily.

If your external IPs change very frequently, or if you have thousands of instances, this tool can still be a useful crutch, but you may want to look into alternatives.

Here are my thoughts on the subject, ordered by effort required.

* Setup a shared private subnetwork between your instances, and you'll get DNS with `.internal` TLD for free. A jumpbox is a way to get access to your instances. [ XXX Other ways ? ]
* Use some form of service registration/discovery. Hashicorp Consul comes to mind.
* Use Google Logging to process instance startup/showdown logs. Tap those into Pub/Sub. Write a lambda function that produces a `hosts` file or a SSH config file. Store that in Storage at a well known URI. Download that in whichever way you like, then `Include` it in your SSH config.
* Same as above, but generate a zone file and feed that to a DNS server you control.
* Move all your things to K8s and welcome your new YAML overlords. You can't ssh into anything without using `kubectl` but that's okay.

## Contributing

Grab a TODO from the _Limitations_ list, an issue or bring your own issue to solve.

If it makes sense, please add tests and make sure they pass with `python -m pytest`.

## License

The code contained in this repository is licensed under the terms of the [MIT license](LICENSE) unless otherwise noted in the source code file.
