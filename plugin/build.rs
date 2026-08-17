use chrono::{DateTime, Utc};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

const TITLE: &str = "Margrete RPC";
const DEVELOPER: &str = "Foahh";
const DLL_NAME: &str = "margrete_rpc";
const REPO_URL: &str = "https://github.com/Foahh/margrete-rpc";

fn main() {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR"));
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("OUT_DIR"));

    println!("cargo:rerun-if-changed=config/margrete_rpc.ini.in");
    println!("cargo:rerun-if-changed=../proto/margrete/rpc/messages.proto");
    println!("cargo:rerun-if-changed=../proto/API_VERSION");

    let version = env::var("CARGO_PKG_VERSION").expect("CARGO_PKG_VERSION");
    let major = env_u16("CARGO_PKG_VERSION_MAJOR");
    let minor = env_u16("CARGO_PKG_VERSION_MINOR");
    let patch = env_u16("CARGO_PKG_VERSION_PATCH");

    let proto_root = manifest_dir.join("../proto");
    prost_build::Config::new()
        .compile_protos(
            &[proto_root.join("margrete/rpc/messages.proto")],
            &[&proto_root],
        )
        .expect("compile protobuf");

    let api_version: u32 = fs::read_to_string(manifest_dir.join("../proto/API_VERSION"))
        .expect("proto/API_VERSION")
        .trim()
        .parse()
        .expect("proto/API_VERSION must be a u32");

    let build_time = build_time_utc();
    let desc_ini = format!("Local RPC/protobuf bridge for Margrete\\n{REPO_URL}");
    let dialog_title = format!("{TITLE} v{version} ({build_time})");

    let meta = format!(
        "pub const TITLE: &str = {TITLE:?};\n\
         pub const DESC: &str = \"Local RPC/protobuf bridge for Margrete\\n{REPO_URL}\";\n\
         pub const DEVELOPER: &str = {DEVELOPER:?};\n\
         pub const DLL_NAME: &str = {DLL_NAME:?};\n\
         pub const CONFIG_FILE_NAME: &str = \"{DLL_NAME}.ini\";\n\
         pub const PRODUCT_VERSION: &str = {version:?};\n\
         pub const RPC_API_VERSION: u32 = {api_version};\n\
         pub const BUILD_TIME: &str = {build_time:?};\n\
         pub const DIALOG_TITLE: &str = {dialog_title:?};\n"
    );
    fs::write(out_dir.join("meta.rs"), meta).expect("write meta.rs");

    let ini_in =
        fs::read_to_string(manifest_dir.join("config/margrete_rpc.ini.in")).expect("ini template");
    let ini = ini_in
        .replace("@TITLE@", TITLE)
        .replace("@DESC@", &desc_ini)
        .replace("@DEVELOPER@", DEVELOPER);
    let ini_name = format!("{DLL_NAME}.ini");
    let ini_path = out_dir.join(&ini_name);
    fs::write(&ini_path, ini).expect("write ini");
    if let Some(profile_dir) = out_dir.ancestors().nth(3) {
        let _ = fs::write(profile_dir.join(&ini_name), fs::read(&ini_path).unwrap());
    }

    embed_version_resource(
        &version,
        major,
        minor,
        patch,
        "Local RPC/protobuf bridge for Margrete",
    );
}

fn env_u16(key: &str) -> u16 {
    env::var(key)
        .unwrap_or_else(|_| panic!("{key}"))
        .parse()
        .unwrap_or_else(|_| panic!("{key} must be a u16"))
}

fn build_time_utc() -> String {
    if let Ok(value) = env::var("SOURCE_DATE_EPOCH")
        && let Ok(secs) = value.parse::<u64>()
    {
        return format_unix(secs);
    }
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format_unix(secs)
}

fn format_unix(secs: u64) -> String {
    DateTime::<Utc>::from_timestamp(secs as i64, 0)
        .unwrap_or(DateTime::<Utc>::UNIX_EPOCH)
        .format("%Y-%m-%dT%H:%M:%SZ")
        .to_string()
}

fn embed_version_resource(version: &str, major: u16, minor: u16, patch: u16, desc: &str) {
    if env::var("CARGO_CFG_TARGET_OS").unwrap_or_default() != "windows" {
        return;
    }
    let mut res = winres::WindowsResource::new();
    res.set("FileDescription", desc);
    res.set("ProductName", TITLE);
    res.set("ProductVersion", version);
    res.set("FileVersion", &format!("{major}.{minor}.{patch}.0"));
    res.set("CompanyName", DEVELOPER);
    res.set("LegalCopyright", &format!("Copyright (C) {DEVELOPER}"));
    res.set("InternalName", DLL_NAME);
    res.set("OriginalFilename", &format!("{DLL_NAME}.dll"));
    let packed = u64::from(major) << 48 | u64::from(minor) << 32 | u64::from(patch) << 16;
    res.set_version_info(winres::VersionInfo::FILEVERSION, packed);
    res.set_version_info(winres::VersionInfo::PRODUCTVERSION, packed);
    if let Err(err) = res.compile() {
        println!("cargo:warning=winres failed: {err}");
    }
    let _ = Path::new(".");
}
