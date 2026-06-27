# ILLIP AI Deployment & Migration Guide

This guide explains how to migrate the ILLIP AI project to a new laptop and set it up cleanly using the automated, portable installation system.

---

## 1. Directory Migration Plan

When copying the codebase to a new laptop, copy only the core source and configuration files. Do **NOT** copy virtual environments or temporary compiler caches to avoid path conflicts and binary mismatches.

### **Files to COPY**
Zip or transfer the following directories and files:
* `/app` - Backend API, routes, business logic, agents, and providers.
* `/frontend` - Static client-side UI (`index.html`, `styles.css`, `app.js`).
* `/tests` - Diagnostic and validation test suites.
* `/docs` - System documentation logs.
* `requirements.txt` - Python environment package dependencies.
* `.env.example` - Default environment configuration template.
* `setup.bat` / `setup.ps1` - Virtual environment setup scripts.
* `start.bat` / `start.ps1` - Application launcher scripts.
* `check_system.ps1` - Prerequisites checking script.
* `README.md` - Standard project documentation.

### **Files to EXCLUDE**
Omit these directories during transfer (they will be rebuilt automatically at installation/startup):
* `.venv/` - Recreated locally by `setup.bat`.
* `data/` - Created on first launch by backend initialization.
* `__pycache__/` - Rebuilt by Python compiler.
* `.pytest_cache/` - Recreated when running tests.

---

## 2. Setting Up the Target Laptop

Follow these steps to deploy and run ILLIP AI on the new laptop:

### **Step 1: Install Prerequisites**
Ensure the target machine has the following dependencies:
1. **Python 3.10+** (Python 3.11.9 is verified and recommended). 
   * *Important:* Ensure the **"Add Python to PATH"** checkbox is selected during installation.
2. **Ollama LLM Engine**
   * Download and install from [ollama.com](https://ollama.com/).
   * Pull the target model from your terminal:
     ```powershell
     ollama pull qwen2.5:3b
     ```

### **Step 2: Run Setup Wrapper**
1. Unzip the project folder on the target laptop.
2. Double-click `setup.bat` to launch the automated installer.
3. The setup script will:
   * Create a local Python virtual environment (`.venv`).
   * Upgrade pip and install all required packages from `requirements.txt`.
   * Create your operational `.env` file from the `.env.example` template.
   * Recreate local data directories.
   * Run diagnostic tests to verify your environment readiness.

### **Step 3: Run the Server**
1. Double-click `start.bat` to launch the server wrapper.
2. The script will activate `.venv` and boot the FastAPI uvicorn server.
3. Access the assistant:
   * **Web UI:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
   * **API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 3. Running Diagnostic Controls manually

You can execute diagnostic checks at any time to verify system, database, and model compatibility:

1. Open PowerShell inside the project directory.
2. Run the diagnostic script:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\check_system.ps1
   ```
3. Read the output report to verify that Python, Ollama, the `.env` settings, and required directories are fully prepared.

---

## 4. Troubleshooting

* **Script execution is disabled warning:**
  * Windows may block PowerShell scripts by default. The provided `.bat` wrappers solve this automatically by setting `-ExecutionPolicy Bypass` for the running shell instance.
* **"python is not recognized" error:**
  * Make sure Python is installed and added to the user PATH environment variables. If you installed it recently, restart your terminal or laptop.
* **Ollama health check failing:**
  * Make sure the Ollama application is active in your system tray or run `ollama serve` in a terminal window.
