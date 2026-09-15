#![windows_subsystem = "windows"]

use std::env;
use std::ffi::OsString;
use std::fs;
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread::sleep;
use std::time::{Duration, Instant};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;
#[cfg(windows)]
const CREATE_NEW_PROCESS_GROUP: u32 = 0x00000200;

const WORKSTATION_ADDR: &str = "127.0.0.1:47832";

fn write_error(exe_dir: &Path, message: &str) {
    let _ = fs::write(
        exe_dir.join("Vertex Session Portal.launch-error.txt"),
        message.as_bytes(),
    );
}

fn port_open() -> bool {
    let Ok(addr) = WORKSTATION_ADDR.parse::<SocketAddr>() else {
        return false;
    };
    TcpStream::connect_timeout(&addr, Duration::from_millis(180)).is_ok()
}

fn start_bundled_workstation(exe_dir: &Path) -> Result<(), String> {
    if env::var_os("VERTEX_SESSION_PORTAL_SKIP_WORKSTATION_AUTO_START").is_some() {
        return Ok(());
    }
    if port_open() {
        return Ok(());
    }

    let root = exe_dir.join("resources").join("workstation-server");
    let binary = root.join("vertex-workstation.exe");
    if !binary.is_file() {
        return Err(format!("BUNDLED_WORKSTATION_MISSING:{}", binary.display()));
    }

    let mut command = Command::new(&binary);
    command
        .arg("workstation")
        .arg("serve")
        .arg("--bind")
        .arg(WORKSTATION_ADDR)
        .arg("--root")
        .arg(&root)
        .current_dir(&root)
        .env("VERTEX_WORKSTATION_ROOT", &root)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    #[cfg(windows)]
    command.creation_flags(CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP);

    command
        .spawn()
        .map_err(|e| format!("BUNDLED_WORKSTATION_SPAWN_FAILED:{e}"))?;

    let deadline = Instant::now() + Duration::from_secs(12);
    while Instant::now() < deadline {
        if port_open() {
            return Ok(());
        }
        sleep(Duration::from_millis(120));
    }

    Err("BUNDLED_WORKSTATION_START_TIMEOUT".to_string())
}

fn launch_portal_runtime(exe_dir: &Path) -> Result<(), String> {
    let runtime = exe_dir.join("Vertex Session Portal.runtime.exe");
    if !runtime.is_file() {
        return Err(format!("PORTAL_RUNTIME_MISSING:{}", runtime.display()));
    }

    let args: Vec<OsString> = env::args_os().skip(1).collect();
    let mut command = Command::new(&runtime);
    command
        .args(args)
        // Preserve the stable 000087V5 launch context exactly.
        .current_dir(exe_dir)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    #[cfg(windows)]
    command.creation_flags(CREATE_NO_WINDOW);

    command
        .spawn()
        .map_err(|e| format!("PORTAL_RUNTIME_SPAWN_FAILED:{e}"))?;

    Ok(())
}

fn main() {
    let exe = match env::current_exe() {
        Ok(v) => v,
        Err(_) => return,
    };
    let exe_dir: PathBuf = match exe.parent() {
        Some(v) => v.to_path_buf(),
        None => return,
    };

    if let Err(error) = start_bundled_workstation(&exe_dir) {
        // Fail-soft for the UI: Portal still launches and can surface Workstation state.
        write_error(&exe_dir, &error);
    }

    if let Err(error) = launch_portal_runtime(&exe_dir) {
        write_error(&exe_dir, &error);
    }
}
