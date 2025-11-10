# Telegram Bot - 5 Minute Quick Start

## 🎉 100% FREE - No costs ever!

---

## Step 1: Create Bot (2 minutes)

1. Open **Telegram** app
2. Search for **@BotFather**
3. Send: `/newbot`
4. Choose name: "My AI Assistant"
5. Choose username: "myai_assistant_bot"
6. **Copy the token** (looks like: `1234567890:ABC...`)

---

## Step 2: Configure (1 minute)

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

---

## Step 3: Install (1 minute)

```bash
pip install -r requirements.txt
```

---

## Step 4: Run (1 minute)

**Terminal 1:** LLM Server
```bash
python llm_server.py
```

**Terminal 2:** Telegram Bot
```bash
python telegram_server.py
```

---

## Step 5: Test!

1. Open **Telegram**
2. Search for your bot: `@myai_assistant_bot`
3. Send: `/start`
4. **Start chatting!**

---

## Example Conversation

```
You: /start
Bot: 👋 Welcome! [auto-registers with your Telegram name]

You: What is artificial intelligence?
Bot: [AI explains AI]

You: Tell me more
Bot: [Continues with context]
```

---

## Commands

- `/start` - Start chatting
- `/help` - Show help
- `/setname <name>` - Change your name
- `/clear` - Clear history

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot not responding | Check token in `.env` |
| "Cannot connect to LLM Server" | Run `llm_server.py` first |
| Token error | Get new token from @BotFather |

---

## What Makes This Different?

✅ **100% FREE** - No SMS costs!
✅ **No ngrok** - No public URL needed!
✅ **Auto-registration** - Uses Telegram names
✅ **Rich formatting** - Markdown support
✅ **Unlimited messages** - No limits ever
✅ **Easy setup** - 5 minutes total

---

## Verification Checklist

- ✅ LLM Server running (port 8033)
- ✅ Telegram Bot running (port 8041)
- ✅ Token in `.env` file
- ✅ Can find bot in Telegram
- ✅ `/start` command works

---

## Next Steps

- Read [TELEGRAM_SETUP_GUIDE.md](TELEGRAM_SETUP_GUIDE.md) for details
- Customize commands and responses
- Deploy to production
- Invite friends to use your bot!

---

## Cost: $0/month 🎉

Unlike SMS (Twilio), Telegram Bot API is:
- **FREE** to create
- **FREE** to run
- **FREE** messages (unlimited!)

**Total savings: 100%**

---

**Ready?** Start at Step 1! 🚀
