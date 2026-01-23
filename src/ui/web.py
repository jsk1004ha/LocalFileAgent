"""
Web UI - Gradio-based chat interface (Simplified)
"""
import sys
from pathlib import Path

import gradio as gr

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Global agent instance
agent = None
workspace = None
model = None
extra_paths_list = None


def get_agent():
    """Lazy initialization of agent."""
    global agent, workspace, model, extra_paths_list
    if agent is None:
        from src.agent import create_agent
        agent = create_agent(workspace or ".", model or "phi3", extra_paths=extra_paths_list)
    return agent


def chat(message: str, history: list) -> tuple:
    """Chat function for Gradio."""
    if not message.strip():
        return history, ""
    
    try:
        ag = get_agent()
        response = ag.invoke(message)
        history.append((message, response))
        return history, ""
    except Exception as e:
        history.append((message, f"❌ 오류: {str(e)}"))
        return history, ""


def index_documents():
    """Index documents."""
    try:
        ag = get_agent()
        return ag.invoke("문서를 인덱싱해줘")
    except Exception as e:
        return f"❌ 오류: {str(e)}"


def clear_history():
    """Clear chat history."""
    global agent
    if agent is not None:
        agent.clear_history()
    return [], ""


def create_ui(workspace_path: str = ".", model_name: str = "phi3", extra_paths: list = None):
    """Create the Gradio UI."""
    global workspace, model, extra_paths_list
    workspace = workspace_path
    model = model_name
    extra_paths_list = extra_paths
    
    with gr.Blocks(
        title="Local AI Agent",
        theme=gr.themes.Soft(
            primary_hue="emerald",
            secondary_hue="cyan",
            neutral_hue="slate",
        ),
    ) as demo:
        
        # Header
        gr.Markdown("""
        # 🤖 Local AI Agent
        **On-Device Hybrid Agent System**
        
        파일 검색, 실행, 시스템 제어를 할 수 있는 로컬 AI 에이전트입니다.
        """)
        
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="대화",
                    height=450,
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="무엇을 도와드릴까요? (예: 파일 목록 보여줘)",
                        scale=4,
                        show_label=False,
                    )
                    send_btn = gr.Button("전송", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ 대화 초기화")
                    index_btn = gr.Button("📚 문서 인덱싱")
                    reset_btn = gr.Button("🧨 인덱스 초기화", variant="stop")
            
            with gr.Column(scale=1):
                gr.Markdown(f"""
                ### 📂 워크스페이스
                `{Path(workspace_path).resolve()}`
                
                ### 🧠 모델
                `{model_name}`
                
                ### ⚡ 사용 예시
                - "파일 목록 보여줘"
                - "requirements 파일 찾아줘"
                - "메모장 열어줘"
                - "실행 중인 앱 보여줘"
                """)
                
                status_output = gr.Textbox(
                    label="상태",
                    interactive=False,
                    lines=3,
                )
        
        # Event handlers
        send_btn.click(chat, [msg, chatbot], [chatbot, msg])
        msg.submit(chat, [msg, chatbot], [chatbot, msg])
        clear_btn.click(clear_history, outputs=[chatbot, msg])
        index_btn.click(index_documents, outputs=[status_output])
        
        def reset_index():
            try:
                ag = get_agent()
                if ag.searcher.clear_index():
                    return "✅ 인덱스가 초기화되었습니다. 재시작하면 자동 인덱싱됩니다."
                return "❌ 인덱스 초기화 실패"
            except Exception as e:
                return f"❌ 오류: {e}"
                
        reset_btn.click(reset_index, outputs=[status_output])
    
    return demo


def run_web(workspace_path: str = ".", model_name: str = "phi3", port: int = 7860, extra_paths: list = None):
    """Run the web UI."""
    print(f"🚀 Starting Web UI...")
    print(f"📂 Workspace: {Path(workspace_path).resolve()}")
    if extra_paths:
        print(f"📂 Extra Paths: {extra_paths}")
    print(f"🧠 Model: {model_name}")
    print(f"🌐 URL: http://localhost:{port}")
    
    demo = create_ui(workspace_path, model_name, extra_paths)
    
    # Auto-Index Check on Startup
    print("🔄 Checking index status...")
    ag = get_agent()
    if not ag.searcher.is_indexed():
        print("🎁 Index is empty. Starting auto-indexing...")
        try:
            stats = ag.searcher.index_documents()
            print(f"✅ Auto-indexing complete: {stats['indexed']} files indexed.")
        except Exception as e:
            print(f"❌ Auto-indexing failed: {e}")
    else:
        print("✅ Index found. Ready.")

    demo.launch(
        server_port=port,
        share=False,
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Local AI Agent Web UI")
    parser.add_argument("--workspace", "-w", default=".", help="Workspace path")
    parser.add_argument("--model", "-m", default="phi3", help="Ollama model name")
    parser.add_argument("--port", "-p", type=int, default=7860, help="Server port")
    
    args = parser.parse_args()
    run_web(args.workspace, args.model, args.port)
