import os
from typing import List, Optional

from pydantic import BaseModel

from .util.case_insensitive_dict import CaseInsensitiveDict
from .util.cased_enum import LowercaseStringEnum


class InstanceStatusEnum(LowercaseStringEnum):
    # Values at https://cloud.google.com/compute/docs/reference/rest/v1/instances/get
    provisionning = 'provisionning'
    running = 'running'
    staging = 'staging'
    stopped = 'stopped'
    suspending = 'suspending'
    suspended = 'suspended'
    repairing = 'repairing'
    terminated = 'terminated'


class AddressFamilyParam(LowercaseStringEnum):
    # Values from ssh_config (5)
    any = "any"
    inet = "inet"
    inet6 = "inet6"


class StrictHostKeyCheckingParam(LowercaseStringEnum):
    yes = "yes"
    accept_new = "accept_new"
    no = "no"
    off = "off"
    ask = "ask"


class TunnelParam(LowercaseStringEnum):
    yes = "yes"
    point_to_point = "point-to-point"
    ethernet = "ethernet"
    no = "no"


class YesNoAskParam(LowercaseStringEnum):
    yes = "yes"
    no = "no"
    ask = "ask"


def _key_casing(casings_map, key):
    return casings_map.get(key, key)


class HostConfig(BaseModel):
    """A model for hostname configuration in SSH config.

The main purpose for this class is to provide fairly strict validation of allowable SSH config
keywordsarguments pairs ("kwarg" pairs, or simply "kwargs").

It was manually made based on OpenSSH 8.2p1 acceptable options.
Not all enums are properly typed.
"""
    # This could be fleshed out into a full SSHconfig library assuming
    # 1) Most of this code can be automatically generated
    #    Basing oneself on the _source code_ seems the best option for that
    #    Parsing the man page or --help might miss lists, enums or other subtelties.
    # 2) Different versions of the OpenSSH config can be supported

    # NB: In the context of gcloud_sync_ssh, this is only used for
    #     __new__ hosts. Existing hosts are parsed into a CaseInsensitiveDict that
    #     preserves original file casing, which is desirable.

    # One could use this class to write an SSH config linting tool, with some additional
    # effort (notably, Hostname/Match support)

    # Pydantic config
    class Config:
        extra = 'forbid'

    gcp_status: Optional[InstanceStatusEnum]

    # commonly used parameters
    # hostname: Optional[str]
    # host_key_alias: Optional[str]
    # ip: Optional[str]
    # identity_file: Optional[str]
    # identities_only: bool = True
    # check_host_ip: bool = False

    # all other ssh_config(5) parameters in alphabetical order
    AddressFamily: Optional[AddressFamilyParam]
    BatchMode: Optional[bool]
    BindAddress: Optional[str]
    CanonicalDomains: Optional[str]
    CanonicalizeFallback_local: Optional[bool]
    CanonicalizeHostname: Optional[bool]
    CanonicalizeMaxDots: Optional[int]
    CanonicalizePermittedCNAMEs: Optional[str]
    CASignatureAlgorithms: Optional[str]
    CertificateFile: Optional[str]
    ChallengeResponseAuthentication: Optional[bool]
    CheckHostIP: Optional[bool]
    Ciphers: Optional[str]
    ClearAllForwardings: Optional[bool]
    Compression: Optional[bool]
    ConnectionAttempts: Optional[int]
    ConnectTimeout: Optional[int]
    ControlMaster: Optional[str]
    ControlPath: Optional[str]
    ControlPersist: Optional[bool]
    DynamicForward: Optional[List[str]]
    EnableSSHKeysign: Optional[bool]
    EscapeChar: Optional[str]
    ExitOnForwardFailure: Optional[bool]
    FingerprintFash: Optional[str]
    ForwardAgent: Optional[bool]
    ForwardX11: Optional[bool]
    ForwardX11Timeout: Optional[str]
    ForwardX11Trusted: Optional[bool]
    GatewayPorts: Optional[bool]
    GlobalKnownHostsFile: Optional[str]
    GSSAPIAuthentication: Optional[bool]
    GSSAPIClientIdentity: Optional[str]
    GSSAPIDelegateClientCredentials: Optional[bool]
    GSSAPIKeyExchange: Optional[bool]
    GSSAPIRenewalForcesRekey: Optional[bool]
    GSSAPIServerIdentity: Optional[str]
    GSSAPITrustDns: Optional[bool]
    GSSAPIKexAlgorithms: Optional[str]
    HashKnownHosts: Optional[bool]
    HostbasedAuthentication: Optional[bool]
    HostbasedKeyTypes: Optional[str]
    HostKeyAlgorithms: Optional[str]
    HostKeyAlias: Optional[str]  # common for our usecase
    HostName: Optional[str]  # common/mandatory (after a while) for this usecase
    IdentitiesOnly: Optional[bool]  # common for our usecase
    IdentityAgent: Optional[str]
    IdentityFile: Optional[str]  # common for our usecase
    IgnoreUnknown: Optional[str]
    Include: Optional[str]
    IPQoS: Optional[str]  # XXX it's an enum
    KbdInteractiveAuthentication: Optional[bool]
    KbdInteractiveDevices: Optional[str]
    KexAlgorightms: Optional[str]
    LocalCommand: Optional[str]
    LocalForward: Optional[List[str]]
    LogLevel: Optional[str]
    MACs: Optional[str]
    NoHostAuthenticationForLocalhost: Optional[bool]
    NumberOfPassword_prompts: Optional[int]
    PasswordAuthentication: Optional[bool]
    PermitLocalCommand: Optional[bool]
    PKCS11Provider: Optional[str]
    Port: Optional[int]
    PreferredAuthentications: Optional[str]
    ProxyCommand: Optional[str]
    ProxyJump: Optional[str]
    ProxyUseFdpass: Optional[bool]
    PubkeyAcceptedKeyTypes: Optional[str]
    PubkeyAuthentication: Optional[bool]
    RekeyLimit: Optional[str]
    RemoteCommand: Optional[str]
    RemoteForward: Optional[List[str]]
    RequestTty: Optional[str]
    RevokedHostKeys: Optional[str]
    SecurityKeyProvider: Optional[str]
    SendEnv: Optional[List[str]]
    ServerAliveCountMax: Optional[int]
    ServerAliveInterval: Optional[int]
    SetEnv: Optional[List[str]]
    StreamLocalBindMask: Optional[str]
    StreamLocalBindUnlink: Optional[bool]
    StrictHostKeyChecking: Optional[StrictHostKeyCheckingParam]
    SyslogFacility: Optional[str]
    TCPKeepAlive: Optional[bool]
    Tunnel: Optional[TunnelParam]
    TunnelDevice: Optional[str]
    UpdateHostKeys: Optional[YesNoAskParam]
    User: Optional[str]
    UserKnownHostsFile: Optional[str]
    VerifyHostKey_DNS: Optional[YesNoAskParam]
    VisualHostKey: Optional[bool]
    XAuthLocation: Optional[str]

    @classmethod
    def default_config(cls):
        """Similar to what gcloud compute config-ssh generates.
           The string rendering has forced consistent delimiters however."""
        ssh_dir = os.path.join(os.environ["HOME"], ".ssh")
        return HostConfig(IdentityFile=os.path.join(ssh_dir, "google_compute_engine"),
                          IdentitiesOnly=True,
                          CheckHostIP=False,
                          UserKnownHostsFile=os.path.join(ssh_dir, "google_compute_known_hosts"))

    def minidict(self):
        """Same as .dict() but without any None values"""
        return {k: v for k, v in self.dict().items() if v is not None}

    def lines(self, separator=" ", casings=[], indent="    ", force_quotes=False,
              ordering=[]):
        """Returns this host configuration data as a list of LF-terminated strings.

           Formatting is pretty flexible. If you don't care about formatting,
           the defaults will provide a pretty consensual result.

           Line ordering
           -------------

           Configuration lines will be sorted in alphabetical order unless the ordering
           parameter is set.

           The ordering list is expected to be a list of configuration keywords in ssh_config()
           format (casing does not matter). For instance, "forwardx11", "ForwardX11" and
           "FoRwArDX11" all refer to the same SSH config keyword and are valid ordering entries.

           If the configuration does not contain a config-parameter specified by the ordering,
           it will be skipped, unless the check_ordering parameter is set.

           If the configuration contains more parameters than the ordering list specifies,
           the extra parameters will be printed after the ordered parameters, in alphabetical
           order.



           Keyword casing
           --------------

           Fields will be cased with canonical ssh_config(5) casing unless alternative
           casings as provided.


           Keyword-Value (Line) formatting
           -------------------------------

           Separator can be any string. Valid SSH configs accept space or '=' or ' = ' or
           similar strings made of spaces and at most one equal sign.

           Indent will be used to indent keyword assignments after the Host block.

           Setting force_quotes=True will place double quotes (`"`) around every value.
           Otherwise quotes will only be added when the value contains spaces.

           Limitations
           -----------

           Separator, indent and separator cannot be set per keyword.

           Examples
           --------
           XXX
"""

        # XXX validate separator, ordering, indent

        # Build up a dict of everything we accept as a SSH config keyword
        canonical_casings_map = CaseInsensitiveDict({k: k for k in self.dict().keys()})

        # User given custom casings
        casings_map = CaseInsensitiveDict({casing: casing for casing in casings})

        # Build a parameter (keyword->attribute) dict
        params = CaseInsensitiveDict()
        for k, v in self.dict().items():
            if v is None:
                continue
            params[_key_casing(casings_map, canonical_casings_map[k])] = v

        def _format_kv(k, v):
            if isinstance(v, bool):
                v = "yes" if v else "no"
            v = f'"{v}"' if (force_quotes or " " in v) else v
            return f"{indent}{k}{separator}{v}\n"

        # Output buffer
        lines = []

        # Output ordered lines first
        for keyword in ordering:
            value = params.pop(keyword, None)
            if value is not None:
                cased_key = _key_casing(casings_map, canonical_casings_map[keyword])
                lines.append(_format_kv(cased_key, value))

        # Order remaining lines alphabetically and append them
        sorted_params = sorted(params.items(), key=lambda e: e[0])
        lines += [_format_kv(p[0], p[1]) for p in sorted_params]

        return lines
