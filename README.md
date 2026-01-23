# LocalFileAgent

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**LocalFileAgent** is a powerful, privacy-focused AI agent that runs entirely on your local machine. It allows you to interact with your local files (documents, code, images) using natural language, leveraging the capabilities of local LLMs via Ollama.

Everything happens locally. No data leaves your computer.

**LocalFileAgent**는 로컬 컴퓨터에서 완벽하게 실행되는 강력한 개인 정보 보호 중심의 AI 에이전트입니다. Ollama를 통한 로컬 LLM 기능을 활용하여 자연어로 로컬 파일(문서, 코드, 이미지)과 상호 작용할 수 있습니다.

모든 작업은 로컬에서 수행되며, 데이터는 컴퓨터 외부로 유출되지 않습니다.

## 🚀 Key Features (주요 기능)

-   **Confidential Local RAG**: Index and search your documents without uploading them to the cloud.
    -   **보안 로컬 RAG**: 클라우드 업로드 없이 문서를 인덱싱하고 검색합니다.
-   **Smart File Management**: Ask the agent to find ("찾아줘") or open ("열어줘") files instantly.
    -   **스마트 파일 관리**: "찾아줘" 또는 "열어줘" 명령으로 파일을 즉시 찾거나 열 수 있습니다.
-   **Code Understanding**: Efficiently search and retrieve code snippets from your local projects.
    -   **코드 이해**: 로컬 프로젝트에서 코드 조각을 효율적으로 검색하고 추출합니다.
-   **TUI (Terminal User Interface)**: Fast, hacker-style experience.
    -   **TUI (터미널 사용자 인터페이스)**: 빠르고 직관적인 해커 스타일의 인터페이스를 제공합니다.
-   **Powered by Ollama**: Uses state-of-the-art open-source models (Llama 3, Phi-3, etc.).
    -   **Ollama 기반**: 최신 오픈 소스 모델(Llama 3, Phi-3 등)을 사용합니다.

## 📋 Prerequisites (필수 요구 사항)

Before you begin, ensure you have the following installed:
(시작하기 전에 다음 항목이 설치되어 있는지 확인하세요.)

-   [**Python 3.10+**](https://www.python.org/downloads/)
-   [**Ollama**](https://ollama.com/) (Required for running the local LLM / 로컬 LLM 실행에 필요)

## 🛠️ Installation (설치)

1.  **Clone the repository (저장소 복제):**
    ```bash
    git clone https://github.com/yourusername/LocalFileAgent.git
    cd LocalFileAgent
    ```

2.  **Create and activate a virtual environment (가상 환경 생성 및 활성화):**
    ```bash
    python -m venv venv
    
    # Windows (PowerShell)
    .\venv\Scripts\Activate
    
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies (종속성 설치):**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Pull the essential models (필수 모델 다운로드):**
    Make sure Ollama is running, then pull the model you intend to use (default is configured for `llama3.1` or `phi3`).
    
    Ollama가 실행 중인지 확인한 후, 사용할 모델을 다운로드하세요 (기본 설정은 `llama3.1` 또는 `phi3`입니다).
    ```bash
    ollama pull llama3.1
    # or
    ollama pull phi3
    ```

## 💻 Usage (사용법)

### Terminal User Interface (TUI)
Run the agent directly in your terminal:
(터미널에서 직접 에이전트를 실행하세요:)
```bash
python run_tui.py
```
**Commands (명령어):**
-   Type your query naturally. (자연어로 질문하세요.)
-   **`찾아줘 [files]`**: Search for files. (파일을 검색합니다.)
-   **`열어줘 [file]`**: Open a specific file. (특정 파일을 엽니다.)
-   **`/bye`** or **`/exit`**: Quit the application. (프로그램을 종료합니다.)

## 📂 Project Structure (프로젝트 구조)

```
LocalFileAgent/
├── .chromadb/           # Vector database storage (not tracked by git)
├── src/
│   ├── agent.py         # Main agent logic
│   ├── llm/             # LLM interface modules
│   ├── tools/           # Agent tools (search, file ops, system ops)
│   └── tui/             # Terminal UI implementation
├── verify_*.py          # Verification and test scripts
├── requirements.txt     # Python dependencies
├── run_tui.py           # Entry point for TUI
```

## 🤝 Contributing (기여하기)

Contributions are welcome! Please follow these steps:
(기여는 언제나 환영합니다! 다음 단계를 따라주세요:)
1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/YourFeature`).
3.  Commit your changes (`git commit -m 'Add some feature'`).
4.  Push to the branch (`git push origin feature/YourFeature`).
5.  Open a Pull Request.

## 📄 License (라이선스)

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
본 프로젝트는 Apache License 2.0에 따라 라이선스가 부여됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.
