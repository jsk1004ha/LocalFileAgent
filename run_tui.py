#!/usr/bin/env python
"""
Run the TUI (Terminal User Interface)
Usage: python run_tui.py
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.tui import run_tui

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run LocalFileAgent TUI")
    parser.add_argument("--workspace", "-w", default=r"C:\Users\js100\Desktop", help="Workspace path")
    parser.add_argument("--extra-paths", "-e", nargs="+", help="Additional paths to index", default=[
        r"C:\Users\js100\Downloads",
        r"C:\Users\js100\Documents\카카오톡 받은 파일"
    ])
    parser.add_argument("--model", "-m", default="llama3.1", help="Ollama model name")
    parser.add_argument("--no-auto-index", action="store_true", help="Skip indexing at startup")
    args = parser.parse_args()
    run_tui(workspace_path=args.workspace, model_name=args.model, auto_index=not args.no_auto_index, extra_paths=args.extra_paths)
