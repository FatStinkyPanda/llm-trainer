# 🤖 LLM Trainer for CEREBRUM

**IMPORTANT**: This is a **completely isolated** system that can be safely deleted without affecting CEREBRUM.

## 🏗️ Architecture

This system uses **3 separate services** to maintain strict separation:

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   CEREBRUM      │         │   Middleware     │         │   LLM Server    │
│   Port: 8000    │ ←────── │   Port: 8002     │ ──────→ │   Port: 8001    │
│                 │  HTTP   │                  │  HTTP   │                 │
│  (No LLM code)  │         │  (Bridge only)   │         │  (Ollama)       │
└─────────────────┘         └──────────────────┘         └─────────────────┘
         ↑                           ↑
         │                           │
         └───────────────────────────┘
              No direct connection
```

### Services:

1. **CEREBRUM** (Port 8000)
   - Runs independently
   - No knowledge of LLM
   - Only exposes REST API

2. **LLM Server** (Port 8001)
   - Serves Ollama gemma3:1b model
   - Simple chat completions API
   - No knowledge of CEREBRUM

3. **Middleware** (Port 8002)
   - Bridges CEREBRUM ↔ LLM
   - Orchestrates conversation flow
   - Can be stopped/removed anytime

## 🚀 Quick Start

### Prerequisites
- Ollama installed with gemma3:1b model downloaded
- CEREBRUM running on port 8000
- Python 3.10+

### Install Dependencies
```bash
cd llm-trainer
pip install -r requirements.txt
```

### Start Services (in separate terminals)

**Terminal 1 - LLM Server**:
```bash
cd llm-trainer
python llm_server.py
```

**Terminal 2 - Middleware**:
```bash
cd llm-trainer
python middleware.py
```

**Terminal 3 - Start Training**:
```bash
cd llm-trainer
python conversation_orchestrator.py --exchanges 100
```

### OR Use the Launcher Script
```bash
cd llm-trainer
python start_training.py
```

## 🎮 Control Interface

### Start Conversation Training
```bash
curl -X POST http://localhost:8002/api/training/start \
  -H "Content-Type: application/json" \
  -d '{"max_exchanges": 100, "delay": 2.0}'
```

### Stop Training
```bash
curl -X POST http://localhost:8002/api/training/stop
```

### Get Training Status
```bash
curl http://localhost:8002/api/training/status
```

### Get Conversation Log
```bash
curl http://localhost:8002/api/training/log
```

## 🗑️ Complete Removal

To completely remove LLM trainer from CEREBRUM:

```bash
# From CEREBRUM project root
rm -rf llm-trainer/
```

CEREBRUM will continue functioning normally - it has **zero dependencies** on this folder.

## 🔒 Isolation Guarantees

✅ **No shared code** - LLM trainer doesn't import any CEREBRUM modules
✅ **No file access** - LLM trainer doesn't read/write CEREBRUM files
✅ **Pure HTTP** - All communication via REST APIs
✅ **Separate processes** - Can be stopped independently
✅ **Deletable** - Entire folder can be removed safely

## 📊 Ports Used

- **8000**: CEREBRUM (main system)
- **8001**: LLM Server (Ollama gemma3:1b)
- **8002**: Middleware (bridge)
- **11434**: Ollama (default, used by LLM Server)

## 📝 Configuration

Edit `config.json` to change settings:
```json
{
  "cerebrum_url": "http://localhost:8000",
  "llm_server_port": 8001,
  "middleware_port": 8002,
  "ollama_url": "http://localhost:11434",
  "ollama_model": "gemma2:2b",
  "conversation_delay": 2.0,
  "topic_switch_interval": 10
}
```

## 🧪 Testing

### Test LLM Server
```bash
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

### Test Middleware → CEREBRUM
```bash
curl http://localhost:8002/api/cerebrum/status
```

### Test Middleware → LLM
```bash
curl -X POST http://localhost:8002/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Test"}'
```

## 📖 How It Works

1. **Middleware** polls training status
2. When training active, it:
   - Fetches message from LLM server
   - Sends to CEREBRUM via `/api/chat`
   - Gets CEREBRUM's response
   - Sends back to LLM server
   - Repeats with configured delay
3. CEREBRUM learns language patterns naturally
4. All services remain independent

## 🛡️ Safety Features

- **No code injection**: LLM never executes in CEREBRUM's process
- **No file system access**: LLM can't read CEREBRUM's code
- **Sandboxed**: Each service runs independently
- **Removable**: Delete folder → LLM completely gone
- **Monitorable**: All traffic visible via middleware logs

## 📈 Expected Results

After running training:
- **0-50 exchanges**: CEREBRUM builds observation database
- **50-100 exchanges**: Starts synthesizing from patterns
- **100-500 exchanges**: Increasingly natural responses
- **500+ exchanges**: Fluent conversation

Training logs saved to: `training_logs/session_YYYYMMDD_HHMMSS.json`
