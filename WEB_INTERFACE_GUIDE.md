# LLM Trainer Web Interface Guide

## 🎉 Complete Control Panel

The LLM Trainer now has a **comprehensive web-based control panel** with support for all system features!

## 🚀 Quick Start

1. **Start the middleware:**
   ```bash
   python middleware.py
   ```

2. **Open the web interface:**
   - Navigate to: http://localhost:8032
   - You'll see the complete LLM Trainer Control Panel with 4 tabs

3. **Navigate the interface:**
   - **Overview** - System status and quick stats
   - **Training** - LLM configuration and training control
   - **Messaging** - SMS and Telegram configuration
   - **Users** - View all registered users

---

## 📑 Interface Tabs

### Overview Tab

**System Status Dashboard** - Real-time monitoring of all services:

- **LLM Server** (Port 8030) - AI backend server status
- **Middleware** (Port 8032) - API gateway status
- **Telegram Bot** (Port 8041) - Telegram service status
- **SMS Server** (Port 8040) - SMS/Twilio service status
- **CEREBRUM** (Port 8000) - Your AGI system status

**Quick Statistics:**
- Training status and progress
- User counts (Telegram, SMS, Total)
- Current training metrics

### Training Tab

**LLM Configuration:**
- **LLM Source** - Switch between Ollama (local) and OpenRouter (cloud)
- **Ollama Model** - Configure local model (e.g., `qwen3:8b`)
- **OpenRouter Model** - Configure cloud model (e.g., `anthropic/claude-3.5-sonnet`)
- **OpenRouter API Key** - Secure API key storage

**Training Control:**
- **Max Exchanges** - Number of conversation turns
- **Delay** - Seconds between messages (rate limiting)
- **Topic Switch Interval** - Messages before changing topic
- **Start/Stop Training** - Real-time training control

**Training Status Display:**
- Current LLM source and model
- Exchanges completed counter
- Current conversation topic
- Running/Stopped status

### Messaging Tab

**Telegram Configuration:**
- **Bot Token** - Telegram bot token from @BotFather
- Configuration status indicator
- Instant save and restart notification

**SMS Configuration (Twilio):**
- **Account SID** - Twilio account identifier
- **Auth Token** - Twilio authentication token
- **Phone Number** - Your Twilio phone number (E.164 format)
- Configuration status indicator
- Instant save and restart notification

**AI Backend Configuration:**
- **Default AI Backend** - Choose OpenRouter or CEREBRUM for new users
- Users can switch backends using `/openrouter` or `/cerebrum` commands

### Users Tab

**User Management Dashboard:**
- View all registered users from both Telegram and SMS
- Columns: Platform, User ID, Name, AI Backend, Registration Date
- Real-time refresh button
- Color-coded AI backend indicators

---

## 🎛️ Configuration Features

### LLM Sources

#### Ollama (Local)

**Advantages:**
- ✅ Free
- ✅ Fast (runs locally)
- ✅ No API costs
- ✅ Privacy (all data stays local)

**Setup:**
1. Select "Ollama (Local)" as LLM Source
2. Enter your model name (e.g., `qwen3:8b`)
3. Click "Save LLM Configuration"

**Requirements:**
- Ollama must be running: `ollama serve`
- Model must be downloaded: `ollama pull qwen3:8b`

#### OpenRouter (API)

**Advantages:**
- ✅ Access to most powerful models
- ✅ No local GPU required
- ✅ Easy model switching
- ✅ Automatic scaling

**Setup:**
1. Get API key from [openrouter.ai/keys](https://openrouter.ai/keys)
2. Select "OpenRouter (API)" as LLM Source
3. Enter your API key
4. Choose a model (e.g., `anthropic/claude-3.5-sonnet`)
5. Click "Save LLM Configuration"

**Popular Models:**
- `anthropic/claude-3.5-sonnet` - Excellent for teaching
- `openai/gpt-4-turbo` - Very capable
- `meta-llama/llama-3.1-70b-instruct` - Open source, powerful
- `google/gemini-pro-1.5` - Fast and capable

**Cost:** $0.001-0.015 per 1000 tokens

---

## 💬 Messaging Configuration

### Telegram Bot Setup

1. **Create Bot:**
   - Open Telegram and message [@BotFather](https://t.me/BotFather)
   - Send `/newbot` command
   - Follow prompts to create your bot
   - Copy the bot token

2. **Configure in Web Interface:**
   - Go to "Messaging" tab
   - Paste bot token in "Bot Token" field
   - Click "Save Telegram Configuration"
   - Restart `telegram_server.py` or use system launcher

3. **Verify:**
   - Check "Overview" tab for Telegram Bot status
   - Should show "Running" in green

### SMS (Twilio) Setup

1. **Get Twilio Credentials:**
   - Sign up at [twilio.com](https://www.twilio.com)
   - Get Account SID from console
   - Get Auth Token from console
   - Purchase a phone number

2. **Configure in Web Interface:**
   - Go to "Messaging" tab
   - Enter Account SID
   - Enter Auth Token
   - Enter Phone Number (format: `+15555551234`)
   - Click "Save SMS Configuration"
   - Restart `sms_server.py` or use system launcher

3. **Configure Webhook:**
   - In Twilio console, set webhook URL to: `http://your-server:8040/sms/webhook`

4. **Verify:**
   - Check "Overview" tab for SMS Server status
   - Should show "Running" in green

### AI Backend Selection

**Default AI Backend:**
- Choose which AI new users start with (OpenRouter or CEREBRUM)
- Users can switch anytime using commands:
  - `/openrouter` - Switch to cloud AI
  - `/cerebrum` - Switch to local AGI
  - `/status` - Check current AI

**User Preferences:**
- Each user's AI selection is saved in database
- Preference persists across sessions
- View user preferences in "Users" tab

---

## 📊 Monitoring Features

### Real-Time Status Updates

The interface automatically updates every 3 seconds:

- Service availability (all 5 services)
- Training status and progress
- User counts
- Current training metrics

### Service Status Indicators

**Colors:**
- 🟢 **Green (Running)** - Service is operational
- 🔴 **Red (Stopped)** - Service is not running
- 🟡 **Yellow (Warning)** - Service error or partial failure

**What to Check if Service Shows Stopped:**
1. Check if service is started manually or via launcher
2. Verify configuration (API keys, tokens, credentials)
3. Check logs for errors
4. Ensure required ports are available

### User Statistics

**Telegram Users:**
- Count of registered Telegram users
- Fetched from Telegram Bot server

**SMS Users:**
- Count of registered SMS users
- Fetched from SMS server

**Total Users:**
- Combined count across both platforms

---

## 🔄 Workflow Examples

### Example 1: Configure Everything from Scratch

1. **Start Services:**
   ```bash
   python start_llm_trainer.py
   ```

2. **Open Web Interface:**
   - Navigate to http://localhost:8032

3. **Configure LLM (Training Tab):**
   - Select OpenRouter
   - Enter API key from openrouter.ai
   - Choose model: `anthropic/claude-3.5-sonnet`
   - Save configuration

4. **Configure Telegram (Messaging Tab):**
   - Enter bot token from @BotFather
   - Save configuration
   - Restart services

5. **Configure SMS (Messaging Tab):**
   - Enter Twilio credentials
   - Save configuration
   - Restart services

6. **Verify (Overview Tab):**
   - Check all services show "Running"
   - Ready to use!

### Example 2: Start Training Session

1. **Go to Training Tab**
2. **Set Parameters:**
   - Max Exchanges: 100
   - Delay: 2 seconds
   - Topic Interval: 10
3. **Click "Start Training"**
4. **Monitor Progress:**
   - Watch exchanges completed counter
   - See current topic in real-time
   - Training status shows "Running"
5. **Stop When Done:**
   - Click "Stop Training"
   - Or let it complete automatically

### Example 3: Monitor Users

1. **Go to Users Tab**
2. **Click "Refresh"**
3. **View User Details:**
   - See all Telegram and SMS users
   - Check which AI backend each user prefers
   - View registration dates
4. **User Switches AI:**
   - User sends `/cerebrum` command
   - Refresh users tab
   - See updated AI backend preference

---

## 💡 Tips and Best Practices

### For Best Training Results:

**Using Ollama:**
- Use `qwen3:8b` or larger for best teaching quality
- Ensure Ollama is running before starting training
- Check model is downloaded: `ollama list`
- Set delay to 0.5-1 second (fast local response)

**Using OpenRouter:**
- Use Claude 3.5 Sonnet for excellent teaching
- Set delay to 1-2 seconds to avoid rate limits
- Monitor costs at [openrouter.ai](https://openrouter.ai)
- Consider using cheaper models for testing

### Configuration Management:

**Save Frequently:**
- Configuration is saved to `config.json`
- Changes persist across restarts
- Always save before restarting services

**Restart Services After Config Changes:**
- LLM configuration: Restart training if active
- Telegram/SMS configuration: Restart respective servers
- Or use unified launcher to restart everything: `python start_llm_trainer.py`

### Monitoring Best Practices:

**Check Overview Tab Regularly:**
- Ensure all required services are running
- Monitor user growth
- Track training progress

**User Management:**
- Refresh users tab to see latest registrations
- Monitor AI backend preferences
- Identify inactive users

---

## 🐛 Troubleshooting

### Service Shows "Stopped"

**LLM Server:**
- Check: `python llm_server.py` runs without errors
- Verify: OpenRouter API key is valid (if using OpenRouter)
- Verify: Ollama is running (if using Ollama)

**Middleware:**
- Should always be running (serves web interface)
- Check port 8032 is not in use
- Check logs: `middleware.log`

**Telegram Bot:**
- Verify bot token is configured
- Check token is valid (test with @BotFather)
- Restart: `python telegram_server.py`

**SMS Server:**
- Verify Twilio credentials are configured
- Check credentials are valid
- Restart: `python sms_server.py`

**CEREBRUM:**
- Ensure your AGI system is running on port 8000
- Check CEREBRUM is accessible: `curl http://localhost:8000/api/status`

### Configuration Not Saving

**Issue:** Changes don't persist

**Solutions:**
1. Check file permissions on `config.json`
2. Ensure middleware has write access to project directory
3. Check middleware logs for permission errors
4. Try running with elevated permissions (if needed)

### Training Won't Start

**Common Causes:**
1. **CEREBRUM not running** - Start CEREBRUM first
2. **LLM Server not accessible** - Check LLM Server status
3. **Invalid configuration** - Verify API keys and model names
4. **Already running** - Stop existing training first

**Solutions:**
1. Check Overview tab - ensure LLM Server is running
2. Verify LLM configuration is saved
3. Check middleware logs for specific errors
4. Try stopping and starting again

### Users Not Loading

**Issue:** Users tab shows "No users registered yet" but users exist

**Solutions:**
1. Ensure Telegram/SMS servers are running
2. Click "Refresh" button
3. Check service status endpoints:
   - Telegram: `http://localhost:8041/telegram/status`
   - SMS: `http://localhost:8040/sms/status`
4. Restart messaging servers if needed

### Web Interface Not Loading

**Issue:** Cannot access http://localhost:8032

**Solutions:**
1. Ensure middleware is running: `python middleware.py`
2. Check port 8032 is not in use by another service
3. Try accessing: `http://127.0.0.1:8032`
4. Check firewall settings
5. Check middleware logs for startup errors

---

## 📁 Files

- `web_interface.html` - Control panel UI (HTML/CSS)
- `control-panel.js` - Interface JavaScript
- `config.json` - Configuration storage (automatically updated)
- `middleware.py` - API server (port 8032)

---

## 🔐 Security Notes

- **API Keys:** Stored in `config.json` - keep this file secure
- **Local Only:** Web interface runs locally (not exposed to internet)
- **Production:** Use environment variables for sensitive data in production
- **Passwords:** Input fields for tokens/keys use password type (hidden)
- **File Permissions:** Ensure `config.json` has appropriate permissions

---

## 🆕 What's New

**Latest Updates:**

✅ **Service Status Monitoring** - Real-time status for all 5 services
✅ **Telegram Configuration** - Configure bot token via web interface
✅ **SMS Configuration** - Configure Twilio credentials via web interface
✅ **AI Backend Selection** - Choose default AI for new users
✅ **User Management** - View all registered users and their AI preferences
✅ **Multi-Tab Interface** - Organized into Overview, Training, Messaging, and Users tabs
✅ **Enhanced Configuration** - All system settings in one place
✅ **Auto-Refresh Status** - Updates every 3 seconds automatically

---

## 🎓 Next Steps

1. **Configure Your Services:**
   - Set up LLM (Ollama or OpenRouter)
   - Configure Telegram bot (optional)
   - Configure SMS/Twilio (optional)

2. **Test the System:**
   - Start training session
   - Message your Telegram bot
   - Send SMS to your Twilio number

3. **Monitor Everything:**
   - Watch Overview tab for service health
   - Track users as they register
   - Monitor training progress

4. **Optimize Settings:**
   - Adjust training parameters based on results
   - Try different LLM models
   - Configure AI backend preferences

Enjoy the enhanced LLM Trainer Control Panel! 🚀
