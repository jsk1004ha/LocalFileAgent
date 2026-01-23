#!/usr/bin/env python
"""
Run the Web UI (Gradio interface)
Usage: python run_web.py
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.web import run_web

if __name__ == "__main__":
    # 기본 워크스페이스를 사용자 홈 디렉터리/Desktop 설정
    workspace = r"C:\Users\js100\Desktop"
    extra_paths = [
        r"C:\Users\js100\Downloads",
        r"C:\Users\js100\Documents\카카오톡 받은 파일"
    ]
    run_web(workspace_path=workspace, model_name="llama3.1", port=7860, extra_paths=extra_paths)
