# 🚀 Quick Start Guide

## Super Quick (First Time)

1. **Make sure Ollama is running with gemma2:2b**:
   ```bash
   ollama serve
   ollama pull gemma2:2b
   ```

2. **Make sure CEREBRUM is running**:
   ```bash
   # In CEREBRUM directory
   python launcher.py
   ```

3. **Start training** (dependencies auto-install!):
   ```bash
   cd C:\Users\dbiss\Desktop\Projects\Personal\llm-trainer
   python start_training.py
   ```

**That's it!** Dependencies will be checked and installed automatically.

---

## What Happens

When you run `python start_training.py`:

1. ✅ **Auto-checks dependencies** (fastapi, uvicorn, requests, pydantic)
2. ✅ **Auto-installs missing packages**
3. ✅ **Verifies CEREBRUM is running**
4. ✅ **Starts LLM Server** (auto-finds port 8030-8035)
5. ✅ **Starts Middleware** (port 8032)
6. ✅ **Begins conversation training**
7. ✅ **Shows real-time progress**

---

## Manual Dependency Check

If you want to just check/install dependencies without starting:

```bash
python check_dependencies.py
```

Or check without installing:

```bash
python check_dependencies.py --no-install
```

---

## Expected Output

```
Checking dependencies before starting...

======================================================================
Checking Dependencies
======================================================================
✓ fastapi
✓ uvicorn
✓ requests
✓ pydantic

✓ All dependencies satisfied!
======================================================================

Checking services...
✓ Middleware is running
✓ CEREBRUM is accessible
✓ LLM Server is accessible

======================================================================
All services ready! Starting training...
======================================================================

Monitoring progress (Ctrl+C to stop)...

Progress: 10/100 exchanges | Topic: What are your thoughts on cons...
Progress: 20/100 exchanges | Topic: How do you think learning and ...
...
```

---

## Troubleshooting

### "Cannot connect to Ollama"
```bash
# Start Ollama
ollama serve

# In another terminal, pull the model
ollama pull gemma2:2b
```

### "Cannot connect to CEREBRUM"
```bash
# Make sure CEREBRUM is running
cd C:\Users\dbiss\Desktop\Projects\Personal\CEREBRUM
python launcher.py
```

### "Dependency installation failed"
```bash
# Install manually
pip install -r requirements.txt

# Or install specific package
pip install fastapi uvicorn requests pydantic
```

---

## Stop Training

Press `Ctrl+C` in the terminal running `start_training.py`

Or use the orchestrator:
```bash
python conversation_orchestrator.py --stop
```

---

## View Progress

While training is running:
```bash
python conversation_orchestrator.py --status
```

View conversation log:
```bash
python conversation_orchestrator.py --log
```

---

**No manual setup required - just run `python start_training.py` and go!** 🎉
