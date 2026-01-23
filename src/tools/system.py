"""
System Control Tool - OS-level operations like closing apps, screen control
"""
import subprocess
import ctypes
import time
from typing import Optional


class SystemController:
    """System-level operations controller."""
    
    # Common application process names
    APP_PROCESSES = {
        "브라우저": ["chrome.exe", "msedge.exe", "firefox.exe", "whale.exe"],
        "chrome": ["chrome.exe"],
        "edge": ["msedge.exe"],
        "firefox": ["firefox.exe"],
        "whale": ["whale.exe"],
        "메모장": ["notepad.exe"],
        "notepad": ["notepad.exe"],
        "vscode": ["Code.exe"],
        "코드": ["Code.exe"],
        "explorer": ["explorer.exe"],
        "탐색기": ["explorer.exe"],
        "word": ["WINWORD.EXE"],
        "워드": ["WINWORD.EXE"],
        "excel": ["EXCEL.EXE"],
        "엑셀": ["EXCEL.EXE"],
        "powerpoint": ["POWERPNT.EXE"],
        "파워포인트": ["POWERPNT.EXE"],
        "카카오톡": ["KakaoTalk.exe"],
        "kakao": ["KakaoTalk.exe"],
    }
    
    def __init__(self):
        pass
    
    def close_application(self, app_name: str) -> dict:
        """Close an application by name."""
        app_lower = app_name.lower()
        
        # Find matching process names
        processes_to_kill = []
        for key, procs in self.APP_PROCESSES.items():
            if key.lower() in app_lower or app_lower in key.lower():
                processes_to_kill.extend(procs)
        
        # If no match found, try treating the name as a process name
        if not processes_to_kill:
            if not app_name.endswith('.exe'):
                app_name += '.exe'
            processes_to_kill = [app_name]
        
        # Remove duplicates
        processes_to_kill = list(set(processes_to_kill))
        
        closed = []
        failed = []
        
        for proc in processes_to_kill:
            try:
                result = subprocess.run(
                    ['taskkill', '/IM', proc, '/F'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    closed.append(proc)
                else:
                    # Process might not be running
                    if "not found" not in result.stderr.lower() and "찾을 수 없" not in result.stderr:
                        failed.append(proc)
            except Exception as e:
                failed.append(f"{proc}: {str(e)}")
        
        if closed:
            return {"success": True, "message": f"종료됨: {', '.join(closed)}"}
        elif not failed:
            return {"success": True, "message": f"'{app_name}'이(가) 실행 중이 아닙니다."}
        else:
            return {"success": False, "message": f"종료 실패: {', '.join(failed)}"}
    
    def open_application(self, app_name: str) -> dict:
        """Open an application by name."""
        app_lower = app_name.lower()
        
        # Common application paths
        app_commands = {
            "브라우저": "start msedge",
            "chrome": "start chrome",
            "edge": "start msedge",
            "firefox": "start firefox",
            "whale": "start whale",
            "메모장": "notepad",
            "notepad": "notepad",
            "vscode": "code",
            "코드": "code",
            "탐색기": "explorer",
            "explorer": "explorer",
            "cmd": "cmd",
            "터미널": "wt",  # Windows Terminal
            "powershell": "powershell",
            "계산기": "calc",
            "calculator": "calc",
            "설정": "start ms-settings:",
            "settings": "start ms-settings:",
        }
        
        cmd = None
        for key, command in app_commands.items():
            if key.lower() in app_lower or app_lower in key.lower():
                cmd = command
                break
        
        if not cmd:
            # Try to run as-is
            cmd = f"start {app_name}"
        
        try:
            subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return {"success": True, "message": f"'{app_name}' 실행됨"}
        except Exception as e:
            return {"success": False, "message": f"실행 실패: {str(e)}"}
    
    def screen_off(self) -> dict:
        """Turn off the monitor."""
        try:
            # Windows API to turn off monitor
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
            return {"success": True, "message": "모니터가 꺼졌습니다. 마우스를 움직이면 다시 켜집니다."}
        except Exception as e:
            return {"success": False, "message": f"모니터 끄기 실패: {str(e)}"}
    
    def shutdown_timer(self, minutes: int) -> dict:
        """Set a shutdown timer."""
        if minutes <= 0:
            # Cancel shutdown
            try:
                subprocess.run(['shutdown', '/a'], capture_output=True)
                return {"success": True, "message": "예약 종료가 취소되었습니다."}
            except:
                return {"success": True, "message": "취소할 예약 종료가 없습니다."}
        
        seconds = minutes * 60
        try:
            subprocess.run(['shutdown', '/s', '/t', str(seconds)], capture_output=True)
            return {"success": True, "message": f"컴퓨터가 {minutes}분 후 종료됩니다. 취소하려면 'shutdown_timer(0)'을 실행하세요."}
        except Exception as e:
            return {"success": False, "message": f"예약 종료 설정 실패: {str(e)}"}
    
    def get_running_apps(self) -> list[str]:
        """Get list of running applications."""
        try:
            result = subprocess.run(
                ['tasklist', '/FO', 'CSV', '/NH'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            apps = set()
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('","')
                    if parts:
                        proc_name = parts[0].strip('"')
                        # Filter common system processes
                        if not any(x in proc_name.lower() for x in ['svchost', 'system', 'runtime', 'host', 'service']):
                            apps.add(proc_name)
            
            return sorted(list(apps))[:30]
        except:
            return []


# LangChain Tool wrappers
def create_system_tools():
    """Create LangChain-compatible system control tools."""
    from langchain.tools import tool
    
    controller = SystemController()
    
    @tool
    def close_app(app_name: str) -> str:
        """
        Close a running application by name.
        
        Args:
            app_name: Name of the application to close (e.g., "chrome", "브라우저", "메모장")
        
        Returns:
            Result message indicating success or failure.
        """
        result = controller.close_application(app_name)
        if result['success']:
            return f"✅ {result['message']}"
        return f"❌ {result['message']}"
    
    @tool
    def open_app(app_name: str) -> str:
        """
        Open an application by name.
        
        Args:
            app_name: Name of the application to open (e.g., "chrome", "메모장", "vscode")
        
        Returns:
            Result message indicating success or failure.
        """
        result = controller.open_application(app_name)
        if result['success']:
            return f"✅ {result['message']}"
        return f"❌ {result['message']}"
    
    @tool
    def screen_off() -> str:
        """
        Turn off the monitor/screen. Move the mouse to turn it back on.
        
        Returns:
            Result message.
        """
        result = controller.screen_off()
        if result['success']:
            return f"✅ {result['message']}"
        return f"❌ {result['message']}"
    
    @tool
    def set_shutdown_timer(minutes: int) -> str:
        """
        Set a timer to shutdown the computer. Use 0 to cancel.
        
        Args:
            minutes: Number of minutes until shutdown (0 to cancel)
        
        Returns:
            Result message.
        """
        result = controller.shutdown_timer(minutes)
        if result['success']:
            return f"✅ {result['message']}"
        return f"❌ {result['message']}"
    
    @tool
    def list_running_apps() -> str:
        """
        Get a list of currently running applications.
        
        Returns:
            List of running application names.
        """
        apps = controller.get_running_apps()
        if apps:
            return "🖥️ 실행 중인 앱:\n" + "\n".join(f"• {app}" for app in apps)
        return "실행 중인 앱을 가져올 수 없습니다."
    
    return close_app, open_app, screen_off, set_shutdown_timer, list_running_apps, controller


if __name__ == "__main__":
    ctrl = SystemController()
    print("Running apps:", ctrl.get_running_apps()[:10])
