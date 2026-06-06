import margrete_rpc


def test_root_package_exports_sdk_surface_only():
    assert set(margrete_rpc.__all__) == {
        "CallbackTracer",
        "Margrete",
        "MargreteDiscoveryError",
        "MargreteError",
        "MargreteInstance",
        "MargreteProtocolError",
        "MargreteRemoteError",
        "NoopTracer",
        "ServerStatus",
        "TraceEvent",
        "Tracer",
        "discovery_dir",
        "list_instances",
        "resolve_endpoint",
    }
    assert not hasattr(margrete_rpc, "Tap")
