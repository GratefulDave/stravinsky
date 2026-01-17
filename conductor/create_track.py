#!/usr/bin/env python3
"""
Conductor Track Creator
Usage: python3 conductor/create_track.py "Track Name" "Track Description"
"""

import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')

def create_track(name, description):
    date_str = datetime.now().strftime("%Y%m%d")
    track_slug = slugify(name)
    track_id = f"{track_slug}_{date_str}"
    
    base_dir = Path("conductor/tracks")
    track_dir = base_dir / track_id
    track_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. metadata.json
    metadata = {
        "track_id": track_id,
        "type": "feature",
        "status": "new",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "description": description
    }
    with open(track_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
        
    # 2. index.md
    index_content = f"""# Track {track_id} Context

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)
"""
    with open(track_dir / "index.md", "w") as f:
        f.write(index_content)
        
    # 3. spec.md
    spec_content = f"""# Track Specification: {name}

## Overview
{description}

## Objectives
1.  [Objective 1]
2.  [Objective 2]

## Scope
-   **In Scope:**
    -   [Item 1]
-   **Out of Scope:**
    -   [Item 2]
"""
    with open(track_dir / "spec.md", "w") as f:
        f.write(spec_content)
        
    # 4. plan.md
    plan_content = f"""# Implementation Plan - {name}

## Phase 1: Inception
- [ ] Task: Initialize track structure.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Inception' (Protocol in workflow.md)

## Phase 2: Implementation
- [ ] Task: [First task]
"""
    with open(track_dir / "plan.md", "w") as f:
        f.write(plan_content)
        
    # 5. Register in tracks.md
    tracks_file = Path("conductor/tracks.md")
    if tracks_file.exists():
        entry = f"\n- [ ] **Track: {name}**\n  *Link: [./conductor/tracks/{track_id}/](./conductor/tracks/{track_id}/)*\n"
        with open(tracks_file, "a") as f:
            f.write(entry)
            
    print(f"✅ Track created: {track_id}")
    print(f"📂 Location: {track_dir}")
    print(f"📝 Registered in: conductor/tracks.md")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 conductor/create_track.py <name> <description>")
        sys.exit(1)
        
    create_track(sys.argv[1], sys.argv[2])
