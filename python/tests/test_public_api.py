import margrete_rpc


def test_root_package_exports_client_surface_only():
    assert set(margrete_rpc.__all__) == {
        "CallbackTracer",
        "Margrete",
        "MargreteDiscoveryError",
        "MargreteError",
        "MargreteInstance",
        "MargreteProtocolError",
        "MargreteRemoteError",
        "MargreteTimeoutError",
        "MargreteVersionError",
        "NoopTracer",
        "ServerStatus",
        "TraceEvent",
        "Tracer",
        "__version__",
        "list_instances",
    }
    assert not hasattr(margrete_rpc, "Tap")
