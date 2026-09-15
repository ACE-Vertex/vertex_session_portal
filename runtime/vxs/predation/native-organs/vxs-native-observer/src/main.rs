use std::env;
use std::fs;
use std::path::Path;

fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

fn print_system() {
    let cwd = env::current_dir()
        .map(|p| p.display().to_string())
        .unwrap_or_default();

    println!(
        "{{\"schema\":\"vertex-vxs/native-organ-output-1\",\"organ\":\"system\",\"action\":\"observe\",\"os\":\"{}\",\"arch\":\"{}\",\"family\":\"{}\",\"cwd\":\"{}\",\"pid\":{}}}",
        esc(env::consts::OS),
        esc(env::consts::ARCH),
        esc(env::consts::FAMILY),
        esc(&cwd),
        std::process::id()
    );
}

fn print_exists(target: &str) {
    println!(
        "{{\"schema\":\"vertex-vxs/native-organ-output-1\",\"organ\":\"filesystem\",\"action\":\"exists\",\"target\":\"{}\",\"exists\":{}}}",
        esc(target),
        Path::new(target).exists()
    );
}

fn print_metadata(target: &str) -> Result<(), String> {
    let meta = fs::metadata(target).map_err(|e| e.to_string())?;
    let file_type = if meta.is_file() {
        "file"
    } else if meta.is_dir() {
        "directory"
    } else {
        "other"
    };

    let modified_ms = meta.modified()
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_millis().to_string())
        .unwrap_or_else(|| "null".to_string());

    println!(
        "{{\"schema\":\"vertex-vxs/native-organ-output-1\",\"organ\":\"filesystem\",\"action\":\"metadata\",\"target\":\"{}\",\"type\":\"{}\",\"readonly\":{},\"bytes\":{},\"modified_unix_ms\":{}}}",
        esc(target),
        file_type,
        meta.permissions().readonly(),
        meta.len(),
        modified_ms
    );
    Ok(())
}

fn print_list(target: &str) -> Result<(), String> {
    let mut entries = Vec::new();
    for entry in fs::read_dir(target).map_err(|e| e.to_string())?.take(128) {
        let entry = entry.map_err(|e| e.to_string())?;
        let name = entry.file_name().to_string_lossy().to_string();
        entries.push(format!("\"{}\"", esc(&name)));
    }

    println!(
        "{{\"schema\":\"vertex-vxs/native-organ-output-1\",\"organ\":\"filesystem\",\"action\":\"list\",\"target\":\"{}\",\"entries\":[{}]}}",
        esc(target),
        entries.join(",")
    );
    Ok(())
}

fn usage() {
    eprintln!("usage: vxs-native-organ <system|fs-exists|fs-meta|fs-list> [target]");
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let result = match args.get(1).map(String::as_str) {
        Some("system") => {
            print_system();
            Ok(())
        }
        Some("fs-exists") => {
            if let Some(target) = args.get(2) {
                print_exists(target);
                Ok(())
            } else {
                Err("target required".to_string())
            }
        }
        Some("fs-meta") => {
            if let Some(target) = args.get(2) {
                print_metadata(target)
            } else {
                Err("target required".to_string())
            }
        }
        Some("fs-list") => {
            if let Some(target) = args.get(2) {
                print_list(target)
            } else {
                Err("target required".to_string())
            }
        }
        _ => {
            usage();
            Err("unknown command".to_string())
        }
    };

    if let Err(err) = result {
        eprintln!("{}", err);
        std::process::exit(2);
    }
}
