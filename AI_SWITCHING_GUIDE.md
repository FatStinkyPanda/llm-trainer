# AI Switching Feature - Telegram Bot

## Overview

The Telegram bot now supports switching between **two AI backends**:

1. **OpenRouter AI** (default) - Cloud-based advanced AI with extensive knowledge
2. **CEREBRUM AI** - Your novel local AGI system running via middleware

Users can seamlessly switch between these AIs mid-conversation using simple commands.

---

## How It Works

### Architecture

```
Telegram User
     ↓
Telegram Bot (telegram_server.py)
     ↓
  [checks user's ai_backend preference in database]
     ↓
     ├─→ OpenRouter? → LLM Server (port 8030) → OpenRouter API
     │
     └─→ CEREBRUM? → Middleware (port 8032) → CEREBRUM (port 8000)
```

### User Preference Storage

Each user's AI backend preference is stored in the database:

```sql
users table:
- user_id: Telegram chat ID
- platform: 'telegram'
- name: User's name
- ai_backend: 'openrouter' or 'cerebrum' (default: 'openrouter')
- created_at, updated_at
```

---

## Commands

### `/status`
Shows which AI the user is currently chatting with.

**Example:**
```
You: /status
Bot: 🤖 Current AI Backend

     You're chatting with: OpenRouter AI

     Available AIs:
     • /openrouter - Cloud-based advanced AI
     • /cerebrum - Local novel AGI system
```

### `/openrouter`
Switches to OpenRouter AI (cloud-based).

**Example:**
```
You: /openrouter
Bot: ✅ Switched to OpenRouter AI

     You're now chatting with OpenRouter's AI models (cloud-based, advanced).

     Use /cerebrum to switch to the local CEREBRUM AI.
```

### `/cerebrum`
Switches to CEREBRUM AI (local AGI).

**Example:**
```
You: /cerebrum
Bot: ✅ Switched to CEREBRUM AI

     You're now chatting with CEREBRUM, a novel AGI system running locally.
     CEREBRUM is currently learning language and may give shorter responses.

     Use /openrouter to switch back to OpenRouter AI.
```

---

## Setup Requirements

### For OpenRouter (Default)

1. **LLM Server must be running:**
   ```bash
   python llm_server.py
   ```

2. **OpenRouter API key configured** in `.env` or `config.json`

### For CEREBRUM

1. **CEREBRUM must be running:**
   - Your CEREBRUM AGI system on port 8000

2. **Middleware must be running:**
   ```bash
   python middleware.py
   ```

3. **LLM Server must be running** (middleware uses it):
   ```bash
   python llm_server.py
   ```

---

## Quick Start

### Option 1: Start Everything with Launcher

```bash
# Start all services (LLM, Middleware, Telegram)
python start_all_servers.py --llm --telegram

# In separate terminal, start middleware
python middleware.py
```

### Option 2: Manual Start

```bash
# Terminal 1: LLM Server
python llm_server.py

# Terminal 2: Middleware (for CEREBRUM access)
python middleware.py

# Terminal 3: Telegram Bot
python telegram_server.py
```

### Option 3: OpenRouter Only

If you only want OpenRouter (no CEREBRUM):

```bash
# Terminal 1: LLM Server
python llm_server.py

# Terminal 2: Telegram Bot
python telegram_server.py
```

Users can still use the bot, but `/cerebrum` command will fail if middleware isn't running.

---

## User Experience

### Conversation Flow

```
User: /start
Bot: 👋 Welcome, Daniel! [auto-registered with OpenRouter AI]

User: What is machine learning?
Bot: [OpenRouter explains ML in detail]

User: /cerebrum
Bot: ✅ Switched to CEREBRUM AI

User: What is machine learning?
Bot: [CEREBRUM's response - may be shorter, learning-oriented]

User: /status
Bot: 🤖 Current AI Backend
     You're chatting with: CEREBRUM AI

User: /openrouter
Bot: ✅ Switched to OpenRouter AI

User: Explain quantum computing
Bot: [OpenRouter provides detailed explanation]
```

---

## Technical Details

### Middleware Chat Endpoint

New endpoint added to `middleware.py`:

```python
POST /api/chat
{
  "message": "User's message",
  "user_id": "telegram_bot"
}

Response:
{
  "response": "CEREBRUM's response",
  "emotions": {...},  # Optional
  "timestamp": "2025-11-10T12:00:00"
}
```

### Database Schema Update

Added `ai_backend` column to users table:

```sql
ALTER TABLE users ADD COLUMN ai_backend TEXT DEFAULT 'openrouter';
```

### Telegram Server Routing Logic

```python
# Get user's preference
user = db.get_user(chat_id, 'telegram')
ai_backend = user.get('ai_backend', 'openrouter')

# Route to appropriate backend
if ai_backend == 'cerebrum':
    response = get_cerebrum_response(message, history)
else:
    response = get_openrouter_response(message, history)
```

---

## Error Handling

### CEREBRUM Not Available

If user switches to CEREBRUM but middleware/CEREBRUM isn't running:

```
User: /cerebrum
Bot: ✅ Switched to CEREBRUM AI...

User: Hello
Bot: ❌ Sorry, I encountered an error processing your message.
```

**Solution:** Start middleware and CEREBRUM, then try again.

### OpenRouter Not Available

If OpenRouter API key is invalid or LLM server is down:

```
User: Hello
Bot: ❌ Sorry, I encountered an error processing your message.
```

**Solution:** Check LLM server logs and verify API key.

---

## Conversation History

- **Separate histories** - Each user has one conversation history regardless of AI backend
- **Context preserved** - When switching AIs, conversation history is maintained
- **History includes all messages** - Both OpenRouter and CEREBRUM responses are in the same history

**Note:** CEREBRUM currently doesn't use conversation history (by design), but OpenRouter does.

---

## SMS Support

Currently, AI switching is **Telegram-only**. SMS users always use OpenRouter.

**Future enhancement:** Add SMS commands like "switch to cerebrum" via text parsing.

---

## Monitoring

### Check Current Users and Their AI Preferences

```bash
curl http://localhost:8041/telegram/status
```

Response includes:
```json
{
  "users": [
    {
      "chat_id": "123456789",
      "name": "Alice",
      "ai_backend": "cerebrum"
    },
    {
      "chat_id": "987654321",
      "name": "Bob",
      "ai_backend": "openrouter"
    }
  ]
}
```

### Check Middleware Status

```bash
curl http://localhost:8032/api/status
```

### Check CEREBRUM Connection

```bash
curl http://localhost:8000/api/status
```

---

## Best Practices

1. **Start CEREBRUM first** if you want users to access it
2. **Start middleware** after CEREBRUM
3. **Start LLM server** before middleware
4. **Start Telegram bot** last

**Recommended startup order:**
1. CEREBRUM (your AGI)
2. LLM Server
3. Middleware
4. Telegram Bot

---

## Troubleshooting

### "Cannot connect to middleware"

**Check:**
1. Is middleware running? `curl http://localhost:8032/api/status`
2. Is middleware port correct in config.json? (should be 8032)
3. Check middleware logs for errors

### "CEREBRUM is not accessible"

**Check:**
1. Is CEREBRUM running? `curl http://localhost:8000/api/status`
2. Is CEREBRUM URL correct in config.json? (should be http://localhost:8000)
3. Check CEREBRUM logs

### Users can't switch

**Check:**
1. Database has `ai_backend` column (should auto-create on first run)
2. User is registered (`/start` command)
3. Check telegram_server logs for errors

---

## Future Enhancements

Possible additions:

- **SMS support** for AI switching
- **Auto-fallback** - If CEREBRUM fails, automatically use OpenRouter
- **Usage statistics** - Track which AI is used more
- **Model selection** - Let users choose specific OpenRouter models
- **Personality modes** - Different "personalities" for CEREBRUM
- **Conversation branching** - Separate histories per AI backend

---

## Summary

✅ Users can switch between OpenRouter and CEREBRUM mid-conversation
✅ Preference saved per user in database
✅ Seamless switching with `/openrouter` and `/cerebrum` commands
✅ `/status` command shows current AI
✅ Conversation history preserved across switches
✅ Easy to extend with more AI backends

**User Experience:** Simple, intuitive, no technical knowledge required!
