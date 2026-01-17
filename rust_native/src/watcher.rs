use notify::{Config, RecommendedWatcher, RecursiveMode, Watcher, EventKind};
use std::path::Path;
use std::time::{Duration, Instant};
use crossbeam_channel::unbounded;
use serde_json::json;
use std::env;
use std::collections::HashMap;

fn main() -> notify::Result<()> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: stravinsky_watcher <path_to_watch>");
        std::process::exit(1);
    }
    
    let path_to_watch = &args[1];
    eprintln!("Watching: {}", path_to_watch);

    let (tx, rx) = unbounded();
    let mut watcher = RecommendedWatcher::new(tx, Config::default())?;
    watcher.watch(Path::new(path_to_watch), RecursiveMode::Recursive)?;

    // Debouncing state
    let mut last_events: HashMap<String, Instant> = HashMap::new();
    let debounce_duration = Duration::from_millis(500);

    for res in rx {
        match res {
            Ok(event) => {
                match event.kind {
                    EventKind::Create(_) | EventKind::Modify(_) | EventKind::Remove(_) => {
                        for path in event.paths {
                            let path_str = path.to_string_lossy().into_owned();
                            let now = Instant::now();
                            
                            let should_emit = if let Some(last_time) = last_events.get(&path_str) {
                                now.duration_since(*last_time) > debounce_duration
                            } else {
                                true
                            };

                            if should_emit {
                                last_events.insert(path_str.clone(), now);
                                let event_json = json!({
                                    "type": format!("{:?}", event.kind),
                                    "path": path_str,
                                    "timestamp": std::time::SystemTime::now()
                                        .duration_since(std::time::UNIX_EPOCH)
                                        .unwrap()
                                        .as_secs()
                                });
                                println!("{}", event_json.to_string());
                            }
                        }
                    }
                    _ => {}
                }
            }
            Err(e) => eprintln!("watch error: {:?}", e),
        }
    }

    Ok(())
}
