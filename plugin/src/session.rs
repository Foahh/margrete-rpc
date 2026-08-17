use crate::abi::{Chart, ComPtr, Context, UndoBuffer};
use crate::error::Result;

pub struct MargreteSession {
    context: *mut Context,
    _document: ComPtr<crate::abi::Document>,
    chart: ComPtr<Chart>,
    undo: ComPtr<UndoBuffer>,
}

impl MargreteSession {
    pub fn new(context: *mut Context) -> Result<Self> {
        let context_ref = unsafe { &*context };
        let document = context_ref.get_document()?;
        let chart = document.document().get_chart()?;
        let undo = document.document().get_undo_buffer()?;
        Ok(Self {
            context,
            _document: document,
            chart,
            undo,
        })
    }

    pub fn current_tick(&self) -> i32 {
        unsafe { (*self.context).current_tick() }
    }

    pub fn chart(&self) -> &Chart {
        self.chart.chart()
    }

    pub fn undo_buffer(&self) -> &UndoBuffer {
        self.undo.undo()
    }

    pub fn update(&self) {
        unsafe {
            (*self.context).update();
        }
    }
}
