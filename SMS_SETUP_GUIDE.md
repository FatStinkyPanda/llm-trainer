# SMS Integration Setup Guide

This guide will help you set up SMS messaging integration with your LLM server using Twilio.

## Table of Contents
1. [Twilio Account Setup](#twilio-account-setup)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Local Testing with ngrok](#local-testing-with-ngrok)
5. [Running the SMS Server](#running-the-sms-server)
6. [Usage](#usage)
7. [Troubleshooting](#troubleshooting)

---

## Twilio Account Setup

### Step 1: Create Twilio Account

1. Go to [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Sign up for a free trial account
3. Verify your email and phone number

**Free Trial Limitations:**
- $15.50 in free credit
- Can send SMS to verified phone numbers only
- Need to upgrade ($20 minimum) for full production use

### Step 2: Get Your Twilio Credentials

1. Log into [Twilio Console](https://console.twilio.com/)
2. Find your **Account SID** and **Auth Token** on the dashboard
3. Keep these safe - you'll need them for configuration

### Step 3: Get a Phone Number

1. In Twilio Console, go to **Phone Numbers** → **Manage** → **Buy a number**
2. Select your country and search for available numbers
3. Purchase a number (free trial includes one number)
4. Note down your phone number in E.164 format (e.g., +12345678900)

---

## Installation

### Step 1: Install Dependencies

```bash
# From the llm-trainer directory
pip install -r requirements.txt
```

This installs:
- `twilio` - Twilio Python SDK
- `python-multipart` - For processing Twilio webhook form data

### Step 2: Create Environment File

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your Twilio credentials:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+12345678900
```

**Security Note:** Never commit your `.env` file to git! It should already be in `.gitignore`.

---

## Configuration

### Option 1: Environment Variables (Recommended)

Use the `.env` file as shown above. This keeps sensitive credentials out of your code.

### Option 2: Config File

Alternatively, edit `config.json`:

```json
{
  "sms_server_port": 8040,
  "twilio_account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "twilio_auth_token": "your_auth_token_here",
  "twilio_phone_number": "+12345678900"
}
```

**Note:** Environment variables take precedence over config file values.

---

## Local Testing with ngrok

Twilio needs a public URL to send webhooks to your local server. Use **ngrok** for this:

### Step 1: Install ngrok

Download from [https://ngrok.com/download](https://ngrok.com/download) or:

```bash
# Windows (with Chocolatey)
choco install ngrok

# Mac
brew install ngrok

# Linux
snap install ngrok
```

### Step 2: Start Your SMS Server

```bash
python sms_server.py
```

The server will start on `http://localhost:8040`

### Step 3: Create ngrok Tunnel

In a new terminal:

```bash
ngrok http 8040
```

You'll see output like:

```
Forwarding   https://abc123.ngrok.io -> http://localhost:8040
```

Copy the `https://` URL (e.g., `https://abc123.ngrok.io`)

### Step 4: Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com/) → **Phone Numbers** → **Manage** → **Active numbers**
2. Click on your phone number
3. Scroll to **Messaging Configuration**
4. Under "A MESSAGE COMES IN":
   - Set **Webhook** URL to: `https://abc123.ngrok.io/sms/webhook`
   - Set method to **HTTP POST**
5. Click **Save**

**Important:** Every time you restart ngrok, you get a new URL and must update Twilio!

---

## Running the SMS Server

### Start All Services

You need to run both the LLM server and SMS server:

**Terminal 1: LLM Server**
```bash
python llm_server.py
```

**Terminal 2: SMS Server**
```bash
python sms_server.py
```

**Terminal 3: ngrok (for local testing)**
```bash
ngrok http 8040
```

### Check Status

Visit these URLs to verify everything is running:

- LLM Server: [http://localhost:8033](http://localhost:8033)
- SMS Server: [http://localhost:8040](http://localhost:8040)
- SMS Status: [http://localhost:8040/sms/status](http://localhost:8040/sms/status)
- API Docs: [http://localhost:8040/docs](http://localhost:8040/docs)

---

## Usage

### For End Users (Texters)

#### First Time Setup

1. Text anything to your Twilio phone number
2. Bot will ask for your name
3. Reply with: `name=John` (replace John with your name)
4. Bot confirms registration

#### Chatting with AI

Just send any message to the phone number:

```
You: What is the meaning of life?
AI: [Response from your configured AI model]
```

#### Changing Your Name

Send a text with just:
```
name=NewName
```

Bot will confirm the name change.

### For Administrators

#### View Registered Users

GET request to:
```
http://localhost:8040/sms/status
```

Returns list of all registered users and statistics.

#### Manually Send SMS

POST request to:
```
http://localhost:8040/sms/send
```

Body:
```json
{
  "phone_number": "+12345678900",
  "message": "Hello from the server!"
}
```

#### Clear User's Conversation History

DELETE request to:
```
http://localhost:8040/sms/user/+12345678900/history
```

---

## Architecture

```
┌─────────────────────┐
│  Texter's Phone     │
└──────────┬──────────┘
           │ SMS
           ↓
┌─────────────────────┐
│  Twilio (Cloud)     │
└──────────┬──────────┘
           │ Webhook (HTTPS)
           ↓
┌─────────────────────┐
│  ngrok (Tunnel)     │ ← Only for local testing
└──────────┬──────────┘
           │ HTTP
           ↓
┌─────────────────────────────┐
│  SMS Server (Port 8040)     │
│  - Receive webhook          │
│  - Parse name commands      │
│  - Manage user database     │
│  - Route to AI              │
│  - Send responses           │
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│  User Database (SQLite)     │
│  - Phone numbers & names    │
│  - Conversation history     │
└─────────────────────────────┘
           │
           ↓
┌─────────────────────────────┐
│  LLM Server (Port 8033)     │
│  /api/chat endpoint         │
│  - Ollama or OpenRouter     │
└─────────────────────────────┘
```

---

## Database Schema

The SMS integration creates a SQLite database (`sms_users.db`) with two tables:

### Users Table
```sql
CREATE TABLE users (
    phone_number TEXT PRIMARY KEY,
    name TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

### Conversations Table
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL,
    role TEXT NOT NULL,           -- 'user' or 'assistant'
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (phone_number) REFERENCES users (phone_number)
)
```

---

## Troubleshooting

### Problem: "SMS service not initialized"

**Solution:** Check your Twilio credentials in `.env` or `config.json`

### Problem: "Twilio authentication failed"

**Solutions:**
1. Verify your Account SID and Auth Token are correct
2. Check for extra spaces or quotes in credentials
3. Make sure your trial account is active

### Problem: Not receiving webhooks

**Solutions:**
1. Check ngrok is running and URL is current
2. Verify webhook URL in Twilio console is correct
3. Check SMS server logs for errors
4. Test webhook manually with curl:
   ```bash
   curl -X POST http://localhost:8040/sms/webhook \
     -d "From=+12345678900" \
     -d "Body=test message"
   ```

### Problem: "Cannot connect to LLM Server"

**Solutions:**
1. Make sure `llm_server.py` is running on port 8033
2. Check LLM server logs for errors
3. Verify port in `config.json` matches

### Problem: SMS sent but no response

**Solutions:**
1. Check SMS server logs - look for errors
2. Verify LLM server is responding (test `/api/chat` directly)
3. Check if user is registered (visit `/sms/status`)
4. Check Twilio debugger: [https://console.twilio.com/monitor/debugger](https://console.twilio.com/monitor/debugger)

### Problem: Trial account can't send to phone numbers

**Solution:**
1. In trial mode, verify recipient phone numbers in Twilio console first
2. Go to Phone Numbers → Verified Caller IDs → Add new number
3. Or upgrade account to remove restrictions

---

## Cost Breakdown

### Twilio Pricing (US)

| Item | Cost |
|------|------|
| Phone number | $1.15/month |
| Inbound SMS | $0.0079 per message |
| Outbound SMS | $0.0079 per message |

**Example Usage:**
- 100 conversations/month (200 messages total): $1.15 + ($0.0079 × 200) = **$2.73/month**
- 1000 conversations/month (2000 messages total): $1.15 + ($0.0079 × 2000) = **$16.95/month**

### OpenRouter/Ollama (AI costs)

- **Ollama (local)**: Free! Uses your computer's resources
- **OpenRouter**: Varies by model, typically $0.001-$0.01 per message

---

## Production Deployment

For production use (without ngrok):

1. **Deploy to a server** with a public IP or domain
2. **Use a reverse proxy** (nginx, Apache) with HTTPS
3. **Configure Twilio webhook** to your production URL
4. **Set up process manager** (systemd, pm2, supervisor) to keep server running
5. **Enable logging** and monitoring
6. **Backup database** regularly (`sms_users.db`)

---

## Security Best Practices

1. ✅ **Never commit credentials** - Use `.env` file (already in `.gitignore`)
2. ✅ **Use HTTPS** in production (Twilio requires it)
3. ✅ **Validate webhook signatures** (optional but recommended)
4. ✅ **Rate limiting** - Prevent abuse (consider adding)
5. ✅ **Input validation** - Already implemented for name commands

---

## Support

### Helpful Resources

- [Twilio SMS Quickstart](https://www.twilio.com/docs/sms/quickstart/python)
- [Twilio Webhook Guide](https://www.twilio.com/docs/usage/webhooks)
- [ngrok Documentation](https://ngrok.com/docs)

### Logs

Check logs for debugging:
- SMS Server: Console output or `logs/sms_server.log` (if configured)
- LLM Server: Console output
- Twilio: [https://console.twilio.com/monitor/logs/sms](https://console.twilio.com/monitor/logs/sms)

---

## Alternative: Free Telegram Bot

If you want a completely **free** alternative (not SMS but similar):

1. Use Telegram Bot API instead of Twilio
2. Users need Telegram app (not standard SMS)
3. Completely free with no limits
4. Similar functionality

Let me know if you'd like me to create a Telegram bot version instead!
