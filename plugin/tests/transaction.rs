mod common;

use common::fake::{APPEND_CHILD_RESULT, FakeBpmEvent, FakeContext, FakeNote};
use margrete_rpc::abi::{Event, MP_FALSE, MP_NOTETYPE_HOLD, MP_NOTETYPE_TAP, MP_TRUE};
use margrete_rpc::chart::session::MargreteSession;
use margrete_rpc::chart::transaction::apply_edit;
use margrete_rpc::rpc::proto::{ApplyEditRequest, Note, NoteType};
use std::sync::atomic::Ordering;

#[test]
fn margrete_session_releases_acquired_interfaces() {
    let context = FakeContext::new();
    assert_eq!(context.document().ref_count_value(), 1);
    assert_eq!(context.chart.ref_count_value(), 1);
    assert_eq!(context.undo.ref_count_value(), 1);
    {
        let _session = MargreteSession::new(context.as_ptr()).unwrap();
        assert_eq!(context.document().ref_count_value(), 2);
        assert_eq!(context.chart.ref_count_value(), 2);
        assert_eq!(context.undo.ref_count_value(), 2);
    }
    assert_eq!(context.document().ref_count_value(), 1);
    assert_eq!(context.chart.ref_count_value(), 1);
    assert_eq!(context.undo.ref_count_value(), 1);
}

#[test]
fn apply_edit_appends_notes_and_child_trees_inside_undo_recording() {
    let context = FakeContext::new();
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.notes_upsert.push(Note {
        r#type: NoteType::Tap as i32,
        tick: 960,
        x: 4,
        width: 1,
        children: vec![Note {
            r#type: NoteType::Air as i32,
            tick: 970,
            ..Default::default()
        }],
        ..Default::default()
    });
    apply_edit(&session, &request).unwrap();
    assert_eq!(context.undo.begin_count, 1);
    assert_eq!(context.undo.commit_count, 1);
    assert_eq!(context.undo.discard_count, 0);
    assert_eq!(context.chart.appended_notes, 1);
    assert_eq!(context.chart.created_notes.len(), 2);
    assert!(context.updated());
}

#[test]
fn apply_edit_releases_created_note_when_root_append_fails() {
    let mut context = FakeContext::new();
    context.chart.append_note_result = MP_FALSE;
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.notes_upsert.push(Note {
        r#type: NoteType::Tap as i32,
        ..Default::default()
    });
    assert!(apply_edit(&session, &request).is_err());
    assert_eq!(context.undo.commit_count, 0);
    assert_eq!(context.undo.discard_count, 1);
    assert_eq!(context.chart.created_notes.len(), 1);
    unsafe {
        assert_eq!((*context.chart.created_notes[0]).ref_count_value(), 0);
    }
}

#[test]
fn apply_edit_releases_created_note_tree_when_child_append_fails() {
    APPEND_CHILD_RESULT.store(MP_FALSE, Ordering::SeqCst);
    let context = FakeContext::new();
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.notes_upsert.push(Note {
        r#type: NoteType::Hold as i32,
        children: vec![Note {
            r#type: NoteType::Hold as i32,
            ..Default::default()
        }],
        ..Default::default()
    });
    let result = apply_edit(&session, &request);
    APPEND_CHILD_RESULT.store(MP_TRUE, Ordering::SeqCst);
    assert!(result.is_err());
    assert_eq!(context.undo.commit_count, 0);
    assert_eq!(context.undo.discard_count, 1);
    assert_eq!(context.chart.created_notes.len(), 2);
    unsafe {
        assert_eq!((*context.chart.created_notes[0]).ref_count_value(), 0);
        assert_eq!((*context.chart.created_notes[1]).ref_count_value(), 0);
    }
}

#[test]
fn event_operation_creates_bpm_event_when_key_is_empty() {
    let context = FakeContext::new();
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.bpm_upsert.push(margrete_rpc::rpc::proto::BpmEvent {
        tick: 0,
        bpm: 180.0,
    });
    apply_edit(&session, &request).unwrap();
    assert_eq!(context.chart.created_bpm.len(), 1);
    unsafe {
        assert_eq!((*context.chart.created_bpm[0]).info.tick, 0);
        assert_eq!((*context.chart.created_bpm[0]).info.bpm, 180.0);
    }
    assert_eq!(context.chart.appended_events, 1);
}

#[test]
fn event_operation_releases_created_event_when_append_fails() {
    let mut context = FakeContext::new();
    context.chart.append_event_result = MP_FALSE;
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.bpm_upsert.push(margrete_rpc::rpc::proto::BpmEvent {
        tick: 0,
        bpm: 180.0,
    });
    assert!(apply_edit(&session, &request).is_err());
    assert_eq!(context.undo.commit_count, 0);
    assert_eq!(context.undo.discard_count, 1);
    assert_eq!(context.chart.created_bpm.len(), 1);
    unsafe {
        assert_eq!((*context.chart.created_bpm[0]).ref_count_value(), 0);
    }
}

#[test]
fn event_operation_replaces_bpm_event_when_key_overlaps() {
    let mut context = FakeContext::new();
    let existing = context.chart.add_existing_bpm(0, 120.0) as *mut FakeBpmEvent;
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.bpm_upsert.push(margrete_rpc::rpc::proto::BpmEvent {
        tick: 0,
        bpm: 185.0,
    });
    apply_edit(&session, &request).unwrap();
    unsafe {
        assert_eq!((*existing).info.bpm, 185.0);
        assert_eq!((*existing).ref_count_value(), 1);
    }
    assert_eq!(context.chart.appended_events, 0);
}

#[test]
fn event_operation_creates_timeline_speed_by_tick_and_timeline_id() {
    let context = FakeContext::new();
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request
        .til_upsert
        .push(margrete_rpc::rpc::proto::TimelineSpeedEvent {
            tick: 960,
            timeline_id: 2,
            speed: 0.75,
        });
    apply_edit(&session, &request).unwrap();
    assert_eq!(context.chart.created_tls.len(), 1);
    unsafe {
        assert_eq!((*context.chart.created_tls[0]).info.tick, 960);
        assert_eq!((*context.chart.created_tls[0]).info.timeline_id, 2);
        assert_eq!((*context.chart.created_tls[0]).info.speed, 0.75);
    }
}

#[test]
fn event_operation_creates_beat_change_and_note_speed_events() {
    let context = FakeContext::new();
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request
        .beat_upsert
        .push(margrete_rpc::rpc::proto::BeatChangeEvent {
            bar: 4,
            beats_per_bar: 3,
            beat_unit: 8,
        });
    request
        .note_speed_upsert
        .push(margrete_rpc::rpc::proto::NoteSpeedEvent {
            tick: 1200,
            speed: 1.25,
        });
    apply_edit(&session, &request).unwrap();
    unsafe {
        assert_eq!(context.chart.created_beat.len(), 1);
        assert_eq!((*context.chart.created_beat[0]).info.bar, 4);
        assert_eq!((*context.chart.created_beat[0]).info.beats_per_bar, 3);
        assert_eq!((*context.chart.created_beat[0]).info.beat_unit, 8);
        assert_eq!(context.chart.created_nsm.len(), 1);
        assert_eq!((*context.chart.created_nsm[0]).info.tick, 1200);
        assert_eq!((*context.chart.created_nsm[0]).info.speed, 1.25);
    }
}

#[test]
fn apply_edit_in_place_update_does_not_duplicate_root_notes() {
    let mut context = FakeContext::new();
    {
        let existing = context.chart.add_existing_note(10);
        existing.info.r#type = MP_NOTETYPE_TAP;
        existing.info.x = 1;
    }
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.notes_upsert.push(Note {
        id: Some(10),
        r#type: NoteType::Tap as i32,
        x: 9,
        ..Default::default()
    });
    apply_edit(&session, &request).unwrap();
    assert_eq!(context.chart.notes.len(), 1);
    unsafe {
        assert_eq!((*context.chart.notes[0]).info.x, 9);
        assert_eq!((*context.chart.notes[0]).ref_count_value(), 1);
    }
    assert_eq!(context.chart.appended_notes, 0);
}

#[test]
fn apply_edit_updates_child_notes_in_place_without_rebuilding_the_tree() {
    let mut context = FakeContext::new();
    {
        let root = context.chart.add_existing_note(10);
        root.info.r#type = MP_NOTETYPE_HOLD;
        root.info.tick = 0;
    }
    let child_ptr = {
        let child = context.chart.add_detached_note(11);
        child.info.r#type = MP_NOTETYPE_HOLD;
        child.info.tick = 480;
        child as *mut _
    };
    unsafe {
        (*context.chart.notes[0]).children.push(child_ptr);
    }
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.notes_upsert.push(Note {
        id: Some(10),
        r#type: NoteType::Hold as i32,
        tick: 1920,
        children: vec![Note {
            id: Some(11),
            r#type: NoteType::Hold as i32,
            tick: 2400,
            ..Default::default()
        }],
        ..Default::default()
    });
    apply_edit(&session, &request).unwrap();
    assert_eq!(context.chart.notes.len(), 1);
    assert_eq!(context.chart.appended_notes, 0);
    assert_eq!(context.chart.deleted_notes, 0);
    assert!(context.chart.created_notes.is_empty());
    unsafe {
        assert_eq!((*context.chart.notes[0]).info.tick, 1920);
        assert_eq!((*child_ptr).info.tick, 2400);
        assert_eq!((*context.chart.notes[0]).ref_count_value(), 1);
        assert_eq!((*child_ptr).ref_count_value(), 1);
    }
}

#[test]
fn apply_edit_rejects_unknown_child_id_before_recording() {
    let mut context = FakeContext::new();
    context.chart.add_existing_note(10);
    let child_ptr = context.chart.add_detached_note(11) as *mut _;
    unsafe {
        (*context.chart.notes[0]).children.push(child_ptr);
    }
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.notes_upsert.push(Note {
        id: Some(10),
        children: vec![Note {
            id: Some(99),
            ..Default::default()
        }],
        ..Default::default()
    });
    assert!(apply_edit(&session, &request).is_err());
    assert_eq!(context.undo.begin_count, 0);
    assert_eq!(context.undo.commit_count, 0);
    assert_eq!(context.undo.discard_count, 0);
}

#[test]
fn apply_edit_updates_existing_note_and_creates_new_note() {
    let mut context = FakeContext::new();
    context.chart.add_existing_note(10).info.x = 1;
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.notes_upsert.push(Note {
        id: Some(10),
        r#type: NoteType::Tap as i32,
        x: 9,
        ..Default::default()
    });
    request.notes_upsert.push(Note {
        r#type: NoteType::Air as i32,
        tick: 1200,
        ..Default::default()
    });
    apply_edit(&session, &request).unwrap();
    assert_eq!(context.chart.notes.len(), 2);
    unsafe {
        assert_eq!((*context.chart.notes[0]).id, 10);
        assert_eq!((*context.chart.notes[0]).info.x, 9);
    }
    assert_eq!(context.chart.created_notes.len(), 1);
    assert_eq!(context.chart.appended_notes, 1);
}

#[test]
fn apply_edit_rejects_replace_all_notes_with_note_ids() {
    let context = FakeContext::new();
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest {
        replace_all_notes: true,
        ..Default::default()
    };
    request.notes_upsert.push(Note {
        id: Some(1),
        r#type: NoteType::Tap as i32,
        ..Default::default()
    });
    assert!(apply_edit(&session, &request).is_err());
    assert_eq!(context.undo.begin_count, 0);
    assert_eq!(context.undo.commit_count, 0);
    assert_eq!(context.undo.discard_count, 0);
}

#[test]
fn apply_edit_rejects_replace_all_notes_without_wiping_existing_notes() {
    let mut context = FakeContext::new();
    context.chart.add_existing_note(10);
    context.chart.add_existing_note(11);
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest {
        replace_all_notes: true,
        ..Default::default()
    };
    request.notes_upsert.push(Note {
        id: Some(1),
        r#type: NoteType::Tap as i32,
        ..Default::default()
    });
    assert!(apply_edit(&session, &request).is_err());
    assert_eq!(context.chart.notes.len(), 2);
    assert_eq!(context.chart.deleted_notes, 0);
    assert_eq!(context.undo.begin_count, 0);
    assert_eq!(context.undo.discard_count, 0);
}

#[test]
fn apply_edit_rejects_upsert_of_unknown_note_id() {
    let context = FakeContext::new();
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.notes_upsert.push(Note {
        id: Some(99),
        r#type: NoteType::Tap as i32,
        ..Default::default()
    });
    assert!(apply_edit(&session, &request).is_err());
    assert_eq!(context.undo.begin_count, 0);
    assert_eq!(context.undo.discard_count, 0);
}

#[test]
fn apply_edit_does_not_delete_notes_before_unknown_upsert_fails() {
    let mut context = FakeContext::new();
    context.chart.add_existing_note(10);
    context.chart.add_existing_note(11);
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.note_ids_delete.push(10);
    request.notes_upsert.push(Note {
        id: Some(99),
        r#type: NoteType::Tap as i32,
        ..Default::default()
    });
    assert!(apply_edit(&session, &request).is_err());
    assert_eq!(context.chart.notes.len(), 2);
    assert_eq!(context.chart.deleted_notes, 0);
    assert_eq!(context.undo.begin_count, 0);
    assert_eq!(context.undo.discard_count, 0);
}

#[test]
fn apply_edit_rejects_in_place_child_upsert_without_child_id() {
    let mut context = FakeContext::new();
    context.chart.add_existing_note(1);
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.notes_upsert.push(Note {
        id: Some(1),
        r#type: NoteType::Hold as i32,
        children: vec![Note {
            r#type: NoteType::Hold as i32,
            ..Default::default()
        }],
        ..Default::default()
    });
    assert!(apply_edit(&session, &request).is_err());
    assert_eq!(context.undo.begin_count, 0);
    assert_eq!(context.undo.discard_count, 0);
}

#[test]
fn apply_edit_deletes_existing_note_by_id() {
    let mut context = FakeContext::new();
    let deleted = context.chart.add_existing_note(10) as *mut FakeNote;
    context.chart.add_existing_note(11);
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.note_ids_delete.push(10);
    apply_edit(&session, &request).unwrap();
    assert_eq!(context.chart.notes.len(), 1);
    unsafe {
        assert_eq!((*context.chart.notes[0]).id, 11);
        assert_eq!((*deleted).ref_count_value(), 0);
    }
    assert_eq!(context.chart.deleted_notes, 1);
}

#[test]
fn apply_edit_deletes_bpm_event_by_tick() {
    let mut context = FakeContext::new();
    let deleted = context.chart.add_existing_bpm(120, 150.0) as *mut FakeBpmEvent;
    context.chart.add_existing_bpm(240, 160.0);
    let session = MargreteSession::new(context.as_ptr()).unwrap();
    let mut request = ApplyEditRequest::default();
    request.bpm_ticks_delete.push(120);
    apply_edit(&session, &request).unwrap();
    assert_eq!(context.chart.deleted_events, 1);
    assert_eq!(context.chart.deleted_event_pointers.len(), 1);
    assert_eq!(
        context.chart.deleted_event_pointers[0],
        deleted as *mut Event
    );
    unsafe {
        assert_eq!((*deleted).ref_count_value(), 0);
    }
}
