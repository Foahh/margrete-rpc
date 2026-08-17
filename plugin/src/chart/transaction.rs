use crate::abi::{
    Chart, ComPtr, EventBcInfo, EventBeat, EventBpm, EventBpmInfo, EventNsm, EventNsmInfo,
    EventTls, EventTlsInfo, IID_EVENT_BEAT, IID_EVENT_BPM, IID_EVENT_NSM, IID_EVENT_TLS, Note,
};
use crate::chart::mapper::proto_to_note_info;
use crate::chart::session::MargreteSession;
use crate::error::{PluginError, Result};
use crate::rpc::proto::{ApplyEditRequest, Note as ProtoNote};
use std::collections::{HashMap, HashSet};

pub fn apply_edit(session: &MargreteSession, request: &ApplyEditRequest) -> Result<()> {
    validate_note_edit(session.chart(), request)?;
    with_undo(session, || {
        apply_edit_notes(session.chart(), request)?;
        apply_edit_events(session.chart(), request)
    })
}

fn with_undo<F>(session: &MargreteSession, f: F) -> Result<()>
where
    F: FnOnce() -> Result<()>,
{
    session.undo_buffer().begin_recording()?;
    match f() {
        Ok(()) => {
            session.undo_buffer().commit_recording()?;
            session.update();
            Ok(())
        }
        Err(err) => {
            session.undo_buffer().discard_recording();
            Err(err)
        }
    }
}

fn create_note_tree(chart: &Chart, proto: &ProtoNote) -> Result<ComPtr<Note>> {
    let owned = chart.create_note()?;
    owned.note().set_info(&proto_to_note_info(proto));
    for child_proto in &proto.children {
        let child = create_note_tree(chart, child_proto)?;
        let child_ptr = child.as_ptr();
        owned.note().append_child(child_ptr)?;
        let _ = child.into_raw();
    }
    Ok(owned)
}

fn upsert_note_tree(existing: &Note, proto: &ProtoNote) -> Result<()> {
    existing.set_info(&proto_to_note_info(proto));
    let child_count = existing.children_count();
    let mut children = Vec::with_capacity(child_count.max(0) as usize);
    let mut child_by_id = HashMap::new();
    for index in 0..child_count {
        let owned = existing.get_child(index)?;
        child_by_id.insert(owned.note().id(), owned.as_ptr());
        children.push(owned);
    }
    for child_proto in &proto.children {
        let Some(id) = child_proto.id else {
            return Err(PluginError::invalid(
                "in-place note upsert requires child ids",
            ));
        };
        let Some(found) = child_by_id.get(&id) else {
            return Err(PluginError::invalid(
                "note upsert references unknown child id",
            ));
        };
        upsert_note_tree(unsafe { &**found }, child_proto)?;
    }
    Ok(())
}

fn apply_bpm_event(chart: &Chart, proto: &crate::rpc::proto::BpmEvent) -> Result<()> {
    let info = EventBpmInfo {
        tick: proto.tick,
        bpm: proto.bpm,
    };
    if let Some(existing) = chart.find_event_bpm(proto.tick) {
        existing.get()?.set_info(&info);
        return Ok(());
    }
    let event = chart.create_event_as::<EventBpm>(&IID_EVENT_BPM)?;
    let created = event.get()?;
    created.set_info(&info);
    chart.append_event(created.as_event())?;
    let _ = event.into_raw();
    Ok(())
}

fn apply_beat_event(chart: &Chart, proto: &crate::rpc::proto::BeatChangeEvent) -> Result<()> {
    let info = EventBcInfo {
        bar: proto.bar,
        beats_per_bar: proto.beats_per_bar,
        beat_unit: proto.beat_unit,
    };
    if let Some(existing) = chart.find_event_beat_change(proto.bar) {
        existing.get()?.set_info(&info);
        return Ok(());
    }
    let event = chart.create_event_as::<EventBeat>(&IID_EVENT_BEAT)?;
    let created = event.get()?;
    created.set_info(&info);
    chart.append_event(created.as_event())?;
    let _ = event.into_raw();
    Ok(())
}

fn apply_tls_event(chart: &Chart, proto: &crate::rpc::proto::TimelineSpeedEvent) -> Result<()> {
    let info = EventTlsInfo {
        timeline_id: proto.timeline_id,
        tick: proto.tick,
        speed: proto.speed,
    };
    if let Some(existing) = chart.find_event_timeline_speed(proto.tick, proto.timeline_id) {
        existing.get()?.set_info(&info);
        return Ok(());
    }
    let event = chart.create_event_as::<EventTls>(&IID_EVENT_TLS)?;
    let created = event.get()?;
    created.set_info(&info);
    chart.append_event(created.as_event())?;
    let _ = event.into_raw();
    Ok(())
}

fn apply_nsm_event(chart: &Chart, proto: &crate::rpc::proto::NoteSpeedEvent) -> Result<()> {
    let info = EventNsmInfo {
        tick: proto.tick,
        speed: proto.speed,
    };
    if let Some(existing) = chart.find_event_note_speed(proto.tick) {
        existing.get()?.set_info(&info);
        return Ok(());
    }
    let event = chart.create_event_as::<EventNsm>(&IID_EVENT_NSM)?;
    let created = event.get()?;
    created.set_info(&info);
    chart.append_event(created.as_event())?;
    let _ = event.into_raw();
    Ok(())
}

fn current_root_notes(chart: &Chart) -> Result<Vec<ComPtr<Note>>> {
    let count = chart.notes_count();
    let mut notes = Vec::with_capacity(count.max(0) as usize);
    for index in 0..count {
        notes.push(chart.get_note(index)?);
    }
    Ok(notes)
}

fn delete_all_root_notes(chart: &Chart) -> Result<()> {
    let count = chart.notes_count();
    for index in (0..count).rev() {
        let owned = chart.get_note(index)?;
        chart.delete_note(owned.as_ptr())?;
    }
    Ok(())
}

fn validate_note_edit(chart: &Chart, request: &ApplyEditRequest) -> Result<()> {
    if request.replace_all_notes {
        for note_proto in &request.notes_upsert {
            reject_existing_ids(note_proto)?;
        }
        return Ok(());
    }

    let roots = current_root_notes(chart)?;
    let mut existing_by_id = HashMap::new();
    for note in &roots {
        existing_by_id.insert(note.note().id(), note.as_ptr());
    }
    let delete_ids: HashSet<i32> = request.note_ids_delete.iter().copied().collect();
    for proto in &request.notes_upsert {
        let Some(id) = proto.id else {
            continue;
        };
        if delete_ids.contains(&id) {
            return Err(PluginError::invalid(
                "note upsert references a note id that is also deleted",
            ));
        }
        let Some(found) = existing_by_id.get(&id) else {
            return Err(PluginError::invalid(
                "note upsert references unknown note id",
            ));
        };
        validate_upsert_tree(unsafe { &**found }, proto)?;
    }
    Ok(())
}

fn reject_existing_ids(note: &ProtoNote) -> Result<()> {
    if note.id.is_some() {
        return Err(PluginError::invalid(
            "replace_all_notes cannot contain existing note ids",
        ));
    }
    for child in &note.children {
        reject_existing_ids(child)?;
    }
    Ok(())
}

fn validate_upsert_tree(existing: &Note, proto: &ProtoNote) -> Result<()> {
    let child_count = existing.children_count();
    let mut children = Vec::with_capacity(child_count.max(0) as usize);
    let mut child_by_id = HashMap::new();
    for index in 0..child_count {
        let owned = existing.get_child(index)?;
        child_by_id.insert(owned.note().id(), owned.as_ptr());
        children.push(owned);
    }
    for child_proto in &proto.children {
        let Some(id) = child_proto.id else {
            return Err(PluginError::invalid(
                "in-place note upsert requires child ids",
            ));
        };
        let Some(found) = child_by_id.get(&id) else {
            return Err(PluginError::invalid(
                "note upsert references unknown child id",
            ));
        };
        validate_upsert_tree(unsafe { &**found }, child_proto)?;
    }
    Ok(())
}

fn apply_edit_notes(chart: &Chart, request: &ApplyEditRequest) -> Result<()> {
    if request.replace_all_notes {
        delete_all_root_notes(chart)?;
        for note_proto in &request.notes_upsert {
            let note = create_note_tree(chart, note_proto)?;
            match chart.append_note(note.as_ptr()) {
                Ok(()) => {
                    let _ = note.into_raw();
                }
                Err(err) => return Err(err),
            }
        }
        return Ok(());
    }

    if !request.note_ids_delete.is_empty() {
        let delete_ids: HashSet<i32> = request.note_ids_delete.iter().copied().collect();
        let roots = current_root_notes(chart)?;
        for note in &roots {
            if delete_ids.contains(&note.note().id()) {
                chart.delete_note(note.as_ptr())?;
            }
        }
    }

    if !request.notes_upsert.is_empty() {
        let roots = current_root_notes(chart)?;
        let mut existing_by_id = HashMap::new();
        for note in &roots {
            existing_by_id.insert(note.note().id(), note.as_ptr());
        }
        for proto in &request.notes_upsert {
            if let Some(id) = proto.id {
                let Some(found) = existing_by_id.get(&id) else {
                    return Err(PluginError::invalid(
                        "note upsert references unknown note id",
                    ));
                };
                upsert_note_tree(unsafe { &**found }, proto)?;
            } else {
                let note = create_note_tree(chart, proto)?;
                match chart.append_note(note.as_ptr()) {
                    Ok(()) => {
                        let _ = note.into_raw();
                    }
                    Err(err) => return Err(err),
                }
            }
        }
    }
    Ok(())
}

fn apply_edit_events(chart: &Chart, request: &ApplyEditRequest) -> Result<()> {
    for tick in &request.bpm_ticks_delete {
        if let Some(event) = chart.find_event_bpm(*tick) {
            chart.delete_event(event.get()?.as_event())?;
        }
    }
    for bar in &request.beat_bars_delete {
        if let Some(event) = chart.find_event_beat_change(*bar) {
            chart.delete_event(event.get()?.as_event())?;
        }
    }
    for key in &request.til_keys_delete {
        if let Some(event) = chart.find_event_timeline_speed(key.tick, key.timeline_id) {
            chart.delete_event(event.get()?.as_event())?;
        }
    }
    for tick in &request.note_speed_ticks_delete {
        if let Some(event) = chart.find_event_note_speed(*tick) {
            chart.delete_event(event.get()?.as_event())?;
        }
    }

    for event in &request.bpm_upsert {
        apply_bpm_event(chart, event)?;
    }
    for event in &request.beat_upsert {
        apply_beat_event(chart, event)?;
    }
    for event in &request.til_upsert {
        apply_tls_event(chart, event)?;
    }
    for event in &request.note_speed_upsert {
        apply_nsm_event(chart, event)?;
    }
    Ok(())
}
