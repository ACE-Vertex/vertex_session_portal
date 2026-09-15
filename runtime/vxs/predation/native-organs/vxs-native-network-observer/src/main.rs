use std::env;

fn main() {
    let cmd = env::args().nth(1).unwrap_or_else(|| "identity".to_string());

    match cmd.as_str() {
        "identity" => {
            println!(r#"{{"schema":"vertex-vxs/native-organ-output-1","organ":"second-organ","organ_id":"vxs-native-network-observer","resource":"NETWORK","status":"SCAFFOLDED_TEST"}}"#);
        }
        "selftest" => {
            println!(r#"{{"schema":"vertex-vxs/native-organ-output-1","organ":"second-organ","organ_id":"vxs-native-network-observer","resource":"NETWORK","selftest":true}}"#);
        }
        _ => {
            eprintln!("unsupported genesis command");
            std::process::exit(2);
        }
    }
}
