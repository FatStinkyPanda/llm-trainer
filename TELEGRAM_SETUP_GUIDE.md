# Telegram Bot Integration - Setup Guide

## 🎉 100% FREE! No Costs, No Limits!

Unlike SMS (which requires Twilio and costs money), Telegram Bot API is completely free with unlimited messages!

---

## Table of Contents
1. [Why Telegram?](#why-telegram)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Using the Bot](#using-the-bot)
5. [Architecture](#architecture)
6. [Troubleshooting](#troubleshooting)
7. [Production Deployment](#production-deployment)

---

## Why Telegram?

### Advantages ✅
- **100% FREE** - No costs ever
- **Unlimited messages** - No message limits
- **No phone verification** - Users just need Telegram app
- **Rich features** - Markdown, buttons, inline keyboards
- **Easy setup** - Get token in 2 minutes
- **Reliable** - Telegram's robust infrastructure

### Limitations ⚠️
- Users must have Telegram app (not standard SMS)
- Requires internet connection
- Not everyone has Telegram (though 800M+ users do)

**Best For:** Projects where you want free, unlimited AI chatting without SMS costs!

---

## Quick Start (5 Minutes!)

### Step 1: Create Bot (2 minutes)

1. Open Telegram app
2. Search for **@BotFather**
3. Send `/newbot`
4. Follow prompts:
   - Choose a name (e.g., "My AI Assistant")
   - Choose a username (must end in "bot", e.g., "myai_assistant_bot")
5. Copy the **bot token** (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Configure (1 minute)

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your bot token:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### Step 3: Install Dependencies (1 minute)

```bash
pip install -r requirements.txt
```

### Step 4: Run (1 minute)

**Terminal 1:** LLM Server
```bash
python llm_server.py
```

**Terminal 2:** Telegram Bot
```bash
python telegram_server.py
```

### Step 5: Test!

1. Open Telegram
2. Search for your bot (e.g., @myai_assistant_bot)
3. Send `/start`
4. Start chatting!

**That's it! No ngrok, no webhooks, no configuration needed!**

---

## Detailed Setup

### Creating Your Bot

1. **Open Telegram** on phone or desktop
2. **Find BotFather**:
   - Search: `@BotFather`
   - Or visit: https://t.me/botfather
3. **Create bot**:
   ```
   You: /newbot
   BotFather: Alright, a new bot. How are we going to call it?
   You: My AI Assistant
   BotFather: Good. Now let's choose a username for your bot...
   You: myai_assistant_bot
   BotFather: Done! Your bot is ready...
   ```
4. **Save the token** - You'll see something like:
   ```
   Use this token to access the HTTP API:
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

### Optional: Customize Your Bot

Send these commands to @BotFather:

**Set description** (shown in chat):
```
/setdescription
Select your bot
Type: I'm an AI assistant powered by advanced language models. Ask me anything!
```

**Set about text** (shown in profile):
```
/setabouttext
Select your bot
Type: AI chatbot with conversation memory and context awareness.
```

**Set profile picture**:
```
/setuserpic
Select your bot
Upload an image
```

**Set commands menu**:
```
/setcommands
Select your bot
Paste this:
start - Start conversation with AI
help - Show help and available commands
setname - Set or change your name
clear - Clear conversation history
```

---

## Using the Bot

### User Experience

#### First Time

```
You: /start
Bot: 👋 Welcome! To get started, please tell me your name:
     /setname <your name>

You: /setname Alice
Bot: ✅ Thanks, Alice! Your name has been saved.
     You can now chat with the AI...
```

**Note:** If your Telegram profile has a first name, the bot will automatically use it!

#### Regular Conversation

```
You: What is quantum computing?
Bot: Quantum computing is a type of computation that harnesses...

You: Can you explain more?
Bot: [Continues with context from previous message]
```

### Available Commands

- `/start` - Start conversation (auto-registers with your Telegram name)
- `/help` - Show help message
- `/setname <name>` - Set or change your display name
- `/clear` - Clear conversation history (fresh start)

### Special Features

✅ **Auto-registration** - Uses your Telegram first name automatically
✅ **Conversation memory** - Remembers last 5 exchanges
✅ **Markdown support** - Rich text formatting in responses
✅ **Long messages** - Handles messages up to 4000 characters
✅ **Context awareness** - Maintains conversation flow

---

## Architecture

### Polling vs Webhook Mode

The bot supports two modes:

#### Polling Mode (Default) ⭐ RECOMMENDED

- Bot checks for new messages every few seconds
- **No server configuration needed**
- **No public URL needed**
- **No ngrok needed**
- Works out of the box on localhost
- Perfect for development and small deployments

```python
python telegram_server.py  # Automatically uses polling
```

#### Webhook Mode (Advanced)

- Telegram sends messages to your server
- Requires public HTTPS URL
- More efficient for high traffic
- Needs configuration

```python
# In telegram_server.py, change:
run_server(use_polling=False)

# Then set webhook:
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://yourserver.com/telegram/webhook"
```

### System Flow

```
User sends message in Telegram
    ↓
Telegram servers
    ↓
Polling: Bot fetches update (or)
Webhook: Telegram POSTs to your server
    ↓
telegram_server.py processes message
    ↓
Check if command (/start, /help, etc)
    YES → Execute command
    NO → Check if user registered
        NOT REGISTERED → Auto-register with Telegram name or ask
        REGISTERED → Forward to AI
    ↓
Call LLM Server API (/api/chat)
    ↓
Get AI response
    ↓
Save to database (conversation history)
    ↓
Send response back via Telegram API
    ↓
User receives message
```

### Database Schema

Uses the unified `messaging_database.py`:

**Users Table:**
```sql
user_id         TEXT    -- Telegram chat ID
platform        TEXT    -- 'telegram'
name            TEXT    -- User's display name
username        TEXT    -- Telegram @username
created_at      TEXT
updated_at      TEXT
```

**Conversations Table:**
```sql
user_id         TEXT    -- Links to user
platform        TEXT    -- 'telegram'
role            TEXT    -- 'user' or 'assistant'
message         TEXT    -- Message content
timestamp       TEXT
```

---

## API Endpoints

The server exposes these endpoints:

### User Endpoints

- `GET /` - Health check
- `POST /telegram/webhook` - Webhook for receiving messages
- `GET /telegram/status` - View all users and statistics

### Admin Endpoints

- `POST /telegram/send` - Manually send message
  ```json
  {
    "chat_id": "123456789",
    "message": "Hello!"
  }
  ```

- `POST /telegram/polling/start` - Start polling mode
- `POST /telegram/polling/stop` - Stop polling mode

### Example: Check Status

```bash
curl http://localhost:8041/telegram/status
```

Response:
```json
{
  "bot_status": "connected",
  "bot_info": {
    "id": 1234567890,
    "username": "myai_assistant_bot",
    "first_name": "My AI Assistant"
  },
  "polling_active": true,
  "total_users": 5,
  "users": [
    {
      "chat_id": "123456789",
      "name": "Alice",
      "username": "alice_telegram",
      "registered": "2025-11-10T10:30:00"
    }
  ]
}
```

---

## Running the System

### Development (Local)

**Terminal 1:** LLM Server
```bash
python llm_server.py
```

**Terminal 2:** Telegram Bot
```bash
python telegram_server.py
```

**That's it!** No ngrok, no webhooks, no extra setup!

### Production

For production deployment:

1. **Deploy to a server** (AWS, DigitalOcean, Heroku, etc.)
2. **Keep using polling mode** OR switch to webhook with HTTPS
3. **Set up process manager** (systemd, pm2, supervisor)
4. **Enable logging**
5. **Backup database** regularly

---

## Troubleshooting

### Bot Not Responding

**Check 1:** Is the token correct?
```bash
# Test manually:
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

**Check 2:** Is the server running?
```bash
curl http://localhost:8041/
```

**Check 3:** Is polling active?
```bash
curl http://localhost:8041/telegram/status
```

**Check 4:** Check logs in terminal

### "Bot token not configured"

**Solution:** Make sure `.env` file exists with:
```env
TELEGRAM_BOT_TOKEN=your_actual_token_here
```

Or add to `config.json`:
```json
{
  "telegram_bot_token": "your_actual_token_here"
}
```

### "Cannot connect to LLM Server"

**Solution:**
1. Make sure `llm_server.py` is running
2. Check it's on port 8033: `curl http://localhost:8033/`
3. Check config.json has correct port

### Bot responds but AI doesn't reply

**Solution:**
1. Check LLM server logs for errors
2. Test LLM server directly:
   ```bash
   curl -X POST http://localhost:8033/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message":"test","conversation_history":[]}'
   ```
3. Check if Ollama/OpenRouter is configured correctly

### Polling not working

**Solution:**
1. Check if webhook is set (it shouldn't be):
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
   ```
2. Delete webhook if set:
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/deleteWebhook
   ```
3. Restart telegram_server.py

---

## Comparison: SMS vs Telegram

| Feature | SMS (Twilio) | Telegram |
|---------|-------------|----------|
| **Cost** | ~$2-3/month + per message | **FREE** |
| **Message Limit** | Pay per message | **Unlimited** |
| **Setup Complexity** | Medium (needs ngrok for local) | **Easy** |
| **User Requirements** | Just phone number | Telegram app |
| **Rich Features** | Plain text only | Markdown, buttons, media |
| **Delivery** | Standard SMS | Internet-based |
| **Best For** | Reach anyone via SMS | Free, feature-rich chatbot |

**Recommendation:**
- Use **Telegram** for most use cases (free, powerful, easy)
- Use **SMS** only if you specifically need SMS access

---

## Advanced Configuration

### Change Response Length

Edit `telegram_server.py`:

```python
payload = {
    "message": user_message,
    "conversation_history": conversation_history,
    "temperature": 0.8,
    "max_tokens": 500  # Change this (100-2000)
}
```

### Change Conversation History Length

Edit `telegram_server.py`:

```python
conversation_history = db.get_conversation_history_formatted(
    chat_id,
    'telegram',
    limit=5  # Change this (1-20)
)
```

### Add Custom Commands

Edit `handle_command()` in `telegram_server.py`:

```python
elif command_lower == '/mycommand':
    telegram_service.send_message(chat_id, "Custom response!")
```

### Enable Markdown Formatting

By default, AI responses are sent as plain text. To enable Markdown:

```python
# In telegram_server.py, find:
telegram_service.send_message(chat_id, ai_response, parse_mode=None)

# Change to:
telegram_service.send_message(chat_id, ai_response, parse_mode="Markdown")
```

---

## Production Best Practices

### 1. Use Environment Variables

Never hardcode tokens in code:

```bash
export TELEGRAM_BOT_TOKEN="your_token"
python telegram_server.py
```

### 2. Set Up Logging

Create log file:

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler()
    ]
)
```

### 3. Process Manager

Use systemd on Linux:

```ini
# /etc/systemd/system/telegram-bot.service
[Unit]
Description=Telegram AI Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/llm-trainer
Environment="TELEGRAM_BOT_TOKEN=your_token"
ExecStart=/usr/bin/python3 telegram_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

### 4. Database Backups

```bash
# Backup script
#!/bin/bash
cp messaging_users.db backups/messaging_users_$(date +%Y%m%d_%H%M%S).db
```

### 5. Monitor Bot

Check status regularly:

```bash
curl http://localhost:8041/telegram/status
```

---

## Security Considerations

✅ **Token security** - Keep bot token secret, use environment variables
✅ **Input validation** - Already implemented for commands
✅ **Rate limiting** - Consider adding for production
✅ **Database encryption** - Consider for sensitive data
✅ **User blocking** - Add allowlist/blocklist if needed

---

## Cost Comparison

### Telegram Bot
- Setup: **FREE**
- Operation: **FREE**
- Messages: **UNLIMITED FREE**
- Total: **$0/month** 🎉

### SMS (Twilio)
- Phone number: $1.15/month
- 100 conversations: ~$2.73/month
- 1000 conversations: ~$16.95/month

**Savings with Telegram: 100%** 💰

---

## Support Resources

- [Telegram Bot API Docs](https://core.telegram.org/bots/api)
- [BotFather Commands](https://core.telegram.org/bots#6-botfather)
- [Telegram Bot Features](https://core.telegram.org/bots/features)

---

## Next Steps

1. ✅ Create your bot with @BotFather
2. ✅ Add token to `.env`
3. ✅ Start the servers
4. ✅ Test with `/start` command
5. 🚀 Share your bot with friends!
6. 📈 Monitor usage at `/telegram/status`
7. 🎨 Customize responses and commands
8. 🌐 Deploy to production when ready

---

## FAQ

**Q: Is it really free?**
A: Yes! Telegram Bot API is 100% free with no limits.

**Q: Can I use both SMS and Telegram?**
A: Yes! Run both servers simultaneously on different ports.

**Q: How many users can it handle?**
A: Unlimited! Each user gets their own conversation history.

**Q: Can I add buttons and rich UI?**
A: Yes! Telegram supports inline keyboards, buttons, and more. See Bot API docs.

**Q: Do I need a server?**
A: For local testing, no. For production, yes (any server works).

**Q: Can users send images/files?**
A: The current implementation handles text only, but you can extend it to handle media.

**Q: How do I shut down the bot?**
A: Press Ctrl+C in the terminal, or kill the process.

---

*Setup time: 5 minutes | Cost: $0 | Messages: Unlimited*

**Ready to start?** Follow the [Quick Start](#quick-start) guide above! 🚀
