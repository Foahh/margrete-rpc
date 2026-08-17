use crate::abi::Chart;
use crate::error::Result;
use std::collections::HashSet;

pub fn deduplicate(chart: &Chart) -> Result<i32> {
    let count = chart.notes_count();
    let mut roots = Vec::with_capacity(count.max(0) as usize);
    for index in 0..count {
        roots.push(chart.get_note(index)?);
    }

    let mut seen = HashSet::new();
    let mut removed = 0;
    for note in &roots {
        let id = note.note().id();
        if !seen.insert(id) {
            chart.delete_note(note.as_ptr())?;
            removed += 1;
        }
    }
    Ok(removed)
}
