"""
Main Agent - Simplified ReAct agent with Ollama integration
"""
import json
import re
from pathlib import Path
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# System prompt for the agent
SYSTEM_PROMPT = """당신은 사용자의 로컬 문서를 분석하고 작업을 수행하는 AI 비서입니다.
'PrivateGPT'와 유사하게, 사용자의 **모든 질문은 기본적으로 문서 내용을 바탕으로 답변**해야 합니다.

*** 핵심 원칙 (RAG First) ***
1. 사용자가 질문을 하면 **무조건** `search_docs` 도구를 사용하여 관련 문서를 먼저 찾으세요. (인사말 제외)
2. 검색 결과가 있다면, 그 내용을 바탕으로 답변을 구성하세요. "문서에 따르면..."과 같은 인용구를 사용하면 좋습니다.
3. 문서에 없는 내용이라면 "문서에서 관련 내용을 찾을 수 없습니다"라고 솔직하게 말하세요. (지어내지 마세요)
4. 사용자가 특정 파일 열기/실행을 요청하면 `open_file` 등을 사용하세요.

*** 도구 사용 프로토콜 (XML) ***
도구 호출 시 **반드시** 아래 XML 형식을 엄격히 지키세요.

<tool>도구이름</tool>
<args>{"인자명": "값"}</args>

- 어떤 사담(예: "알겠습니다", "검색합니다")도 XML 밖에 붙이지 마세요. 오직 XML만 출력하거나, 최종 답변만 출력하세요.

*** 사용 가능한 도구 ***
- search_docs(query): 문서 내용 검색 (가장 자주 사용)
- index_documents(): 문서 인덱싱 (새로운 파일 추가 시 사용)
- add_search_path(path): 인덱싱할 추가 경로(폴더) 등록 (예: "D드라이브 추가해줘")
- open_file(filename): 파일 열기
- list_files(pattern): 파일 목록 조회
- read_file(filename): (필요시) 특정 파일 전체 읽기
- create_file(filename, content): 파일 생성
- open_app(app_name): 앱 실행
- close_app(app_name): 앱 종료
- screen_off(): 화면 끄기
"""


class LocalAgent:
    """Simplified ReAct agent that coordinates all tools."""
    
    def __init__(self, workspace_path: str, model_name: str = "llama3.1", extra_paths: list = None):
        self.workspace_path = Path(workspace_path).resolve()
        self.extra_paths = extra_paths
        self.model_name = model_name
        self.chat_history: list = []
        
        # Initialize LLM with improved settings
        self.llm = ChatOllama(
            model=model_name,
            temperature=0.0, # Zero temperature for precision
            num_predict=2048, # Increase context window for answer generation
            repeat_penalty=1.1,
            stop=["<|eot_id|>", "<|start_header_id|>", "<|end_header_id|>", "User:", "Question:"],
        )
        
        # Initialize tools
        self.tools = {}
        self.last_search_results = [] # Store last search context
        self._setup_tools()
        
    def _setup_tools(self):
        """Setup all tools."""
        from src.tools.search import DocumentSearcher
        from src.tools.file_ops import FileOperator
        from src.tools.system import SystemController
        
        # Initialize components
        self.searcher = DocumentSearcher(str(self.workspace_path), extra_paths=self.extra_paths)
        # 파일 조작 범위를 워크스페이스로 제한해 초기화 속도 개선
        self.file_op = FileOperator(str(self.workspace_path), extra_paths=self.extra_paths)
        self.system_ctrl = SystemController()
        
        # Register tools (accept **kwargs to tolerate extra args from the model)
        self.tools = {
            "search_docs": lambda query, **kwargs: self._format_search_results(self._compound_search(query)),
            "index_documents": lambda **kwargs: self._format_index_results(self.searcher.index_documents()),
            "add_search_path": lambda path, **kwargs: self._add_path_tool(path),
            "open_file": lambda filename="", user_query=None, **kwargs: self._format_result(self.file_op.open_file(filename, user_query)),
            "list_files": lambda pattern="*", path=None, **kwargs: self._format_files(self.file_op.list_files(pattern, path)),
            "read_file": lambda filename, **kwargs: self._format_read(self.file_op.read_file(filename)),
            "create_file": lambda filename, content, **kwargs: self._format_result(self.file_op.create_file(filename, content)),
            "open_app": lambda app_name, **kwargs: self._format_result(self.system_ctrl.open_application(app_name)),
            "close_app": lambda app_name, **kwargs: self._format_result(self.system_ctrl.close_application(app_name)),
            "screen_off": lambda **kwargs: self._format_result(self.system_ctrl.screen_off()),
            "list_running_apps": lambda **kwargs: "??? 실행 중인 앱:\\n" + "\\n".join(f"? {app}" for app in self.system_ctrl.get_running_apps()[:20]),
        }
        
    def _add_path_tool(self, path: str) -> str:
        """Add a new path to the searcher and re-index."""
        try:
            from pathlib import Path
            new_path = Path(path)
            if not new_path.exists():
                return f"❌ 경로가 존재하지 않습니다: {path}"
            
            # Add to searcher
            self.searcher.add_path(new_path)
            # Trigger delta index
            stats = self.searcher.index_documents()
            return f"✅ 경로가 추가되고 인덱싱되었습니다: {path}\n결과: {stats['indexed']}개 추가됨."
        except Exception as e:
            return f"❌ 경로 추가 실패: {str(e)}"
    
    def _compound_search(self, query: str) -> list[dict]:
        """Combine ChromaDB search with Fuzzy Filename search."""
        # 1. Semantic Search (DB)
        semantic_results = self.searcher.search(query)
        
        # 2. Fuzzy Filename Search (Live)
        fuzzy_results = self.file_op.fuzzy_find(query)
        
        # Convert fuzzy results to match search result format
        formatted_fuzzy = []
        for f in fuzzy_results:
            formatted_fuzzy.append({
                "path": str(f['path']),
                "filename": f['name'],
                "content_preview": f"Filename Match: {f['name']}",
                "score": f['score'] / 100.0, # Normalize to 0-1
                "match_type": "filename (live)"
            })
            
        # 3. Merge & Deduplicate
        seen_paths = set()
        final_results = []
        
        # Priority 1: High confidence fuzzy matches (e.g. > 85%) as they are likely what user asked for
        # But semantic search results usually come sorted by score too.
        
        all_candidates = formatted_fuzzy + semantic_results
        # Sort by score desc
        all_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        for res in all_candidates:
            p = str(res['path'])
            if p not in seen_paths:
                seen_paths.add(p)
                final_results.append(res)
                
        # Save context
        self.last_search_results = final_results[:15]
        return self.last_search_results

    def _resolve_references(self, text: str) -> str:
        """Resolve 'N번 파일' references using last search results."""
        if not self.last_search_results:
            return text
            
        def replace_match(match):
            try:
                # 1-based index from user
                idx = int(match.group(1)) - 1 
                if 0 <= idx < len(self.last_search_results):
                    target = self.last_search_results[idx]
                    return f"'{target['filename']}' ({target['path']})"
            except:
                pass
            return match.group(0)
            
        # Match pattern: "1번", "1번 파일", "1번 문서" etc.
        # But be careful not to match random numbers if possible. 
        # User usually says "1번 파일", "11번", etc.
        # Simple regex: number + '번'
        return re.sub(r'(\d+)번', replace_match, text)

    def _format_search_results(self, results: list) -> str:
        if not results:
            return "검색 결과가 없습니다."
        output = f"🔍 검색 결과 ({len(results)}개):\n\n"
        for i, r in enumerate(results, 1):
            output += f"{i}. **{r['filename']}**\n"
            output += f"   📁 경로: {r['path']}\n"
            output += f"   📊 유사도: {r['score']:.2%}\n\n"
        return output
    
    def _format_index_results(self, stats: dict) -> str:
        msg = f"✅ 인덱싱 완료!\n- 새로 인덱싱: {stats['indexed']}개"
        if stats.get('updated', 0) > 0:
            msg += f"\n- 업데이트: {stats['updated']}개"
        if stats.get('deleted', 0) > 0:
            msg += f"\n- 삭제 정리: {stats['deleted']}개"
        msg += f"\n- 변경없음: {stats['skipped']}개\n- 총 문서 수: {stats['total_in_db']}개"
        return msg
    
    def _format_result(self, result: dict) -> str:
        if result.get('success'):
            path_info = f"\n경로: {result['path']}" if result.get('path') else ""
            return f"✅ {result.get('message', 'Success')}{path_info}"
        alt_info = ""
        if result.get('alternatives'):
            alt_list = "\n- " + "\n- ".join(result['alternatives'])
            alt_info = f"\n대안 후보:{alt_list}"
        if result.get('requires_selection'):
            return f"❌ {result.get('message', 'Failed' if 'message' not in result else result['message'])}{alt_info}"
        return f"❌ {result.get('message', 'Failed')}{alt_info}"
    
    def _format_files(self, files: list) -> str:
        if not files:
            return "파일이 없습니다."
        output = f"📂 파일 목록 ({len(files)}개):\n\n"
        for f in files[:20]:
            size_kb = f['size'] / 1024
            output += f"• {f['name']} ({size_kb:.1f} KB)\n"
        if len(files) > 20:
            output += f"\n...외 {len(files) - 20}개 파일"
        return output
    
    def _format_read(self, result: dict) -> str:
        if result.get('success'):
            content = result['content']
            if len(content) > 2000:
                content = content[:2000] + "\n\n... [truncated]"
            return f"📄 파일 내용:\n\n{content}"
        return f"❌ {result.get('message', 'Failed')}"
    
    def _parse_tool_call(self, response: str) -> tuple[Optional[str], Optional[dict]]:
        """Parse tool call from LLM response."""
        tool_match = re.search(r'<tool>(\w+)</tool>', response)
        args_match = re.search(r'<args>(.+?)</args>', response, re.DOTALL)
        
        if tool_match:
            tool_name = tool_match.group(1)
            args = {}
            if args_match:
                try:
                    args = json.loads(args_match.group(1).strip())
                except json.JSONDecodeError:
                    pass
            return tool_name, args
        return None, None
    
    def _execute_tool(self, tool_name: str, args: dict, user_input: str | None = None) -> str:
        """Execute a tool and return the result."""
        if tool_name not in self.tools:
            return f"❌ 알 수 없는 도구: {tool_name}"
        
        try:
            tool_fn = self.tools[tool_name]
            if args:
                # pass original user input when available (e.g., for open_file)
                result = tool_fn(**args, user_query=user_input)
            else:
                result = tool_fn(user_query=user_input)
            return result
        except Exception as e:
            return f"❌ 도구 실행 오류: {str(e)}"
    
    def invoke(self, user_input: str, fast_mode: bool = False) -> str:
        """Process user input and return response. fast_mode=True이면 도구 실행 후 LLM을 다시 호출하지 않고 바로 결과를 반환합니다."""
        # Pre-process: Resolve references like "1번 파일"
        original_input = user_input
        user_input = self._resolve_references(user_input)
        if user_input != original_input:
            # print(f"[Context] Resolved input: {user_input}") # Log for debugging
            pass

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
        ]
        
        # Add chat history
        for msg in self.chat_history[-10:]:
            messages.append(msg)
        
        messages.append(HumanMessage(content=user_input))
        
        try:
            # Get LLM response
            response = self.llm.invoke(messages)
            response_text = response.content
            
            # Check for tool call
            tool_name, args = self._parse_tool_call(response_text)
            
            if tool_name:
                # Execute tool
                tool_result = self._execute_tool(tool_name, args, user_input)
                if fast_mode:
                    # 도구 결과만 바로 반환
                    self.chat_history.append(HumanMessage(content=user_input))
                    self.chat_history.append(AIMessage(content=tool_result))
                    return tool_result
                # Get final response with tool result
                messages.append(AIMessage(content=response_text))
                messages.append(HumanMessage(content=f"도구 실행 결과:\n{tool_result}\n\n이 결과를 바탕으로 사용자에게 답변해주세요."))
                
                final_response = self.llm.invoke(messages)
                final_text = final_response.content
                
                # Clean up any remaining tool tags and special tokens
                final_text = re.sub(r'<tool>.*?</tool>', '', final_text)
                final_text = re.sub(r'<args>.*?</args>', '', final_text, flags=re.DOTALL)
                final_text = re.sub(r'<\|[^|]+\|>', '', final_text)  # Clean <|solution|>, <|end|>, etc.
                final_text = re.sub(r'\n{3,}', '\n\n', final_text)  # Remove excessive newlines
                
                # Update chat history
                self.chat_history.append(HumanMessage(content=user_input))
                self.chat_history.append(AIMessage(content=final_text.strip()))
                
                return f"{tool_result}\n\n{final_text.strip()}"
            else:
                # No tool needed, direct response
                self.chat_history.append(HumanMessage(content=user_input))
                self.chat_history.append(AIMessage(content=response_text))
                
                return response_text
                
        except Exception as e:
            return f"❌ 오류가 발생했습니다: {str(e)}"
    
    def clear_history(self):
        """Clear chat history."""
        self.chat_history = []
    
    def get_tool_names(self) -> list[str]:
        """Get list of available tool names."""
        return list(self.tools.keys())


def create_agent(workspace_path: str = ".", model_name: str = "phi3", extra_paths: list = None) -> LocalAgent:
    """Factory function to create an agent."""
    return LocalAgent(workspace_path, model_name, extra_paths)


if __name__ == "__main__":
    import sys
    workspace = sys.argv[1] if len(sys.argv) > 1 else "."
    
    agent = create_agent(workspace)
    print(f"Agent created with tools: {agent.get_tool_names()}")
    
    # Test
    response = agent.invoke("파일 목록 보여줘")
    print(f"Response: {response}")
