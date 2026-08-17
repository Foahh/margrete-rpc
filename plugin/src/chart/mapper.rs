use crate::abi::{Chart, Note, NoteInfo};
use crate::error::Result;
use crate::rpc::proto::{
    BeatChangeEvent, BeginEditResponse, BpmEvent, Note as ProtoNote, NoteSpeedEvent,
    TimelineSpeedEvent,
};

pub fn snapshot_notes(chart: &Chart) -> Result<Vec<ProtoNote>> {
    let count = chart.notes_count();
    let mut notes = Vec::with_capacity(count.max(0) as usize);
    for index in 0..count {
        let owned = chart.get_note(index)?;
        notes.push(note_to_proto(owned.note())?);
    }
    Ok(notes)
}

pub fn snapshot_for_edit(
    chart: &Chart,
    event_scan_lookahead_ticks: i32,
    event_scan_til_ids: &[i32],
    note_til_only: bool,
    response: &mut BeginEditResponse,
) -> Result<()> {
    response.snapshot = true;
    let notes = snapshot_notes(chart)?;
    let mut last_note_tick = 0;
    for note in &notes {
        last_note_tick = last_note_tick.max(last_note_tick_of(note));
        response.notes.push(note.clone());
    }

    let scan_til_ids = if note_til_only {
        filter_event_scan_til_by_notes(&notes, event_scan_til_ids)
    } else {
        event_scan_til_ids.to_vec()
    };

    let scan_until = last_note_tick + event_scan_lookahead_ticks;
    response.event_scan_lookahead_ticks = event_scan_lookahead_ticks;
    response.event_scan_til_ids = scan_til_ids.clone();

    for tick in 0..=scan_until {
        if let Some(event) = chart.find_event_bpm(tick) {
            let info = event.get()?.info();
            response.bpm_events.push(BpmEvent {
                tick: info.tick,
                bpm: info.bpm,
            });
        }
        if let Some(event) = chart.find_event_note_speed(tick) {
            let info = event.get()?.info();
            response.note_speed_events.push(NoteSpeedEvent {
                tick: info.tick,
                speed: info.speed,
            });
        }
        if let Some(event) = chart.find_event_beat_change(tick) {
            let info = event.get()?.info();
            response.beat_change_events.push(BeatChangeEvent {
                bar: info.bar,
                beats_per_bar: info.beats_per_bar,
                beat_unit: info.beat_unit,
            });
        }
        for timeline_id in &scan_til_ids {
            if let Some(event) = chart.find_event_timeline_speed(tick, *timeline_id) {
                let info = event.get()?.info();
                response.timeline_speed_events.push(TimelineSpeedEvent {
                    tick: info.tick,
                    timeline_id: info.timeline_id,
                    speed: info.speed,
                });
            }
        }
    }
    Ok(())
}

pub fn note_to_proto(note: &Note) -> Result<ProtoNote> {
    let info = note.info();
    let mut proto = ProtoNote {
        id: Some(note.id()),
        r#type: info.r#type,
        long_attr: info.long_attr,
        direction: info.direction,
        ex_attr: info.ex_attr,
        variation_id: info.variation_id,
        x: info.x,
        width: info.width,
        height: info.height,
        tick: info.tick,
        timeline_id: info.timeline_id,
        option_value: info.option_value,
        children: Vec::new(),
    };
    let child_count = note.children_count();
    for index in 0..child_count {
        let child = note.get_child(index)?;
        proto.children.push(note_to_proto(child.note())?);
    }
    Ok(proto)
}

pub fn proto_to_note_info(note: &ProtoNote) -> NoteInfo {
    NoteInfo {
        r#type: note.r#type,
        long_attr: note.long_attr,
        direction: note.direction,
        ex_attr: note.ex_attr,
        variation_id: note.variation_id,
        x: note.x,
        width: note.width,
        height: note.height,
        tick: note.tick,
        timeline_id: note.timeline_id,
        option_value: note.option_value,
    }
}

fn last_note_tick_of(note: &ProtoNote) -> i32 {
    let mut tick = note.tick;
    for child in &note.children {
        tick = tick.max(last_note_tick_of(child));
    }
    tick
}

fn collect_timeline_ids(note: &ProtoNote, out: &mut std::collections::HashSet<i32>) {
    out.insert(note.timeline_id);
    for child in &note.children {
        collect_timeline_ids(child, out);
    }
}

fn filter_event_scan_til_by_notes(notes: &[ProtoNote], event_scan_til_ids: &[i32]) -> Vec<i32> {
    let mut used = std::collections::HashSet::new();
    for note in notes {
        collect_timeline_ids(note, &mut used);
    }
    event_scan_til_ids
        .iter()
        .copied()
        .filter(|til| used.contains(til))
        .collect()
}
