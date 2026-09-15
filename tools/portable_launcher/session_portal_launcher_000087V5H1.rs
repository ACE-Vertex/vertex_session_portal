#![windows_subsystem = "windows"]

use std::env;
use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

fn canonical_if_dir(path: &Path) -> Option<PathBuf> {
    if !path.is_dir() {
        return None;
    }
    fs::canonicalize(path).ok().or_else(|| Some(path.to_path_buf()))
}

fn looks_like_portal_root(path: &Path) -> bool {
    path.join("package.json").is_file()
        && path.join("src").join("main").is_dir()
        && path.join("src").join("renderer").is_dir()
}

fn resolve_workspace_root(exe_dir: &Path) -> PathBuf {
    if let Ok(value) = env::var("VERTEX_SESSION_PORTAL_WORKSPACE_ROOT") {
        let candidate = PathBuf::from(value);
        if let Some(root) = canonical_if_dir(&candidate) {
            return root;
        }
    }

    for ancestor in exe_dir.ancestors() {
        if looks_like_portal_root(ancestor) {
            if let Some(root) = canonical_if_dir(ancestor) {
                return root;
            }
        }
    }

    let hint = exe_dir.join("workspace-root.txt");
    if let Ok(text) = fs::read_to_string(&hint) {
        let candidate = PathBuf::from(text.trim());
        if let Some(root) = canonical_if_dir(&candidate) {
            return root;
        }
    }

    exe_dir.to_path_buf()
}

fn write_error(exe_dir: &Path, message: &str) {
    let _ = fs::write(
        exe_dir.join("Vertex Session Portal.launch-error.txt"),
        message.as_bytes(),
    );
}

fn main() {
    let exe = match env::current_exe() {
        Ok(v) => v,
        Err(_) => return,
    };
    let exe_dir = match exe.parent() {
        Some(v) => v.to_path_buf(),
        None => return,
    };

    let runtime = exe_dir.join("Vertex Session Portal.runtime.exe");
    if !runtime.is_file() {
        write_error(&exe_dir, &format!("RUNTIME_MISSING:{}", runtime.display()));
        return;
    }

    let workspace_root = resolve_workspace_root(&exe_dir);
    let args: Vec<OsString> = env::args_os().skip(1).collect();

    let mut cmd = Command::new(&runtime);
    cmd.args(args)
        .current_dir(&workspace_root)
        .env("VERTEX_SESSION_PORTAL_WORKSPACE_ROOT", &workspace_root)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    #[cfg(windows)]
    cmd.creation_flags(CREATE_NO_WINDOW);

    if let Err(err) = cmd.spawn() {
        write_error(
            &exe_dir,
            &format!("SPAWN_FAILED:{}:{}", runtime.display(), err),
        );
    }
}
