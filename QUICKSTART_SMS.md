# SMS Integration - Quick Start

Get your SMS chatbot running in 10 minutes!

## Prerequisites

- Python 3.8+ installed
- Twilio account (free trial works!)
- ngrok installed (for local testing)

---

## Step 1: Install Dependencies (2 minutes)

```bash
pip install -r requirements.txt
```

---

## Step 2: Get Twilio Credentials (3 minutes)

1. Sign up at [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Get a free phone number
3. Copy your **Account SID**, **Auth Token**, and **Phone Number**

---

## Step 3: Configure Credentials (1 minute)

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_PHONE_NUMBER=+12345678900
```

---

## Step 4: Start Servers (1 minute)

**Terminal 1:** Start LLM Server
```bash
python llm_server.py
```

**Terminal 2:** Start SMS Server
```bash
python sms_server.py
```

**Terminal 3:** Start ngrok tunnel
```bash
ngrok http 8040
```

Copy the ngrok HTTPS URL (e.g., `https://abc123.ngrok.io`)

---

## Step 5: Configure Twilio Webhook (2 minutes)

1. Go to [Twilio Console](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)
2. Click your phone number
3. Under "Messaging Configuration" → "A MESSAGE COMES IN":
   - Paste: `https://abc123.ngrok.io/sms/webhook`
   - Method: **POST**
4. Click **Save**

---

## Step 6: Test! (1 minute)

1. **Text your Twilio number** from your phone
2. Bot asks for your name
3. Reply: `name=YourName`
4. Start chatting with AI!

---

## Example Conversation

```
You: [sends any text]
Bot: Welcome! To get started, please tell me your name by texting: name=<your name>

You: name=Alice
Bot: Thanks, Alice! Your name has been saved. You can now chat with the AI...

You: What is machine learning?
Bot: Machine learning is a subset of artificial intelligence...

You: name=AliceSmith
Bot: Your name has been updated to: AliceSmith
```

---

## Verification Checklist

✅ LLM Server running on port 8033
✅ SMS Server running on port 8040
✅ ngrok tunnel active
✅ Twilio webhook configured
✅ .env file has correct credentials

---

## Quick Commands

### View Status
```bash
curl http://localhost:8040/sms/status
```

### Test Webhook Locally
```bash
curl -X POST http://localhost:8040/sms/webhook \
  -d "From=+12345678900" \
  -d "Body=test message"
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "SMS service not initialized" | Check `.env` credentials |
| Not receiving texts | Update Twilio webhook URL |
| Bot not responding | Check both servers are running |
| "Cannot connect to LLM Server" | Make sure `llm_server.py` is running |

---

## Cost

**Twilio Free Trial:** $15.50 credit (enough for ~1,800 messages)

**After trial:**
- $1.15/month for phone number
- $0.0079 per SMS sent/received
- **Example:** 100 conversations/month ≈ $2.73/month

---

## Next Steps

- Read full [SMS_SETUP_GUIDE.md](SMS_SETUP_GUIDE.md) for advanced features
- Deploy to production (no ngrok needed)
- Set up multiple users
- Customize AI responses

---

## Support

Having issues? Check:
1. Server logs in both terminals
2. Twilio debugger: [https://console.twilio.com/monitor/debugger](https://console.twilio.com/monitor/debugger)
3. ngrok web interface: [http://localhost:4040](http://localhost:4040)

**Need help?** See detailed troubleshooting in [SMS_SETUP_GUIDE.md](SMS_SETUP_GUIDE.md)
