use crate::abi::{
    Command, CommandVTable, Context, IID_BASE, IID_COMMAND, MP_FALSE, MP_SDK_VERSION, MP_TRUE,
    MpBoolean, MpGuid, MpInteger, MpPluginInfo, copy_wide,
};
use crate::error::Result;
use crate::meta;
use crate::server::ServerController;
use crate::server::config::{ServerConfig, load_server_config};
use std::path::PathBuf;
use std::sync::atomic::{AtomicI32, Ordering};

#[repr(C)]
pub struct Plugin {
    vtable: *const CommandVTable,
    ref_count: AtomicI32,
    controller: ServerController,
}

static COMMAND_VT: CommandVTable = CommandVTable {
    add_ref: plugin_add_ref,
    release: plugin_release,
    query_interface: plugin_query_interface,
    get_command_name: plugin_get_command_name,
    invoke: plugin_invoke,
};

impl Plugin {
    fn new() -> Result<Box<Self>> {
        let source_path = resolve_config_path();
        let config = match load_server_config(&source_path) {
            Ok(config) => config,
            Err(_) => ServerConfig {
                source_path,
                ..ServerConfig::default()
            },
        };
        Ok(Box::new(Self {
            vtable: &COMMAND_VT,
            ref_count: AtomicI32::new(0),
            controller: ServerController::new(config, dll_directory())?,
        }))
    }

    fn from_ptr<'a>(ptr: *mut Command) -> &'a mut Self {
        unsafe { &mut *(ptr as *mut Self) }
    }
}

pub unsafe fn margrete_plugin_get_info(info: *mut MpPluginInfo) {
    unsafe {
        if info.is_null() {
            return;
        }
        (*info).sdk_version = MP_SDK_VERSION;
        copy_wide((*info).name_buffer, (*info).name_buffer_length, meta::TITLE);
        copy_wide((*info).desc_buffer, (*info).desc_buffer_length, meta::DESC);
        copy_wide(
            (*info).developer_buffer,
            (*info).developer_buffer_length,
            meta::DEVELOPER,
        );
    }
}

pub unsafe fn margrete_plugin_command_create(ppobj: *mut *mut Command) -> MpBoolean {
    unsafe {
        if ppobj.is_null() {
            return MP_FALSE;
        }
        let plugin = match Plugin::new() {
            Ok(plugin) => plugin,
            Err(err) => {
                log::error!("failed to create plugin: {err}");
                return MP_FALSE;
            }
        };
        let ptr = Box::into_raw(plugin) as *mut Command;
        plugin_add_ref(ptr);
        *ppobj = ptr;
        MP_TRUE
    }
}

unsafe extern "C" fn plugin_add_ref(this: *mut Command) -> MpInteger {
    Plugin::from_ptr(this)
        .ref_count
        .fetch_add(1, Ordering::SeqCst)
        + 1
}

unsafe extern "C" fn plugin_release(this: *mut Command) -> MpInteger {
    unsafe {
        let value = Plugin::from_ptr(this)
            .ref_count
            .fetch_sub(1, Ordering::SeqCst)
            - 1;
        if value == 0 {
            Plugin::from_ptr(this).controller.stop();
            drop(Box::from_raw(this as *mut Plugin));
        }
        value
    }
}

unsafe extern "C" fn plugin_query_interface(
    this: *mut Command,
    iid: *const MpGuid,
    ppobj: *mut *mut std::ffi::c_void,
) -> MpBoolean {
    unsafe {
        if ppobj.is_null() || iid.is_null() {
            return MP_FALSE;
        }
        let iid = &*iid;
        if iid.eq_guid(&IID_BASE) || iid.eq_guid(&IID_COMMAND) {
            *ppobj = this as *mut std::ffi::c_void;
            plugin_add_ref(this);
            MP_TRUE
        } else {
            *ppobj = std::ptr::null_mut();
            MP_FALSE
        }
    }
}

unsafe extern "C" fn plugin_get_command_name(
    _this: *mut Command,
    text: *mut u16,
    text_length: MpInteger,
) -> MpBoolean {
    if text.is_null() || text_length <= 0 {
        return MP_FALSE;
    }
    copy_wide(text, text_length, meta::TITLE);
    MP_TRUE
}

unsafe extern "C" fn plugin_invoke(this: *mut Command, ctx: *mut Context) -> MpBoolean {
    if ctx.is_null() {
        return MP_FALSE;
    }
    let plugin = Plugin::from_ptr(this);
    let config_error = try_reload_config(&plugin.controller);
    if !plugin.controller.running() && config_error.is_empty() {
        plugin.controller.start(ctx);
    }
    crate::ui::dialog::show_server_status_dialog(ctx, &plugin.controller, config_error);
    MP_TRUE
}

fn try_reload_config(controller: &ServerController) -> String {
    match load_server_config(resolve_config_path()) {
        Ok(config) => {
            controller.set_config(config);
            String::new()
        }
        Err(err) => err.to_string(),
    }
}

fn resolve_config_path() -> PathBuf {
    if let Some(env_path) = environment_path("MARGRETE_RPC_CONFIG")
        && env_path.exists()
    {
        return env_path;
    }
    if let Some(dll_dir) = dll_directory() {
        let near_dll = dll_dir.join(meta::CONFIG_FILE_NAME);
        if near_dll.exists() {
            return near_dll;
        }
    }
    let plugins = PathBuf::from("./plugins").join(meta::CONFIG_FILE_NAME);
    if plugins.exists() {
        return plugins;
    }
    PathBuf::from(meta::CONFIG_FILE_NAME)
}

fn environment_path(name: &str) -> Option<PathBuf> {
    std::env::var_os(name).map(PathBuf::from)
}

fn dll_directory() -> Option<PathBuf> {
    use windows::Win32::Foundation::HMODULE;
    use windows::Win32::System::LibraryLoader::{
        GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        GetModuleFileNameW, GetModuleHandleExW,
    };
    use windows::core::PCWSTR;
    unsafe {
        let mut module = HMODULE::default();
        let addr = dll_directory as *const ();
        if GetModuleHandleExW(
            GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
            PCWSTR(addr as *const u16),
            &mut module,
        )
        .is_err()
            || module.is_invalid()
        {
            return None;
        }
        let mut buf = vec![0u16; 260];
        loop {
            let n = GetModuleFileNameW(Some(module), &mut buf);
            if n == 0 {
                return None;
            }
            if (n as usize) < buf.len() {
                buf.truncate(n as usize);
                let path = String::from_utf16_lossy(&buf);
                return Some(PathBuf::from(path).parent()?.to_path_buf());
            }
            buf.resize(buf.len() * 2, 0);
        }
    }
}
