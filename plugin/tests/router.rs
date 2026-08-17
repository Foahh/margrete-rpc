mod common;

use common::fake::FakeContext;
use margrete_rpc::meta;
use margrete_rpc::rpc::proto::{
    envelope, ApplyEditRequest, BeginEditRequest, Envelope, ErrorCode, Note, NoteType,
    StatusRequest,
};
use margrete_rpc::rpc::router::{RequestRouter, RouterStatusSnapshot};

fn ping(id: u64) -> Envelope {
    Envelope {
        request_id: id,
        body: Some(envelope::Body::PingRequest(Default::default())),
    }
}

#[test]
fn router_responds_to_ping() {
    let context = FakeContext::new();
    let router = RequestRouter::new(context.as_ptr());
    let response = router.route(&ping(11));
    assert_eq!(response.request_id, 11);
    assert!(matches!(
        response.body,
        Some(envelope::Body::PingResponse(_))
    ));
}

#[test]
fn router_responds_to_status() {
    let context = FakeContext::new();
    let router = RequestRouter::new(context.as_ptr());
    router.set_instance_id("test-instance");
    router.set_status_snapshot_provider(|| RouterStatusSnapshot {
        uptime: 42,
        pid: 1234,
        log_path: r"C:\logs\margrete_rpc.log".into(),
        config_path: r"C:\config\margrete_rpc.ini".into(),
    });
    let request = Envelope {
        request_id: 12,
        body: Some(envelope::Body::StatusRequest(StatusRequest {})),
    };
    let response = router.route(&request);
    let Some(envelope::Body::StatusResponse(status)) = response.body else {
        panic!("expected status");
    };
    assert_eq!(status.server_name, "Margrete RPC");
    assert_eq!(status.server_version, meta::PRODUCT_VERSION);
    assert_eq!(status.server_build_time, meta::BUILD_TIME);
    assert!(!status.server_build_time.is_empty());
    assert_eq!(status.api_version, meta::RPC_API_VERSION);
    assert_eq!(status.instance_id, "test-instance");
    assert_eq!(status.uptime, 42);
    assert_eq!(status.pid, 1234);
    assert_eq!(status.log_path, r"C:\logs\margrete_rpc.log");
    assert_eq!(status.config_path, r"C:\config\margrete_rpc.ini");
}

#[test]
fn router_retains_context_while_it_may_be_used_by_background_requests() {
    let first = FakeContext::new();
    let second = FakeContext::new();
    assert_eq!(first.ref_count_value(), 1);
    assert_eq!(second.ref_count_value(), 1);
    {
        let router = RequestRouter::new(first.as_ptr());
        assert_eq!(first.ref_count_value(), 2);
        router.set_context(second.as_ptr());
        assert_eq!(first.ref_count_value(), 1);
        assert_eq!(second.ref_count_value(), 2);
        router.set_context(std::ptr::null_mut());
        assert_eq!(second.ref_count_value(), 1);
    }
    assert_eq!(first.ref_count_value(), 1);
    assert_eq!(second.ref_count_value(), 1);
}

#[test]
fn router_rejects_unknown_request_body() {
    let context = FakeContext::new();
    let router = RequestRouter::new(context.as_ptr());
    let response = router.route(&Envelope {
        request_id: 13,
        body: None,
    });
    let Some(envelope::Body::ErrorResponse(err)) = response.body else {
        panic!("expected error");
    };
    assert_eq!(err.code, ErrorCode::InvalidArgument as i32);
}

#[test]
fn router_begins_edit_transaction_with_note_snapshot() {
    let mut context = FakeContext::new();
    context.set_current_tick(777);
    context.chart.add_existing_note(10).info.tick = 123;
    context.chart.add_existing_bpm(200, 180.0);
    let router = RequestRouter::new(context.as_ptr());
    let request = Envelope {
        request_id: 20,
        body: Some(envelope::Body::BeginEditRequest(BeginEditRequest {
            snapshot: true,
            ..Default::default()
        })),
    };
    let response = router.route(&request);
    let Some(envelope::Body::BeginEditResponse(begin)) = response.body else {
        panic!("expected begin");
    };
    assert_eq!(begin.current_tick, 777);
    assert!(begin.snapshot);
    assert_eq!(begin.notes.len(), 1);
    assert_eq!(begin.notes[0].id, Some(10));
    assert_eq!(begin.event_scan_lookahead_ticks, 19200);
    assert_eq!(begin.event_scan_til_ids, vec![0]);
    assert_eq!(begin.bpm_events.len(), 1);
    assert_eq!(begin.bpm_events[0].tick, 200);
}

#[test]
fn router_begins_edit_transaction_without_snapshot() {
    let mut context = FakeContext::new();
    context.set_current_tick(777);
    context.chart.add_existing_note(10).info.tick = 123;
    context.chart.add_existing_bpm(200, 180.0);
    let router = RequestRouter::new(context.as_ptr());
    let response = router.route(&Envelope {
        request_id: 23,
        body: Some(envelope::Body::BeginEditRequest(BeginEditRequest {
            snapshot: false,
            ..Default::default()
        })),
    });
    let Some(envelope::Body::BeginEditResponse(begin)) = response.body else {
        panic!("expected begin");
    };
    assert_eq!(begin.current_tick, 777);
    assert!(!begin.snapshot);
    assert!(begin.notes.is_empty());
    assert!(begin.bpm_events.is_empty());
    assert_eq!(begin.event_scan_lookahead_ticks, 19200);
    assert_eq!(begin.event_scan_til_ids.len(), 16);
}

#[test]
fn router_applies_edit_request() {
    let mut context = FakeContext::new();
    context.chart.add_existing_note(10).info.tick = 123;
    context.chart.add_existing_bpm(200, 180.0);
    let router = RequestRouter::new(context.as_ptr());
    let mut edit = ApplyEditRequest {
        replace_all_notes: true,
        ..Default::default()
    };
    edit.notes_upsert.push(Note {
        r#type: NoteType::Tap as i32,
        ..Default::default()
    });
    edit.bpm_ticks_delete.push(200);
    edit.bpm_upsert.push(margrete_rpc::rpc::proto::BpmEvent {
        tick: 240,
        bpm: 0.0,
    });
    let response = router.route(&Envelope {
        request_id: 22,
        body: Some(envelope::Body::ApplyEditRequest(edit)),
    });
    assert!(matches!(
        response.body,
        Some(envelope::Body::ApplyEditResponse(_))
    ));
    assert!(context.chart.deleted_notes >= 1);
    assert!(context.chart.appended_notes >= 1);
    assert!(context.chart.deleted_events >= 1);
    assert_eq!(context.undo.commit_count, 1);
}

#[test]
fn router_invokes_undo_and_reports_result() {
    let context = FakeContext::new();
    let router = RequestRouter::new(context.as_ptr());
    let response = router.route(&Envelope {
        request_id: 24,
        body: Some(envelope::Body::UndoRequest(Default::default())),
    });
    let Some(envelope::Body::UndoResponse(undo)) = response.body else {
        panic!("expected undo");
    };
    assert!(undo.success);
    assert_eq!(context.undo.undo_count, 1);
}

#[test]
fn router_deduplicates_root_notes_after_successful_undo() {
    let mut context = FakeContext::new();
    context.chart.add_existing_note(10);
    context.chart.add_existing_note(10);
    let router = RequestRouter::new(context.as_ptr());
    let response = router.route(&Envelope {
        request_id: 30,
        body: Some(envelope::Body::UndoRequest(Default::default())),
    });
    let Some(envelope::Body::UndoResponse(undo)) = response.body else {
        panic!("expected undo");
    };
    assert!(undo.success);
    assert_eq!(context.chart.notes.len(), 1);
    assert_eq!(context.chart.deleted_notes, 1);
    assert!(context.updated());
}

#[test]
fn router_invokes_redo_and_reports_result() {
    let mut context = FakeContext::new();
    context.undo.can_redo_result = margrete_rpc::abi::MP_TRUE;
    context.undo.redo_result = margrete_rpc::abi::MP_FALSE;
    let router = RequestRouter::new(context.as_ptr());
    let response = router.route(&Envelope {
        request_id: 25,
        body: Some(envelope::Body::RedoRequest(Default::default())),
    });
    let Some(envelope::Body::RedoResponse(redo)) = response.body else {
        panic!("expected redo");
    };
    assert!(!redo.success);
    assert_eq!(context.undo.redo_count, 1);
}

#[test]
fn router_skips_undo_when_undo_is_unavailable() {
    let mut context = FakeContext::new();
    context.undo.can_undo_result = margrete_rpc::abi::MP_FALSE;
    let router = RequestRouter::new(context.as_ptr());
    let response = router.route(&Envelope {
        request_id: 28,
        body: Some(envelope::Body::UndoRequest(Default::default())),
    });
    let Some(envelope::Body::UndoResponse(undo)) = response.body else {
        panic!("expected undo");
    };
    assert!(!undo.success);
    assert_eq!(context.undo.undo_count, 0);
}

#[test]
fn router_skips_redo_when_redo_is_unavailable() {
    let mut context = FakeContext::new();
    context.undo.can_redo_result = margrete_rpc::abi::MP_FALSE;
    let router = RequestRouter::new(context.as_ptr());
    let response = router.route(&Envelope {
        request_id: 29,
        body: Some(envelope::Body::RedoRequest(Default::default())),
    });
    let Some(envelope::Body::RedoResponse(redo)) = response.body else {
        panic!("expected redo");
    };
    assert!(!redo.success);
    assert_eq!(context.undo.redo_count, 0);
}

#[test]
fn router_returns_current_tick() {
    let mut context = FakeContext::new();
    context.set_current_tick(1234);
    let router = RequestRouter::new(context.as_ptr());
    let response = router.route(&Envelope {
        request_id: 26,
        body: Some(envelope::Body::CurrentTickRequest(Default::default())),
    });
    let Some(envelope::Body::CurrentTickResponse(tick)) = response.body else {
        panic!("expected tick");
    };
    assert_eq!(tick.current_tick, 1234);
}
