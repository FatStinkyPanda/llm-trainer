# LLM Trainer - Service Status Guide

## Quick Start

**To restart all services properly:**
1. Close the current terminal running the services (or run `restart_services.bat`)
2. Run: `python start_llm_trainer.py`
3. Open your browser to: `http://localhost:8032`

---

## Service Overview

### ✅ Currently Working Services

#### 1. **LLM Server** (Port 8030) - ✓ CONFIGURED & RUNNING
- **Status**: Fully functional
- **Purpose**: Connects to OpenRouter or Ollama for AI responses
- **Configuration**: OpenRouter API key is configured
- **Model**: Using `openrouter/polaris-alpha`
- **No action needed** - This service is ready to use

#### 2. **Middleware** (Port 8032) - ✓ RUNNING (but had timeout issues)
- **Status**: Running (serves the web interface)
- **Purpose**: Central hub that coordinates all services
- **Issue Found**: Was hanging due to connection timeouts
- **Fix Applied**: Reduced timeouts from 3s to 1s for faster failure detection
- **Action**: Restart services to apply the fix

#### 3. **Telegram Bot** (Port 8041) - ⚠️ NOT CONFIGURED
- **Status**: Service exists but no bot token configured
- **Purpose**: Allows users to chat with your AI via Telegram
- **What's Missing**: `TELEGRAM_BOT_TOKEN` in config.json
- **How to Configure**:
  1. Create a bot with [@BotFather](https://t.me/botfather) on Telegram
  2. Get your bot token (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
  3. Add it to `config.json`: `"telegram_bot_token": "YOUR_TOKEN_HERE"`
  4. Restart services
  5. Chat with your bot on Telegram!

---

### ❌ Services Not in This Project

#### 4. **CEREBRUM** (Port 8000) - ❌ DOES NOT EXIST
- **Status**: Referenced in config but no server exists
- **Issue**: Middleware was trying to connect to CEREBRUM and timing out
- **Fix Applied**: Made CEREBRUM truly optional with fast failure
- **Action**:
  - If you have CEREBRUM, start it separately on port 8000
  - If not, ignore this - the system works fine without it
  - The "NOT CONFIGURED" status in the web interface is NORMAL

---

### ⚠️ Optional Services (Not Configured)

#### 5. **SMS Server** (Port 8040) - ⚠️ NOT CONFIGURED
- **Status**: Service exists but no Twilio credentials
- **Purpose**: Allows users to chat with your AI via SMS
- **What's Missing**: Twilio credentials in config.json
- **How to Configure**:
  1. Sign up for [Twilio](https://www.twilio.com/)
  2. Get your Account SID, Auth Token, and Phone Number
  3. Add to `config.json`:
     ```json
     "twilio_account_sid": "YOUR_SID",
     "twilio_auth_token": "YOUR_TOKEN",
     "twilio_phone_number": "+1234567890"
     ```
  4. Restart services
  5. Text your Twilio number to chat!

---

## Root Cause Analysis

### Why Services Showed as "STOPPED"

The middleware was **hanging** due to:
1. **Blocking on CEREBRUM**: Trying to connect to CEREBRUM (which doesn't exist) with 3-second timeouts
2. **Connection Leaks**: Too many CLOSE_WAIT connections building up
3. **Slow Health Checks**: 3-second timeouts made status checks stack up

### Fixes Applied

1. ✅ Reduced all timeouts from 3s → 1s for fast failure
2. ✅ Added explicit exception handling for Timeout and ConnectionError
3. ✅ Made all service checks truly optional (return 503 immediately if not available)
4. ✅ Better error messages to distinguish "not configured" from "crashed"

---

## What You Should See After Restart

### Web Interface (http://localhost:8032)

**System Status Panel:**
- **LLM Server**: ✅ **Running** (green)
- **Middleware**: ✅ **Running** (green)
- **Telegram Bot**: ⚠️ **Not Configured** (red) - NORMAL if you haven't added a token
- **SMS Server**: ⚠️ **Not Configured** (red) - NORMAL if you haven't added Twilio credentials
- **CEREBRUM**: ⚠️ **Not Configured** (red) - NORMAL (this service doesn't exist in your project)

---

## Training Configuration

### Current Settings
- **LLM Source**: OpenRouter
- **Model**: `openrouter/polaris-alpha`
- **API Key**: Configured ✅
- **Conversation Delay**: 2.0 seconds
- **Topic Switch Interval**: 10 messages

### What Works Now
1. ✅ **Web Interface** - Control panel accessible
2. ✅ **LLM Server** - AI responses working
3. ✅ **Training Mode** - Can start training sessions
4. ✅ **Configuration** - Can update settings via web UI

### What Needs Configuration
1. ⚠️ **Telegram Bot** - Add bot token to enable Telegram chat
2. ⚠️ **SMS Server** - Add Twilio credentials to enable SMS chat
3. ❌ **CEREBRUM** - Not needed (or start separately if you have it)

---

## Next Steps

1. **Immediate**: Run `restart_services.bat` or close terminal and run `python start_llm_trainer.py`
2. **Optional**: Configure Telegram bot if you want Telegram integration
3. **Optional**: Configure SMS server if you want SMS integration
4. **Test**: Open http://localhost:8032 and verify all services show correct status

---

## Troubleshooting

### If services still show as "STOPPED":
1. Check that ports aren't blocked by firewall
2. Look at terminal output for error messages
3. Check `middleware.log` for details
4. Run `netstat -ano | findstr "8030 8032"` to verify ports are listening

### If web interface won't load:
1. Verify middleware is running: `python -c "import requests; print(requests.get('http://localhost:8032/health', timeout=2).json())"`
2. Check browser console for errors (F12)
3. Try a different browser

### If LLM responses don't work:
1. Verify OpenRouter API key is valid
2. Check you have credits in your OpenRouter account
3. Look at `llm_server.log` for API errors

---

## Configuration File Reference

Your `config.json` currently has:

```json
{
  "llm_source": "openrouter",           // ✅ Configured
  "openrouter_model": "openrouter/polaris-alpha", // ✅ Configured
  "openrouter_api_key": "sk-or-v1-...",  // ✅ Configured
  "telegram_bot_token": "",              // ⚠️ Empty - configure for Telegram
  "twilio_account_sid": "",              // ⚠️ Empty - configure for SMS
  "twilio_auth_token": "",               // ⚠️ Empty - configure for SMS
  "twilio_phone_number": "",             // ⚠️ Empty - configure for SMS
  "cerebrum_url": "http://localhost:8000" // ❌ Service doesn't exist
}
```

---

## Summary

**What's Working**: LLM Server + Middleware + Web Interface
**What Needs Config**: Telegram Bot + SMS Server
**What Doesn't Exist**: CEREBRUM (ignore this)

**Current Status**: 2 out of 5 services fully functional ✅
**After Configuration**: Up to 4 out of 5 services available
