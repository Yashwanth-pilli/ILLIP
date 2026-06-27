# Portability Guide

## Design Principles

ILLIP AI is designed for portability across Windows, Mac, and Linux laptops.

## Moving to Another Machine

### Step 1: Prepare Source Code

```bash
# Copy entire project directory
# All paths are relative, so project works as-is
copy /S ILLIP_AI C:\path\on\new\machine\
```

### Step 2: Environment Setup

On new machine:

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Data Migration

To move your chat history and tasks:

```powershell
# Old machine - backup data
copy /S .\data\*.db .\backup\
copy /S .\data\memory\ .\backup\
copy /S .\data\tasks\ .\backup\

# On new machine - restore data
copy /S .\backup\*.db .\data\
copy /S .\backup\memory\ .\data\
copy /S .\backup\tasks\ .\data\
```

### Step 4: Configuration

Copy .env file (update paths if needed):

```powershell
copy .env.example .env
# Edit .env if using different LLM provider
```

### Step 5: Verify

```powershell
# Run tests to verify everything works
pytest -v

# Start backend
python -m uvicorn app.main:app --reload
```

## Path Configuration

All paths are configured in **app/config.py**:

```python
data_dir = "./data"              # Local data storage
memory_dir = "./data/memory"     # Chat memory
logs_dir = "./data/logs"         # Application logs
tasks_dir = "./data/tasks"       # Task files
```

These are relative to project root, so they automatically adapt.

## What's Portable

✅ **Portable:**
- All Python source code
- Frontend files (HTML/CSS/JS)
- Configuration templates (.env.example)
- Test suite
- Documentation

❌ **Not Portable** (machine-specific):
- Virtual environment (data/venv/) → Recreate on new machine
- Database with local paths → May need path fixes
- Environment variables (.env) → Update for new machine

## What Gets Left Behind

These should NOT be copied to new machine:

```
.gitignore items:
- __pycache__/
- *.pyc
- .venv/
- .env (use .env.example instead)
- data/*.db (if migrating, copy separately)
- data/logs/*
```

## Backup Strategy

Before moving machines:

```powershell
# Create backup
mkdir ./backups
copy .env ./backups/.env.backup
copy /S ./data ./backups/data_backup

# Copy to external drive or cloud storage
```

## Cross-Platform Notes

### Windows
- Uses backslash paths: `.\data\`
- PowerShell scripts available in `./scripts`

### Mac/Linux
- Use forward slashes: `./data/`
- Use bash instead of PowerShell
- Change scripts to .sh files

### Converting Between Platforms

1. Python code is platform-agnostic (uses pathlib)
2. Update scripts for target OS
3. Use relative paths everywhere
4. Test carefully on new platform

## Version Compatibility

Ensure target machine has:
- Python 3.9+ (tested on 3.9, 3.10, 3.11)
- 100MB free disk space minimum
- Network access (for initial setup only)

## Troubleshooting Migration

**Database won't work:**
- Delete .db file and start fresh
- Database schema will auto-create

**Imports fail:**
- Verify venv is activated
- Run `pip install -r requirements.txt` again

**Paths not found:**
- Check .env file points to correct locations
- Verify data/ directory structure exists

**Logs won't write:**
- Check data/logs/ directory has write permissions
- chmod 755 data/logs/ (on Mac/Linux)

## Future Scaling

When ready to scale beyond laptop:

- Database: Migrate SQLite to PostgreSQL
- Storage: Move data/logs/ to cloud storage
- Backend: Deploy to cloud VM or container
- Frontend: Deploy to static hosting

All without changing application code due to abstraction layers!
