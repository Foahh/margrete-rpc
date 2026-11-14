mod common;

use common::fake::FakeContext;
use margrete_rpc::abi::{Note, Unknown};
use margrete_rpc::chart::deduper::deduplicate;

#[test]
fn root_note_deduper_removes_later_duplicate_ids() {
    let mut context = FakeContext::new();
    let first = context.chart.add_existing_note(10) as *mut _;
    let second = context.chart.add_existing_note(11) as *mut _;
    context.chart.add_existing_note(10);
    context.chart.add_existing_note(11);
    let removed = deduplicate(unsafe { &*context.chart.as_ptr() }).unwrap();
    assert_eq!(removed, 2);
    assert_eq!(context.chart.deleted_notes, 2);
    assert_eq!(context.chart.notes.len(), 2);
    assert_eq!(context.chart.notes[0], first);
    assert_eq!(context.chart.notes[1], second);
}

#[test]
fn root_note_deduper_leaves_unique_ids_unchanged() {
    let mut context = FakeContext::new();
    let first = context.chart.add_existing_note(10) as *mut _;
    let second = context.chart.add_existing_note(11) as *mut _;
    let removed = deduplicate(unsafe { &*context.chart.as_ptr() }).unwrap();
    assert_eq!(removed, 0);
    assert_eq!(context.chart.deleted_notes, 0);
    assert_eq!(context.chart.notes.len(), 2);
    assert_eq!(context.chart.notes[0], first);
    assert_eq!(context.chart.notes[1], second);
}

#[test]
fn repeated_undo_aliases_leave_one_reference_per_id() {
    let mut context = FakeContext::new();
    let original = context.chart.add_existing_note(10) as *mut common::fake::FakeNote;
    for _ in 0..3 {
        unsafe {
            Note::add_ref(original.cast());
        }
        context.chart.notes.push(original);
    }
    let removed = deduplicate(unsafe { &*context.chart.as_ptr() }).unwrap();
    assert_eq!(removed, 3);
    assert_eq!(context.chart.notes, vec![original]);
    assert_eq!(unsafe { (*original).ref_count_value() }, 1);
}
