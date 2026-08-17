#![allow(clippy::missing_safety_doc)]
#![allow(clippy::not_unsafe_ptr_arg_deref)]
#![allow(clippy::too_many_arguments)]

pub mod abi;
pub mod chart;
pub mod error;
pub mod plugin;
pub mod rpc;
pub mod server;
pub mod ui;

pub mod meta {
    include!(concat!(env!("OUT_DIR"), "/meta.rs"));
}

pub use plugin::{margrete_plugin_command_create, margrete_plugin_get_info};

#[unsafe(no_mangle)]
pub unsafe extern "system" fn MargretePluginGetInfo(info: *mut abi::MpPluginInfo) {
    unsafe {
        margrete_plugin_get_info(info);
    }
}

#[unsafe(no_mangle)]
pub unsafe extern "system" fn MargretePluginCommandCreate(
    ppobj: *mut *mut abi::Command,
) -> abi::MpBoolean {
    unsafe { margrete_plugin_command_create(ppobj) }
}
