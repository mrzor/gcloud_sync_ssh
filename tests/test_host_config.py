from gcloud_sync_ssh.host_config import HostConfig


def test_empty():
    hc = HostConfig()
    assert not hc.minidict()


def test_default_lines():
    hc = HostConfig(HostName="4.4.4.4", CertificateFile="exists-or-not-we-dont-check")
    ls = hc.lines()
    assert ls == ['    CertificateFile exists-or-not-we-dont-check\n', '    HostName 4.4.4.4\n']


def test_ordering_default():
    hc = HostConfig(HostName="192.168.0.20", User="mrzor", ForwardX11=False)
    assert hc.lines() == ['    ForwardX11 no\n',
                          '    HostName 192.168.0.20\n',
                          '    User mrzor\n']


def test_ordering_fully_specified():
    hc = HostConfig(HostName="192.168.0.20", User="mrzor", ForwardX11=False)
    ordering = ['User', 'HostName', 'ForwardX11']
    assert hc.lines(ordering=ordering) == ['    User mrzor\n',
                                           '    HostName 192.168.0.20\n',
                                           '    ForwardX11 no\n']


def test_ordering_partially_specified():
    hc = HostConfig(HostName="192.168.0.20", User="mrzor", ForwardX11=False)
    ordering = ['User']
    assert hc.lines(ordering=ordering) == ['    User mrzor\n',
                                           '    ForwardX11 no\n',
                                           '    HostName 192.168.0.20\n']


def test_ordering_extra_keys():
    hc = HostConfig(HostName="192.168.0.20", User="mrzor", ForwardX11=False)
    ordering = ['User', 'BindAddress']
    assert hc.lines(ordering=ordering) == ['    User mrzor\n',
                                           '    ForwardX11 no\n',
                                           '    HostName 192.168.0.20\n']


def test_custom_casing():
    hc = HostConfig(HostName="192.168.0.20", User="mrzor")
    assert hc.lines(casings=["HoStNaMe", "USER"]) == ['    HoStNaMe 192.168.0.20\n',
                                                      '    USER mrzor\n']


def test_custom_separator():
    hc = HostConfig(User="narcissus")
    assert hc.lines(separator="=") == ['    User=narcissus\n']
    assert hc.lines(separator=" = ") == ['    User = narcissus\n']


def test_custom_indent():
    hc = HostConfig(User="narcissus")
    assert hc.lines(indent="") == ['User narcissus\n']
    assert hc.lines(indent="\t") == ['\tUser narcissus\n']


def test_quoting():
    hc = HostConfig(User="narcissus")
    assert hc.lines(force_quotes=True) == ['    User "narcissus"\n']

    hc = HostConfig(User="narcissus maximus")
    assert hc.lines() == ['    User "narcissus maximus"\n']
    assert hc.lines(force_quotes=True) == ['    User "narcissus maximus"\n']


def test_multiple_values():
    hc = HostConfig(LocalForward=['lf1', 'lf2', 'lf3'], User="narcissus")
    assert len(hc.lines()) == 4
