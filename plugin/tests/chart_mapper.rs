mod common;

use common::fake::{FakeBeatEvent, FakeBpmEvent, FakeContext, FakeNsmEvent, FakeTlsEvent};
use margrete_rpc::abi::{
    MP_NOTEDIR_UPLEFT, MP_NOTEEXATTR_HAS_NOTE, MP_NOTELONGATTR_BEGIN, MP_NOTETYPE_SLIDE,
    MP_NOTETYPE_TAP,
};
use margrete_rpc::chart::mapper::{snapshot_for_edit, snapshot_notes};
use margrete_rpc::rpc::proto::{BeginEditResponse, Direction, ExAttr, LongAttr, NoteType};

#[test]
fn chart_mapper_serializes_root_notes_and_child_notes() {
    let mut context = FakeContext::new();
    {
        let root = context.chart.add_existing_note(10);
        root.info.r#type = MP_NOTETYPE_SLIDE;
        root.info.long_attr = MP_NOTELONGATTR_BEGIN;
        root.info.direction = MP_NOTEDIR_UPLEFT;
        root.info.ex_attr = MP_NOTEEXATTR_HAS_NOTE;
        root.info.variation_id = 2;
        root.info.x = 3;
        root.info.width = 2;
        root.info.height = 1;
        root.info.tick = 120;
        root.info.timeline_id = 4;
        root.info.option_value = 9;
    }
    let child_ptr = {
        let child = context.chart.add_detached_note(11);
        child.info.r#type = MP_NOTETYPE_TAP;
        child.info.tick = 180;
        child as *mut _
    };
    unsafe {
        (*context.chart.notes[0]).children.push(child_ptr);
    }

    let notes = snapshot_notes(unsafe { &*context.chart.as_ptr() }).unwrap();
    assert_eq!(notes.len(), 1);
    assert_eq!(notes[0].id, Some(10));
    assert_eq!(notes[0].r#type, NoteType::Slide as i32);
    assert_eq!(notes[0].long_attr, LongAttr::Begin as i32);
    assert_eq!(notes[0].direction, Direction::Upleft as i32);
    assert_eq!(notes[0].ex_attr, ExAttr::HasNote as i32);
    assert_eq!(notes[0].children.len(), 1);
    assert_eq!(notes[0].children[0].id, Some(11));
    assert_eq!(notes[0].children[0].tick, 180);
    unsafe {
        assert_eq!((*context.chart.notes[0]).ref_count_value(), 1);
        assert_eq!((*child_ptr).ref_count_value(), 1);
    }
}

#[test]
fn chart_mapper_scans_events_through_configured_tick_range() {
    let mut context = FakeContext::new();
    {
        let root = context.chart.add_existing_note(10);
        root.info.tick = 1000;
        root.info.timeline_id = 2;
    }
    let bpm = context.chart.add_existing_bpm(120, 180.0) as *mut FakeBpmEvent;
    let note_speed = context.chart.add_existing_nsm(240, 1.25) as *mut FakeNsmEvent;
    let timeline_speed = context.chart.add_existing_tls(360, 2, 0.75) as *mut FakeTlsEvent;
    let beat = context.chart.add_existing_beat(1, 3, 4) as *mut FakeBeatEvent;

    let mut response = BeginEditResponse::default();
    snapshot_for_edit(
        unsafe { &*context.chart.as_ptr() },
        200,
        &[2],
        false,
        &mut response,
    )
    .unwrap();

    assert!(response.snapshot);
    assert_eq!(response.event_scan_lookahead_ticks, 200);
    assert_eq!(response.event_scan_til_ids, vec![2]);
    assert_eq!(response.bpm_events.len(), 1);
    assert_eq!(response.bpm_events[0].tick, 120);
    assert_eq!(response.bpm_events[0].bpm, 180.0);
    assert_eq!(response.note_speed_events.len(), 1);
    assert_eq!(response.note_speed_events[0].tick, 240);
    assert_eq!(response.timeline_speed_events.len(), 1);
    assert_eq!(response.timeline_speed_events[0].timeline_id, 2);
    assert_eq!(response.beat_change_events.len(), 1);
    assert_eq!(response.beat_change_events[0].bar, 1);
    unsafe {
        assert_eq!((*context.chart.notes[0]).ref_count_value(), 1);
        assert_eq!((*bpm).ref_count_value(), 1);
        assert_eq!((*note_speed).ref_count_value(), 1);
        assert_eq!((*timeline_speed).ref_count_value(), 1);
        assert_eq!((*beat).ref_count_value(), 1);
    }
}

#[test]
fn chart_mapper_note_til_only_skips_timelines_without_notes() {
    let mut context = FakeContext::new();
    {
        let root = context.chart.add_existing_note(10);
        root.info.tick = 1000;
        root.info.timeline_id = 2;
    }
    let unused = context.chart.add_existing_tls(100, 0, 0.5) as *mut FakeTlsEvent;
    let used = context.chart.add_existing_tls(360, 2, 0.75) as *mut FakeTlsEvent;

    let mut with_flag = BeginEditResponse::default();
    snapshot_for_edit(
        unsafe { &*context.chart.as_ptr() },
        200,
        &[0, 2],
        true,
        &mut with_flag,
    )
    .unwrap();
    assert_eq!(with_flag.event_scan_til_ids, vec![2]);
    assert_eq!(with_flag.timeline_speed_events.len(), 1);
    assert_eq!(with_flag.timeline_speed_events[0].timeline_id, 2);
    assert_eq!(with_flag.timeline_speed_events[0].tick, 360);

    let mut without_flag = BeginEditResponse::default();
    snapshot_for_edit(
        unsafe { &*context.chart.as_ptr() },
        200,
        &[0, 2],
        false,
        &mut without_flag,
    )
    .unwrap();
    assert_eq!(without_flag.event_scan_til_ids.len(), 2);
    assert_eq!(without_flag.timeline_speed_events.len(), 2);
    unsafe {
        assert_eq!((*context.chart.notes[0]).ref_count_value(), 1);
        assert_eq!((*unused).ref_count_value(), 1);
        assert_eq!((*used).ref_count_value(), 1);
    }
}
