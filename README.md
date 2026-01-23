# LocalFileAgent

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**LocalFileAgent** is a powerful, privacy-focused AI agent that runs entirely on your local machine. Inspired by PrivateGPT, it allows you to interact with your local files (documents, code, images) using natural language, leveraging the capabilities of local LLMs via Ollama.

Everything happens locally. No data leaves your computer.

## 🚀 Key Features

-   **Confidential Local RAG**: Index and search your documents without uploading them to the cloud.
-   **Smart File Management**: Ask the agent to find ("찾아줘") or open ("열어줘") files instantly.
-   **Code Understanding**: Efficiently search and retrieve code snippets from your local projects.
-   **Dual Interface**:
    -   **TUI (Terminal User Interface)** for a fast, hacker-style experience.
    -   **Web UI** for a modern, accessible chat interface.
-   **Powered by Ollama**: Uses state-of-the-art open-source models (Llama 3, Phi-3, etc.).

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

-   [**Python 3.10+**](https://www.python.org/downloads/)
-   [**Ollama**](https://ollama.com/) (Required for running the local LLM)

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/LocalFileAgent.git
    cd LocalFileAgent
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    
    # Windows (PowerShell)
    .\venv\Scripts\Activate
    
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Pull the essential models:**
    Make sure Ollama is running, then pull the model you intend to use (default is configured for `llama3.1` or `phi3`).
    ```bash
    ollama pull llama3.1
    # or
    ollama pull phi3
    ```

## 💻 Usage

### Terminal User Interface (TUI)
Run the agent directly in your terminal:
```bash
python run_tui.py
```
**Commands:**
-   Type your query naturally.
-   **`찾아줘 [files]`**: Search for files.
-   **`열어줘 [file]`**: Open a specific file.
-   **`/bye`** or **`/exit`**: Quit the application.

### Web Interface
Launch the web-based chat interface:
```bash
python run_web.py
```
Then open your browser and navigate to `http://localhost:8000` (or the port displayed in the terminal).

## 📂 Project Structure

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
└── run_web.py           # Entry point for Web UI
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/YourFeature`).
3.  Commit your changes (`git commit -m 'Add some feature'`).
4.  Push to the branch (`git push origin feature/YourFeature`).
5.  Open a Pull Request.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
