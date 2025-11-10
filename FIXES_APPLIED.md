# LLM Server Startup Issues - Fixes Applied

## Issues Identified and Fixed

### 1. **IPv4/IPv6 Mismatch** (CRITICAL)
- **Problem**: `localhost` resolves to IPv6 (`::1`) on your system, but uvicorn binds to IPv4 only (`0.0.0.0`)
- **Fix**: Changed all URLs from `localhost` to `127.0.0.1` in start_training.py
- **Files**: start_training.py (lines 188, 208, 224, 243)

### 2. **Python Output Buffering**
- **Problem**: Print statements in llm_server.py were fully buffered when run as subprocess
- **Fix**: Added `flush=True` to all print statements in llm_server.py
- **Files**: llm_server.py (lines 264-286)

### 3. **Port Race Condition**
- **Problem**: Config.json retained old port values from previous runs, causing mismatches
- **Fix**: Clear `llm_server_port` from config before starting the server
- **Files**: start_training.py (lines 136-141)

### 4. **Startup Timing**
- **Problem**: Start_training.py tried to connect before uvicorn fully initialized
- **Fix**: Increased initialization delay from 3 to 6 seconds
- **Files**: start_training.py (line 184)

### 5. **Process Detachment**
- **Problem**: Subprocess stdout/stderr handling caused various issues
- **Fix**: Used Windows-specific process flags (CREATE_NO_WINDOW | DETACHED_PROCESS)
- **Files**: start_training.py (lines 58-70)

## Remaining Issue

Despite all fixes, there's a **ReadTimeout** issue when start_training.py tries to connect to the LLM Server as a subprocess. The server starts successfully and uvicorn runs, but HTTP requests timeout while reading the response.

**Evidence**:
- Server logs show successful "200 OK" responses
- Direct execution of llm_server.py works perfectly
- The issue only occurs when run as subprocess from start_training.py

## Workaround

### Manual Start Method (Recommended for Now)

1. **Start LLM Server separately**:
   ```bash
   python llm_server.py
   ```
   This will start on port 8030 or next available port

2. **Comment out LLM Server startup in start_training.py**:
   Edit start_training.py and comment lines 143-192 (the entire LLM Server startup section)

3. **Update config.json** with the port shown by llm_server.py

4. **Run start_training.py** - it will connect to the already-running server

### Alternative: Increase Timeout

Try increasing the requests timeout from 2 to 10 seconds in wait_for_service (line 84):
```python
response = requests.get(url, timeout=10)
```

## Next Steps for Full Fix

The ReadTimeout issue likely stems from a Windows-specific subprocess/networking interaction. Possible solutions to investigate:

1. Use a different HTTP client library (httpx, urllib3 directly)
2. Add explicit TCP keep-alive settings
3. Run servers as Windows services instead of subprocesses
4. Use multiprocessing instead of subprocess

## Files Modified

- `start_training.py` - Multiple fixes for IPv6, timing, subprocess handling
- `llm_server.py` - Output buffering fixes
