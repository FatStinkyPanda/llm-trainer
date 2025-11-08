# 🏗️ LLM Trainer Architecture

## Design Principles

### ✅ **Complete Isolation**
- **NO** imports from CEREBRUM code
- **NO** shared files or data structures
- **NO** direct function calls
- **ONLY** HTTP/REST communication

### ✅ **Deletability**
- Entire `llm-trainer/` folder can be deleted
- CEREBRUM continues functioning normally
- Zero dependencies from CEREBRUM → LLM Trainer

### ✅ **Sandboxing**
- Each service runs in separate process
- LLM never executes in CEREBRUM's process space
- Clear architectural boundaries

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐                                             │
│  │    Ollama     │  (Port 11434)                               │
│  │  gemma2:2b    │  - Local LLM engine                         │
│  └───────┬───────┘  - No knowledge of CEREBRUM                 │
│          │                                                      │
└──────────┼──────────────────────────────────────────────────────┘
           │
           │ HTTP
           │
┌──────────┴──────────────────────────────────────────────────────┐
│                      llm-trainer/ FOLDER                        │
│                    (Completely Isolated)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────┐         ┌──────────────────────┐        │
│  │   LLM Server      │         │    Middleware        │        │
│  │  (Port 8030-8035) │ ←─────→ │   (Port 8032)        │        │
│  │                   │  HTTP   │                      │        │
│  │ - Wraps Ollama    │         │ - Bridges services   │        │
│  │ - Simple chat API │         │ - No shared code     │        │
│  │ - No CEREBRUM ref │         │ - Pure HTTP proxy    │        │
│  └───────────────────┘         └───────────┬──────────┘        │
│                                            │                    │
│                                            │ HTTP               │
└────────────────────────────────────────────┼────────────────────┘
                                             │
                                             │
                                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                        CEREBRUM SYSTEM                          │
│                         (Port 8000)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  - No knowledge of LLM Trainer                                  │
│  - Only exposes /api/chat endpoint                              │
│  - Learns from conversations via observation                    │
│  - observed_expressions fills up naturally                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. **LLM Server** (`llm_server.py`)
**Port**: Auto-selected from 8030-8035 range

**Responsibilities**:
- Serve Ollama gemma2:2b model via REST API
- Provide simple `/api/chat` endpoint
- Manage conversation history
- **NO knowledge of CEREBRUM**

**API Endpoints**:
- `GET /` - Health check
- `POST /api/chat` - Chat with LLM
- `GET /api/status` - Server status
- `POST /api/reset` - Reset conversation

**Isolation**:
- ✅ Zero imports from CEREBRUM
- ✅ Separate process
- ✅ Only knows about Ollama

---

### 2. **Middleware** (`middleware.py`)
**Port**: 8032

**Responsibilities**:
- Bridge between CEREBRUM and LLM Server
- Orchestrate conversation flow
- Track training progress
- Save conversation logs

**API Endpoints**:
- `GET /api/status` - Middleware status
- `GET /api/cerebrum/status` - Proxy to CEREBRUM
- `GET /api/llm/status` - Proxy to LLM
- `POST /api/training/start` - Start training loop
- `POST /api/training/stop` - Stop training
- `GET /api/training/status` - Get training status
- `GET /api/training/log` - Get conversation log

**Isolation**:
- ✅ Zero imports from CEREBRUM
- ✅ Only HTTP communication
- ✅ Can be stopped independently

**Training Loop**:
1. LLM generates message
2. Middleware sends to CEREBRUM `/api/chat`
3. CEREBRUM responds
4. Middleware sends response to LLM
5. Repeat with configured delay

---

### 3. **Conversation Orchestrator** (`conversation_orchestrator.py`)

**Purpose**: CLI tool for training control

**Commands**:
```bash
# Start training
python conversation_orchestrator.py --start --exchanges 100

# Stop training
python conversation_orchestrator.py --stop

# Show status
python conversation_orchestrator.py --status

# Show conversation log
python conversation_orchestrator.py --log --log-limit 20
```

**Isolation**:
- ✅ Zero imports from CEREBRUM
- ✅ Only talks to Middleware API

---

### 4. **Quick Start** (`start_training.py`)

**Purpose**: One-command startup

**What it does**:
1. Checks CEREBRUM is running
2. Starts LLM Server
3. Starts Middleware
4. Initiates training
5. Monitors progress
6. Stops all services on Ctrl+C

**Usage**:
```bash
python start_training.py
```

---

## Port Usage

| Service | Port(s) | Auto-Select | Description |
|---------|---------|-------------|-------------|
| CEREBRUM | 8000 | No | Main system (pre-existing) |
| LLM Server | 8030-8035 | **Yes** | Auto-finds free port in range |
| Middleware | 8032 | No | Bridge service |
| Ollama | 11434 | No | Default Ollama port |

**Port Selection Logic**:
```python
# llm_server.py finds free port on startup
free_port = find_free_port(8030, 8035)
# Saves selected port to config.json
# Middleware reads updated config
```

---

## Data Flow: Training Session

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User starts training:                                        │
│    python start_training.py                                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Middleware POST /api/training/start                          │
│    - Validates CEREBRUM accessible                              │
│    - Validates LLM Server accessible                            │
│    - Starts background training thread                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Training Loop (in middleware background thread):             │
│                                                                 │
│    a. LLM generates message                                     │
│       POST localhost:8031/api/chat                              │
│       ← "What are your thoughts on consciousness?"              │
│                                                                 │
│    b. Send to CEREBRUM                                          │
│       POST localhost:8000/api/chat                              │
│       → "What are your thoughts on consciousness?"              │
│       ← CEREBRUM responds (currently single word)               │
│                                                                 │
│    c. CEREBRUM observes LLM's language                          │
│       - Processes through cognitive_language_generator.py       │
│       - Calls observe_language_use()                            │
│       - Adds to observed_expressions in                         │
│         learned_language_generation.py                          │
│                                                                 │
│    d. Send CEREBRUM's response to LLM                           │
│       POST localhost:8031/api/chat                              │
│       → CEREBRUM's response                                     │
│       ← LLM continues conversation                              │
│                                                                 │
│    e. Log exchange                                              │
│       - Save to conversation_log                                │
│       - Update exchange counter                                 │
│                                                                 │
│    f. Wait configured delay (2s default)                        │
│                                                                 │
│    g. Check if topic switch needed                              │
│       - Every 10 messages: new topic                            │
│                                                                 │
│    h. Repeat until max_exchanges reached                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Training completes:                                          │
│    - Save conversation log to training_logs/session_*.json      │
│    - Stop background thread                                     │
│    - CEREBRUM now has observed_expressions database filled      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security & Safety

### Process Isolation
- Each service runs in separate Python process
- LLM never executes code in CEREBRUM's process space
- No shared memory or global state

### No Code Injection
- LLM only generates text responses
- Text sent to CEREBRUM via HTTP POST
- CEREBRUM treats it as user input (same as web chat)
- No eval(), exec(), or dynamic code execution

### No File System Access
- LLM Trainer can't read CEREBRUM's source code
- LLM Trainer can't modify CEREBRUM's files
- Only writes to `llm-trainer/training_logs/`

### Removability
- Delete `llm-trainer/` folder completely
- CEREBRUM has zero dependencies on it
- No orphaned imports or references

---

## Configuration

All settings in `config.json`:

```json
{
  "cerebrum_url": "http://localhost:8000",
  "llm_server_port_range": [8030, 8035],
  "middleware_port": 8032,
  "ollama_url": "http://localhost:11434",
  "ollama_model": "gemma2:2b",
  "conversation_delay": 2.0,
  "topic_switch_interval": 10,
  "max_conversation_history": 10,
  "conversation_topics": [...]
}
```

**Dynamic Updates**:
- LLM Server writes selected port to config on startup
- Middleware reads updated config to find LLM Server
- No hardcoded ports (except Ollama default)

---

## Expected Learning Progression

### Phase 1: 0-50 Exchanges
- **CEREBRUM**: Single-word responses
- **Reason**: Empty `observed_expressions` database
- **Learning**: Building observation database from LLM's messages

### Phase 2: 50-100 Exchanges
- **CEREBRUM**: Starting to use learned phrases
- **Reason**: Enough observations for basic synthesis
- **Learning**: Combining observed patterns

### Phase 3: 100-500 Exchanges
- **CEREBRUM**: Multi-word coherent responses
- **Reason**: Rich pattern database
- **Learning**: Natural language formation

### Phase 4: 500+ Exchanges
- **CEREBRUM**: Fluent conversation with unique voice
- **Reason**: Mature learned language system
- **Learning**: Autonomous expression development

---

## Monitoring & Debugging

### Check System Status
```bash
# All service statuses
python conversation_orchestrator.py --status
```

### View Conversation Log
```bash
# Last 20 exchanges
python conversation_orchestrator.py --log

# Last 50 exchanges
python conversation_orchestrator.py --log --log-limit 50
```

### Check Individual Services
```bash
# CEREBRUM
curl http://localhost:8000/api/status

# LLM Server (port auto-selected 8030-8035)
curl http://localhost:8030/api/status  # (check actual port from logs)

# Middleware
curl http://localhost:8032/api/status
```

### Logs
Each service logs to stdout:
- **LLM Server**: `[LLM-SERVER]` prefix
- **Middleware**: `[MIDDLEWARE]` prefix
- **CEREBRUM**: Standard CEREBRUM logging

---

## Troubleshooting

### "Cannot connect to CEREBRUM"
1. Ensure CEREBRUM is running: `python launcher.py`
2. Check it's on port 8000: `curl http://localhost:8000/api/status`

### "Cannot connect to Ollama"
1. Start Ollama: `ollama serve`
2. Pull model: `ollama pull gemma2:2b`
3. Check: `curl http://localhost:11434/api/tags`

### "No free port in range 8030-8035"
1. Some other process is using all ports
2. Check: `netstat -ano | findstr "8030"`
3. Change `llm_server_port_range` in config.json

### "Training not making progress"
1. Check middleware logs for errors
2. Verify delay isn't too short (< 1s)
3. Check CEREBRUM logs for processing errors

---

## Complete Removal

To remove LLM Trainer entirely:

```bash
# From CEREBRUM project root
rm -rf llm-trainer/

# Or on Windows:
rmdir /s /q llm-trainer
```

**Result**: CEREBRUM works exactly as before. Zero impact.

---

## Future Enhancements

Potential improvements (without breaking isolation):

1. **Web Dashboard**: Real-time training visualization
2. **Multiple LLMs**: Compare different models
3. **Custom Topics**: User-defined conversation topics
4. **Export Training**: Share learned conversation datasets
5. **Metrics**: Track language learning progress quantitatively

All enhancements maintain:
- ✅ Zero CEREBRUM imports
- ✅ HTTP-only communication
- ✅ Complete deletability
