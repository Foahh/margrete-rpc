import pytest
from margrete_rpc import Margrete, MargreteDiscoveryError, list_instances
from margrete_rpc.discovery import pipe_name_for, resolve_pipe_name


def test_list_instances_filters_pipe_names(monkeypatch):
    monkeypatch.setattr(
        "margrete_rpc.discovery.os.listdir",
        lambda _path: ["margrete-0421", "other", "margrete-7", "margrete-0999", "margrete-abcd"],
    )

    instances = list_instances(validate=False)

    assert [(item.instance_id, item.pipe_name) for item in instances] == [
        ("0421", "margrete-0421"),
        ("0999", "margrete-0999"),
    ]


def test_list_instances_returns_empty_when_pipe_dir_missing(monkeypatch):
    def _fail(_path: str) -> list[str]:
        raise FileNotFoundError

    monkeypatch.setattr("margrete_rpc.discovery.os.listdir", _fail)
    assert list_instances(validate=False) == []


def test_list_instances_filters_unreachable_pipes(monkeypatch):
    monkeypatch.setattr(
        "margrete_rpc.discovery.os.listdir",
        lambda _path: ["margrete-0001", "margrete-0002"],
    )
    monkeypatch.setattr(
        "margrete_rpc.discovery._can_ping",
        lambda pipe_name, _timeout: pipe_name == "margrete-0002",
    )

    instances = list_instances(validate=True, timeout=0.1)

    assert [item.pipe_name for item in instances] == ["margrete-0002"]


def test_resolve_pipe_name_uses_single_live_instance(monkeypatch):
    monkeypatch.setattr(
        "margrete_rpc.discovery.os.listdir",
        lambda _path: ["margrete-0421"],
    )
    monkeypatch.setattr("margrete_rpc.discovery._can_ping", lambda _pipe, _timeout: True)

    assert resolve_pipe_name(timeout=1.0) == "margrete-0421"


def test_resolve_pipe_name_rejects_ambiguous_instances(monkeypatch):
    monkeypatch.setattr(
        "margrete_rpc.discovery.os.listdir",
        lambda _path: ["margrete-0001", "margrete-0002"],
    )
    monkeypatch.setattr("margrete_rpc.discovery._can_ping", lambda _pipe, _timeout: True)

    with pytest.raises(MargreteDiscoveryError, match="multiple"):
        resolve_pipe_name(timeout=1.0)


def test_resolve_pipe_name_selects_explicit_instance_without_listing():
    assert resolve_pipe_name("0421") == "margrete-0421"
    assert resolve_pipe_name("margrete-0999") == "margrete-0999"


def test_pipe_name_for_round_trips():
    assert pipe_name_for("0421") == "margrete-0421"
    assert pipe_name_for("margrete-0421") == "margrete-0421"


def test_margrete_requires_single_discovered_instance(monkeypatch):
    monkeypatch.setattr("margrete_rpc.discovery.os.listdir", lambda _path: [])

    with pytest.raises(MargreteDiscoveryError, match="no running"):
        Margrete(timeout=0.1)


def test_margrete_rejects_instance_with_transport():
    class _Transport:
        def request(self, envelope):  # pragma: no cover
            raise AssertionError(envelope)

    with pytest.raises(ValueError, match="instance cannot be used with transport"):
        Margrete("0421", transport=_Transport())


def test_list_instances_treats_unexpected_ping_errors_as_unreachable(monkeypatch):
    class _Boom:
        def request(self, envelope):
            raise Exception("The pipe is being closed.")

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        "margrete_rpc.discovery.os.listdir",
        lambda _path: ["margrete-0421"],
    )
    monkeypatch.setattr(
        "margrete_rpc.discovery.create_transport",
        lambda *_args, **_kwargs: _Boom(),
    )

    assert list_instances(validate=True, timeout=0.1) == []
