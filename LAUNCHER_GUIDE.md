# LLM Trainer - Complete System Launcher

## Quick Start

**One command to rule them all:**

```bash
python start_llm_trainer.py
```

That's it! The launcher handles everything automatically.

---

## What It Does

The launcher automatically:

1. ✅ **Checks dependencies** - Verifies all required packages
2. ✅ **Checks configuration** - Validates .env and config.json
3. ✅ **Kills existing processes** - Finds and stops old llm-trainer processes
4. ✅ **Frees up ports** - Ensures ports 8030-8041 are available
5. ✅ **Starts services in order** - LLM Server → Middleware → Telegram/SMS
6. ✅ **Health checks** - Verifies each service started correctly
7. ✅ **Monitors services** - Watches for crashes and restarts if needed
8. ✅ **Clean shutdown** - Stops all services gracefully on Ctrl+C

---

## Services Started

### Always Started (Required)

1. **LLM Server** (port 8030-8035)
   - AI backend (OpenRouter/Ollama)
   - Required for all AI interactions

2. **Middleware Service** (port 8032)
   - Bridge to CEREBRUM
   - Required for CEREBRUM AI access

### Conditionally Started (If Configured)

3. **Telegram Bot** (port 8041)
   - Started if `TELEGRAM_BOT_TOKEN` is configured
   - Skipped if not configured

4. **SMS Server** (port 8040)
   - Started if Twilio credentials configured
   - Skipped if not configured

---

## Output Example

```
======================================================================
LLM Trainer - Complete System Launcher
======================================================================

----------------------------------------------------------------------
Checking Dependencies
----------------------------------------------------------------------
  [OK] fastapi
  [OK] uvicorn
  [OK] requests
  [OK] pydantic
  [OK] python-dotenv
  [OK] psutil
  [OK] twilio
  [OK] python-telegram-bot

----------------------------------------------------------------------
Checking Configuration
----------------------------------------------------------------------
  [OK] .env file found
  [OK] Telegram bot configured
  [!] SMS server not configured (will skip)
  [OK] OpenRouter API key configured

----------------------------------------------------------------------
Cleaning Up Existing Processes
----------------------------------------------------------------------
  --> Found LLM Server on port 8030
  [OK] Stopped python.exe (PID 12345)
  --> Found Telegram Bot on port 8041
  [OK] Stopped python.exe (PID 12346)
  [OK] Cleanup complete

----------------------------------------------------------------------
Starting Services
----------------------------------------------------------------------
  --> Starting LLM Server (port 8030)...
  [OK] LLM Server started successfully (PID 15000)
  --> Starting Middleware Service (port 8032)...
  [OK] Middleware Service started successfully (PID 15001)
  --> Starting Telegram Bot (port 8041)...
  [OK] Telegram Bot started successfully (PID 15002)
  [!] Skipping SMS Server (not configured)

----------------------------------------------------------------------
Service Status
----------------------------------------------------------------------
  [OK] LLM Server          - Running (PID 15000, Port 8030)
  [OK] Middleware Service  - Running (PID 15001, Port 8032)
  [OK] Telegram Bot        - Running (PID 15002, Port 8041)
  [!]  SMS Server          - Not started

----------------------------------------------------------------------
Service URLs
----------------------------------------------------------------------
  LLM Server:        http://localhost:8030
    API Docs:        http://localhost:8030/docs
  Middleware:        http://localhost:8032
    Status:          http://localhost:8032/api/status
    API Docs:        http://localhost:8032/docs
  Telegram Bot:      http://localhost:8041
    Status:          http://localhost:8041/telegram/status

======================================================================
All services started successfully!
======================================================================

Press Ctrl+C to stop all services
```

---

## Stopping Services

**Just press `Ctrl+C` in the terminal:**

```
^C
Shutdown requested...

----------------------------------------------------------------------
Stopping Services
----------------------------------------------------------------------
  --> Stopping LLM Server...
  [OK] LLM Server stopped
  --> Stopping Middleware Service...
  [OK] Middleware Service stopped
  --> Stopping Telegram Bot...
  [OK] Telegram Bot stopped

[OK] All services stopped
```

---

## Troubleshooting

### "Port X is still in use!"

The launcher tries to kill existing processes, but if it can't:

**Manual cleanup:**
```bash
# Windows
netstat -ano | findstr :8030
taskkill /PID <PID> /F

# Or just reboot
```

### "Missing required dependencies"

```bash
pip install -r requirements.txt
```

### "Service failed to start"

Check individual service logs:
- Look at the terminal output for error messages
- Check if CEREBRUM is running (for middleware)
- Verify API keys in .env

### "Required service failed - exiting"

If a required service (LLM Server or Middleware) fails:
1. Check the error message
2. Fix the issue
3. Run the launcher again

---

## Advanced Usage

### Run Specific Services Only

The launcher always starts required services (LLM Server, Middleware) but you can control optional ones by configuration:

**Disable Telegram:**
```bash
# Remove or comment out TELEGRAM_BOT_TOKEN in .env
# Or remove from config.json
```

**Disable SMS:**
```bash
# Remove Twilio credentials from .env
```

### Check What's Running

While launcher is running, open new terminal:

```bash
# Check LLM Server
curl http://localhost:8030/

# Check Middleware
curl http://localhost:8032/api/status

# Check Telegram Bot
curl http://localhost:8041/telegram/status
```

---

## Process Management

### How It Finds Existing Processes

The launcher:
1. Checks each service port (8030, 8032, 8040, 8041)
2. Finds processes listening on those ports
3. Checks if they're llm-trainer processes (by command line)
4. Kills them gracefully (SIGTERM) → forcefully (SIGKILL) if needed

### Startup Order

Services start in this order for dependencies:

```
1. LLM Server      (independent)
2. Middleware      (depends on LLM Server)
3. Telegram Bot    (depends on LLM Server)
4. SMS Server      (depends on LLM Server)
```

Each service waits a few seconds before the next starts.

### Health Checks

After starting, the launcher checks:
- HTTP service responds on expected port
- Process is still running
- Service-specific endpoints return 200 OK

---

## Comparison with Old Method

### Old Way ❌

```bash
# Terminal 1
python llm_server.py

# Terminal 2
python middleware.py

# Terminal 3
python telegram_server.py

# Terminal 4
python sms_server.py

# To stop: Ctrl+C in each terminal
# If terminals crash: processes keep running
# Ports stay occupied
# Manual cleanup needed
```

### New Way ✅

```bash
# Single terminal
python start_llm_trainer.py

# To stop: Ctrl+C once
# Automatic cleanup
# All processes stopped cleanly
```

---

## Integration with start_all_servers.py

The **new launcher** (`start_llm_trainer.py`) is more comprehensive than `start_all_servers.py`:

| Feature | start_all_servers.py | start_llm_trainer.py |
|---------|---------------------|---------------------|
| Kill existing processes | ❌ | ✅ |
| Port checking | ❌ | ✅ |
| Dependency checking | ❌ | ✅ |
| Health checks | ❌ | ✅ |
| Crash monitoring | ❌ | ✅ |
| Auto-cleanup | ❌ | ✅ |
| Process management | Manual | Automatic |

**Recommendation:** Use `start_llm_trainer.py` for daily use.

---

## Examples

### Fresh Start (Nothing Running)

```bash
python start_llm_trainer.py
```

Output: Starts everything cleanly.

### Restart (Services Already Running)

```bash
python start_llm_trainer.py
```

Output:
```
Found LLM Server on port 8030
[OK] Stopped python.exe (PID 12345)
Found Middleware Service on port 8032
[OK] Stopped python.exe (PID 12346)
...
[Starts all services fresh]
```

### Partial Start (Telegram Not Configured)

```bash
python start_llm_trainer.py
```

Output:
```
[!] Telegram bot not configured (will skip)
...
[!] Skipping Telegram Bot (not configured)
```

Only starts LLM Server and Middleware.

---

## Requirements

Ensure `psutil` is installed (for process management):

```bash
pip install -r requirements.txt
```

This adds `psutil>=5.9.0` to requirements.

---

## Exit Codes

- `0` - Normal exit (Ctrl+C or all services stopped)
- `1` - Fatal error (missing dependencies, required service failed)

---

## Tips

1. **Always use the launcher** - Don't start services manually anymore
2. **Keep one terminal** - All services in one window
3. **Check URLs** - Launcher shows all service URLs on startup
4. **Watch for errors** - Red `[X]` marks indicate problems
5. **Clean shutdown** - Always Ctrl+C, don't force-close terminal

---

## Future Enhancements

Possible additions:
- Web dashboard for service status
- Auto-restart crashed services
- Log aggregation from all services
- Service dependency detection
- Configuration validation
- Health check dashboard

---

## Summary

✅ **One command** to start everything
✅ **Automatic cleanup** of old processes
✅ **Smart port management**
✅ **Health monitoring**
✅ **Clean shutdown** with Ctrl+C
✅ **No manual process management**

**Just run:** `python start_llm_trainer.py` and you're good to go! 🚀
