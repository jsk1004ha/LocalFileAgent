"""
File Operations Tool - File execution and manipulation with fuzzy matching
"""
import os
import re
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Callable

from fuzzywuzzy import fuzz, process


class FileOperator:
    """File operations with fuzzy matching support."""
    
    # Dangerous operations that require confirmation
    DANGEROUS_COMMANDS = {'delete', 'remove', 'rm', 'del', '삭제', '지워', '제거'}
    
    def __init__(self, base_path: str, confirm_callback: Optional[Callable] = None, extra_paths: list = None):
        self.base_path = Path(base_path)
        self.extra_paths = [Path(p) for p in (extra_paths or [])]
        self.all_paths = [self.base_path] + self.extra_paths
        self.confirm_callback = confirm_callback or self._default_confirm
        self._file_cache: list[Path] = []
    
    def _default_confirm(self, message: str) -> bool:
        """Default confirmation (always returns False for safety)."""
        return False
    
    def _refresh_cache(self):
        """Refresh the file cache."""
        self._file_cache = []
        skip_dirs = {
            "AppData",
            "$Recycle.Bin",
            "ProgramData",
            "Windows",
            "System Volume Information",
            "venv",
            ".venv",
            "node_modules",
            "__pycache__",
        }

        for search_path in self.all_paths:
            if not search_path.exists():
                continue
                
            for root, dirs, files in os.walk(search_path, topdown=True, onerror=lambda e: None):
                # Prune directories to avoid permission issues and hidden/system folders
                dirs[:] = [
                    d for d in dirs
                    if d not in skip_dirs and not d.startswith('.')
                ]
                for name in files:
                    try:
                        path = Path(root) / name
                        if any(part.startswith('.') for part in path.parts):
                            continue
                        self._file_cache.append(path)
                    except OSError:
                        # Skip files/dirs that cannot be accessed
                        continue
    
    def fuzzy_find(self, query: str, threshold: int = 70) -> list[dict]:
        """Find files using fuzzy matching (token + partial)."""
        if not self._file_cache:
            self._refresh_cache()
        
        results = []
        for file_path in self._file_cache:
            # Match against filename and full path
            name_score = fuzz.partial_ratio(query.lower(), file_path.name.lower())
            token_score = fuzz.token_set_ratio(query.lower(), file_path.name.lower())
            path_score = fuzz.partial_ratio(query.lower(), str(file_path).lower())
            best_score = max(name_score, token_score, path_score)
            
            if best_score >= threshold:
                results.append({
                    "path": file_path,
                    "name": file_path.name,
                    "score": best_score
                })
        
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:10]  # Return top 10
    
    def open_file(self, filename: str, user_query: Optional[str] = None) -> dict:
        """Open a file with the default application. Falls back to user query if model-supplied name fails."""
        stopwords = {"파일", "열어줘", "열어", "열어줘요", "열어 줘", "열어주세요", "줘", "주세요"}

        def attempt(query: str) -> dict:
            q = query.strip()
            if not q:
                return {"success": False, "message": "파일명이 비어 있습니다."}

            # Try exact match first
            exact_path = (self.base_path / q).resolve()
            if exact_path.exists():
                os.startfile(str(exact_path))
                return {"success": True, "path": str(exact_path), "message": f"'{exact_path.name}' 파일을 열었습니다."}
            
            # Exact name match anywhere in workspace (case-insensitive)
            exact_name_matches = [f for f in self._file_cache if f.name.lower() == q.lower()]
            if len(exact_name_matches) == 1:
                target = exact_name_matches[0]
                os.startfile(str(target))
                return {"success": True, "path": str(target), "message": f"'{target.name}' 파일을 열었습니다."}
            elif len(exact_name_matches) > 1:
                return {
                    "success": False,
                    "message": f"'{q}' 이름의 파일이 여러 개 있습니다. 정확한 경로를 지정해주세요.",
                    "alternatives": [str(p) for p in exact_name_matches[:5]]
                }
            
            # Keyword containment match (한국어/공백 그대로)
            tokens = [t for t in re.split(r"\s+", q) if t and t not in stopwords]
            keyword_hits = []
            if tokens:
                for f in self._file_cache:
                    name = f.name.lower()
                    if all(t.lower() in name for t in tokens):
                        keyword_hits.append(f)
            if len(keyword_hits) == 1:
                target = keyword_hits[0]
                os.startfile(str(target))
                return {"success": True, "path": str(target), "message": f"'{target.name}' 파일을 열었습니다."}
            elif len(keyword_hits) > 1:
                return {
                    "success": False,
                    "requires_selection": True,
                    "message": f"'{q}'과(와) 일치하는 후보가 여러 개입니다. 정확한 경로를 선택해주세요.",
                    "alternatives": [str(p) for p in keyword_hits[:5]]
                }

            # Try fuzzy match (stricter threshold to avoid unrelated files)
            matches = self.fuzzy_find(q, threshold=80)
            if not matches:
                return {"success": False, "message": f"'{q}'과(와) 일치하는 파일을 찾을 수 없습니다."}
            
            # Do not auto-open on fuzzy hit; ask for confirmation
            return {
                "success": False,
                "requires_selection": True,
                "message": f"'{q}'을(를) 정확히 찾지 못했습니다. 가장 유사한 파일을 선택해주세요.",
                "alternatives": [str(m['path']) for m in matches[:5]]
            }

        # Refresh cache once
        self._refresh_cache()
        attempts = []
        for q in [filename, user_query]:
            if q is None:
                continue
            q = q.strip()
            if not q:
                continue
            attempts.append(q)

        if not attempts:
            return {"success": False, "message": "파일명이 비어 있습니다."}

        failures = []
        for q in attempts:
            result = attempt(q)
            if result.get("success"):
                return result
            failures.append(result)

        # return most recent failure (likely from user query)
        return failures[-1]
    
    def list_files(self, pattern: str = "*", path: Optional[str] = None) -> list[dict]:
        """List files matching a pattern. Optional `path` limits search to a subdirectory."""
        results = []
        target_root = self.base_path
        if path:
            target_root = (self.base_path / path).resolve()
            # Only search if subpath exists inside base
            try:
                target_root.relative_to(self.base_path)
            except ValueError:
                return []
            if not target_root.exists():
                return []
        
        if path:
            skip_dirs = {"AppData", "$Recycle.Bin", "ProgramData", "Windows", "System Volume Information"}
            for root, dirs, files in os.walk(target_root, topdown=True, onerror=lambda e: None):
                dirs[:] = [
                    d for d in dirs
                    if d not in skip_dirs and not d.startswith('.')
                ]
                for name in files:
                    file_path = Path(root) / name
                    if any(part.startswith('.') for part in file_path.parts):
                        continue
                    if pattern == "*" or file_path.match(pattern) or pattern.lower() in name.lower():
                        try:
                            stat = file_path.stat()
                            results.append({
                                "name": name,
                                "path": str(file_path),
                                "size": stat.st_size,
                                "modified": stat.st_mtime
                            })
                        except OSError:
                            continue
        else:
            self._refresh_cache()
            for f in self._file_cache:
                if pattern == "*" or f.match(pattern) or pattern.lower() in f.name.lower():
                    results.append({
                        "name": f.name,
                        "path": str(f),
                        "size": f.stat().st_size,
                        "modified": f.stat().st_mtime
                    })
        
        return results[:50]  # Limit results
    
    def read_file(self, filename: str) -> dict:
        """Read file content."""
        # Try exact match first
        exact_path = self.base_path / filename
        if not exact_path.exists():
            matches = self.fuzzy_find(filename)
            if not matches:
                return {"success": False, "content": None, "message": f"파일을 찾을 수 없습니다: {filename}"}
            exact_path = matches[0]['path']
        
        try:
            with open(exact_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"success": True, "content": content, "path": str(exact_path)}
        except UnicodeDecodeError:
            try:
                with open(exact_path, 'r', encoding='cp949') as f:
                    content = f.read()
                return {"success": True, "content": content, "path": str(exact_path)}
            except:
                return {"success": False, "content": None, "message": "파일을 읽을 수 없습니다 (인코딩 오류)"}
    
    def create_file(self, filename: str, content: str) -> dict:
        """Create a new file inside the workspace without replacing existing data."""
        try:
            if not isinstance(filename, str) or not filename.strip():
                raise ValueError("파일명이 비어 있습니다.")
            if not isinstance(content, str):
                raise ValueError("파일 내용은 문자열이어야 합니다.")

            workspace = self.base_path.resolve()
            candidate = self.base_path / filename
            # Even a dangling link is an existing entry, not a new file.
            if candidate.is_symlink():
                raise FileExistsError("이미 존재하는 파일이나 링크입니다.")
            file_path = candidate.resolve()
            if file_path == workspace or not file_path.is_relative_to(workspace):
                raise ValueError("작업 폴더 안의 파일 경로를 지정해주세요.")

            # Validate before creating directories, including symlinked parents.
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation also protects against another writer creating
            # the same destination after validation.
            with open(file_path, 'x', encoding='utf-8') as f:
                f.write(content)
            self._refresh_cache()
            return {"success": True, "path": str(file_path), "message": f"파일 생성됨: {file_path.name}"}
        except FileExistsError:
            return {"success": False, "message": "파일 생성 실패: 같은 경로에 파일이나 링크가 이미 존재합니다. 다른 이름을 지정해주세요."}
        except Exception as e:
            return {"success": False, "message": f"파일 생성 실패: {str(e)}"}
    
    def delete_file(self, filename: str, confirmed: bool = False) -> dict:
        """Delete a file (requires confirmation)."""
        # Find the file
        exact_path = self.base_path / filename
        if not exact_path.exists():
            matches = self.fuzzy_find(filename)
            if not matches:
                return {"success": False, "message": f"파일을 찾을 수 없습니다: {filename}"}
            exact_path = matches[0]['path']
        
        if not confirmed:
            return {
                "success": False,
                "requires_confirmation": True,
                "path": str(exact_path),
                "message": f"⚠️ 정말로 '{exact_path.name}' 파일을 삭제하시겠습니까? (이 작업은 되돌릴 수 없습니다)"
            }
        
        # Confirmed - proceed with deletion
        try:
            exact_path.unlink()
            self._refresh_cache()
            return {"success": True, "message": f"파일이 삭제되었습니다: {exact_path.name}"}
        except Exception as e:
            return {"success": False, "message": f"삭제 실패: {str(e)}"}


# LangChain Tool wrappers
def create_file_tools(base_path: str, confirm_callback=None):
    """Create LangChain-compatible file operation tools."""
    from langchain.tools import tool
    
    operator = FileOperator(base_path, confirm_callback)
    
    @tool
    def open_file(filename: str) -> str:
        """
        Open a file with the default application. Uses fuzzy matching to find files
        even if the name is not exact.
        
        Args:
            filename: Name or partial name of the file to open
        
        Returns:
            Result message indicating success or failure.
        """
        result = operator.open_file(filename)
        if result['success']:
            msg = result['message']
            if result.get('alternatives'):
                msg += f"\n\n다른 후보: {', '.join(result['alternatives'])}"
            return msg
        return f"❌ {result['message']}"
    
    @tool
    def list_files(pattern: str = "*") -> str:
        """
        List files in the workspace. Can filter by pattern or keyword.
        
        Args:
            pattern: File pattern or keyword to filter (default: "*" for all files)
        
        Returns:
            List of matching files with their details.
        """
        files = operator.list_files(pattern)
        if not files:
            return f"'{pattern}' 패턴과 일치하는 파일이 없습니다."
        
        output = f"📂 파일 목록 ({len(files)}개):\n\n"
        for f in files[:20]:
            size_kb = f['size'] / 1024
            output += f"• {f['name']} ({size_kb:.1f} KB)\n"
        
        if len(files) > 20:
            output += f"\n...외 {len(files) - 20}개 파일"
        
        return output
    
    @tool
    def read_file(filename: str) -> str:
        """
        Read the content of a file.
        
        Args:
            filename: Name or partial name of the file to read
        
        Returns:
            The file content or error message.
        """
        result = operator.read_file(filename)
        if result['success']:
            content = result['content']
            if len(content) > 3000:
                content = content[:3000] + f"\n\n... [파일이 너무 길어 {len(result['content'])}자 중 일부만 표시됨]"
            return f"📄 {result['path']}:\n\n{content}"
        return f"❌ {result['message']}"
    
    @tool  
    def create_file(filename: str, content: str) -> str:
        """
        Create a new file with the given content.
        
        Args:
            filename: Name of the file to create (can include subdirectories)
            content: Content to write to the file
        
        Returns:
            Success or error message.
        """
        result = operator.create_file(filename, content)
        if result['success']:
            return f"✅ {result['message']}"
        return f"❌ {result['message']}"
    
    return open_file, list_files, read_file, create_file, operator


if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    op = FileOperator(base)
    print(op.list_files())
    print(op.fuzzy_find("req"))
