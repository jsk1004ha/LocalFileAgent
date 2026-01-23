import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

from src.agent import create_agent

def test_rag():
    print("Initializing Agent with llama3.1...")
    # Using 'src' as workspace for safer/faster test if needed, but '.' is better for real test
    agent = create_agent(".", "llama3.1") 
    
    print("\n--- Test 1: Search Capability (Project Structure) ---")
    query = "LocalFileAgent의 프로젝트 구조를 알려줘"
    print(f"User: {query}")
    
    # We expect the agent to use search_docs first
    response = agent.invoke(query)
    print(f"Agent Response:\n{response}")
    
    if "src" in response or "agent.py" in response or "search.py" in response:
        print("\n✅ Test 1 Passed: Retrieved structure info.")
    else:
        print("\n⚠️ Test 1 Warning: Might not have retrieved structure strictly from docs.")

    print("\n--- Test 2: Code Search (Function Logic) ---")
    query = "search.py의 index_documents 함수가 어떻게 동작하는지 설명해줘"
    print(f"User: {query}")
    response = agent.invoke(query)
    print(f"Agent Response:\n{response}")
    
    if "index" in response.lower() and ("chromadb" in response.lower() or "vector" in response.lower() or "multiprocessing" in response.lower()):
        print("\n✅ Test 2 Passed: Retrieved code info.")
    else:
        print("\n❌ Test 2 Failed: Did not seem to use file context.")

if __name__ == "__main__":
    test_rag()
