"""
Terminal User Interface (TUI) - Rich-based hacker-style interface
"""
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.table import Table
from rich.style import Style
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

console = Console()

# Custom styles
HEADER_STYLE = Style(color="bright_green", bold=True)
USER_STYLE = Style(color="bright_cyan")
AI_STYLE = Style(color="bright_white")
ERROR_STYLE = Style(color="bright_red")
INFO_STYLE = Style(color="bright_yellow")


def print_banner():
    """Print the startup banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ██╗      ██████╗  ██████╗ █████╗ ██╗         █████╗ ██╗        ║
║   ██║     ██╔═══██╗██╔════╝██╔══██╗██║        ██╔══██╗██║        ║
║   ██║     ██║   ██║██║     ███████║██║        ███████║██║        ║
║   ██║     ██║   ██║██║     ██╔══██║██║        ██╔══██║██║        ║
║   ███████╗╚██████╔╝╚██████╗██║  ██║███████╗   ██║  ██║██║        ║
║   ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝  ╚═╝╚═╝        ║
║                                                                   ║
║              On-Device Hybrid Agent System                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style=HEADER_STYLE)


def print_help():
    """Print help information."""
    table = Table(box=box.ROUNDED, border_style="bright_green")
    table.add_column("명령어", style="bright_cyan")
    table.add_column("설명", style="white")
    
    table.add_row("/help", "도움말 표시")
    table.add_row("/clear", "대화 기록 초기화")
    table.add_row("/tools", "사용 가능한 도구 목록")
    table.add_row("/index", "문서 인덱싱 실행")
    table.add_row("/quit", "프로그램 종료")
    
    console.print(Panel(table, title="🛠️ 명령어", border_style="bright_green"))


def print_tools(tool_names: list[str]):
    """Print available tools."""
    table = Table(box=box.ROUNDED, border_style="bright_cyan")
    table.add_column("#", style="dim")
    table.add_column("도구", style="bright_yellow")
    
    for i, name in enumerate(tool_names, 1):
        table.add_row(str(i), name)
    
    console.print(Panel(table, title="🔧 사용 가능한 도구", border_style="bright_cyan"))


def run_tui(workspace_path: str = ".", model_name: str = "phi3", auto_index: bool = True, extra_paths: list = None):
    """Run the TUI interface."""
    from src.agent import create_agent
    
    print_banner()
    
    console.print(f"\n[dim]워크스페이스: {Path(workspace_path).resolve()}[/dim]")
    if extra_paths:
        console.print(f"[dim]추가 경로: {', '.join(str(Path(p).resolve()) for p in extra_paths)}[/dim]")
    console.print(f"[dim]모델: {model_name}[/dim]\n")
    
    console.print("[yellow]🔄 에이전트 초기화 중...[/yellow]")
    
    import threading
    import time

    try:
        agent = create_agent(workspace_path, model_name, extra_paths)
        if auto_index:
            if not agent.searcher.is_indexed():
                console.print("[yellow]🎁 문서 인덱스가 비어있습니다. 자동 인덱싱을 시작합니다...[/yellow]")
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                    transient=True
                ) as progress:
                    task_id = progress.add_task("인덱싱 (다중 프로세스)...", total=None)
                    def update_progress(current, total, filename):
                        progress.update(task_id, total=total, completed=current, description=f"[cyan]{filename[:30]}...")
                    stats = agent.searcher.index_documents(progress_callback=update_progress)
                
                msg = f"[green]✅ 초기 인덱싱 완료: {stats['indexed']}개 파일 인덱싱됨.[/green]"
                console.print(msg)
            else:
                pass # Already indexed, skip silently or show brief message


        console.print("[green]✅ 에이전트 준비 완료![/green]\n")
        print_help()
    except Exception as e:
        console.print(f"[red]❌ 에이전트 초기화 실패: {e}[/red]")
        console.print("[yellow]Ollama가 실행 중인지 확인해주세요: ollama serve[/yellow]")
        return
    
    console.print("\n[dim]무엇을 도와드릴까요? (종료: /quit)[/dim]\n")
    
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower().strip()
                
                if cmd == "/quit" or cmd == "/exit":
                    console.print("\n[yellow]👋 안녕히 가세요![/yellow]\n")
                    break
                elif cmd == "/help":
                    print_help()
                elif cmd == "/clear":
                    agent.clear_history()
                    console.clear()
                    print_banner()
                    console.print("[green]✅ 대화 기록이 초기화되었습니다.[/green]\n")
                elif cmd == "/tools":
                    print_tools(agent.get_tool_names())
                elif cmd == "/index":
                    console.print("[yellow]🔄 문서 인덱싱 중...[/yellow]")
                    response = agent.invoke("문서를 인덱싱해줘")
                    console.print(Panel(Markdown(response), title="📚 인덱싱 결과", border_style="green"))
                elif cmd == "/reset":
                    if agent.searcher.clear_index():
                        console.print("[green]🗑️ 문서 인덱스가 완전히 삭제되었습니다. (재시작 시 다시 인덱싱)[/green]")
                    else:
                        console.print("[red]❌ 인덱스 삭제 실패[/red]")
                else:
                    console.print(f"[red]알 수 없는 명령어: {cmd}[/red]")
                continue
            
            # Process with agent
            with console.status("[bold green]🤔 생각 중...", spinner="dots"):
                response = agent.invoke(user_input)
            
            # Display response
            console.print()
            console.print(Panel(
                Markdown(response),
                title="🤖 AI",
                border_style="bright_white",
                padding=(1, 2)
            ))
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Ctrl+C 감지. 종료하려면 /quit을 입력하세요.[/yellow]")
        except Exception as e:
            console.print(f"[red]오류: {e}[/red]")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Local AI Agent TUI")
    parser.add_argument("--workspace", "-w", default=".", help="Workspace path")
    parser.add_argument("--model", "-m", default="phi3", help="Ollama model name")
    
    args = parser.parse_args()
    run_tui(args.workspace, args.model)
