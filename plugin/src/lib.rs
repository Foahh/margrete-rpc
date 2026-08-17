#![allow(clippy::missing_safety_doc)]
#![allow(clippy::not_unsafe_ptr_arg_deref)]
#![allow(clippy::too_many_arguments)]

pub mod abi;
pub mod chart_mapper;
pub mod config;
pub mod deduper;
pub mod discovery;
pub mod error;
pub mod fake;
pub mod framing;
pub mod logger;
pub mod plugin;
pub mod proto;
pub mod router;
pub mod server;
pub mod session;
pub mod transaction;

#[cfg(windows)]
pub mod dialog;

pub mod meta {
    include!(concat!(env!("OUT_DIR"), "/meta.rs"));
}

pub use plugin::{margrete_plugin_command_create, margrete_plugin_get_info};

#[no_mangle]
pub unsafe extern "system" fn MargretePluginGetInfo(info: *mut abi::MpPluginInfo) {
    margrete_plugin_get_info(info);
}

#[no_mangle]
pub unsafe extern "system" fn MargretePluginCommandCreate(
    ppobj: *mut *mut abi::Command,
) -> abi::MpBoolean {
    margrete_plugin_command_create(ppobj)
}
