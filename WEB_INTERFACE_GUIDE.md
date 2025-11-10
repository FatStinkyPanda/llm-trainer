# LLM Trainer Web Interface Guide

## 🎉 New Features

The LLM Trainer now has a **web-based control panel** with support for multiple LLM sources!

## 🚀 Quick Start

1. **Start the middleware:**
   ```bash
   python middleware.py
   ```

2. **Open the web interface:**
   - Navigate to: http://localhost:8032
   - You'll see the LLM Trainer Control Panel

3. **Configure your LLM source:**
   - Choose between **Ollama (Local)** or **OpenRouter (API)**
   - Configure model settings
   - Save configuration

4. **Start training:**
   - Set training parameters (exchanges, delay, topic interval)
   - Click "Start Training"
   - Monitor progress in real-time

## 📡 LLM Sources

### Ollama (Local)

**Default option** - Uses locally installed Ollama models.

**Setup:**
1. Select "Ollama (Local)" as LLM Source
2. Enter your model name (e.g., `gemma3:4b`, `qwen3:8b`)
3. Click "Save Configuration"

**Advantages:**
- ✅ Free
- ✅ Fast (runs locally)
- ✅ No API costs
- ✅ Privacy (all data stays local)

**Requirements:**
- Ollama must be running: `ollama serve`
- Model must be downloaded: `ollama pull qwen3:8b`

### OpenRouter (API)

**Cloud-based** - Access to hundreds of models including Claude, GPT-4, and more.

**Setup:**
1. Get API key from [openrouter.ai/keys](https://openrouter.ai/keys)
2. Select "OpenRouter (API)" as LLM Source
3. Enter your API key
4. Choose a model (e.g., `anthropic/claude-3.5-sonnet`)
5. Click "Save Configuration"

**Advantages:**
- ✅ Access to most powerful models
- ✅ No local GPU required
- ✅ Easy model switching
- ✅ Automatic scaling

**Popular Models:**
- `anthropic/claude-3.5-sonnet` - Excellent for teaching
- `openai/gpt-4-turbo` - Very capable
- `meta-llama/llama-3.1-70b-instruct` - Open source, powerful
- `google/gemini-pro-1.5` - Fast and capable

**Cost:**
- Pay per token
- Usually $0.001-0.015 per 1000 tokens
- Typical training session: $0.10-0.50

## 🎛️ Web Interface Features

### LLM Configuration Panel
- **LLM Source**: Switch between Ollama and OpenRouter
- **Model Selection**: Choose/enter model name
- **API Key**: For OpenRouter (securely stored)

### Training Control Panel
- **Max Exchanges**: How many conversation turns
- **Delay**: Seconds between messages (prevents rate limits)
- **Topic Switch Interval**: Messages before changing topic

### Status Display
- **Training Status**: Running/Stopped with live updates
- **Current Source**: Which LLM system is active
- **Current Model**: Which specific model is being used
- **Exchanges Completed**: Progress counter
- **Current Topic**: What CEREBRUM is learning about

## 🔄 Switching Between Sources

You can switch between Ollama and OpenRouter **anytime**:

1. Stop any running training
2. Change LLM Source in web interface
3. Update model settings
4. Save configuration
5. Start new training session

The system automatically reloads configuration when you start training!

## 📊 Monitoring Training

The web interface updates every 3 seconds with:
- Training status (running/stopped)
- Number of exchanges completed
- Current conversation topic
- Active LLM source and model

## 💡 Tips

### For Best Results:

**Using Ollama:**
- Use `qwen3:8b` or larger for best teaching quality
- Ensure Ollama is running before starting training
- Check model is downloaded: `ollama list`

**Using OpenRouter:**
- Use Claude 3.5 Sonnet for excellent teaching
- Set delay to 1-2 seconds to avoid rate limits
- Monitor costs at [openrouter.ai](https://openrouter.ai)

### Training Parameters:

**Max Exchanges:**
- Start with 50-100 for testing
- Use 500+ for serious training sessions

**Delay:**
- Ollama: 0.5-1 second (fast local response)
- OpenRouter: 1-2 seconds (avoid rate limits)

**Topic Interval:**
- 10-15 messages works well for most topics
- Longer (20-30) for complex topics

## 🐛 Troubleshooting

**"Ollama is not running":**
- Run: `ollama serve`
- Check: `http://localhost:11434/api/tags`

**"OpenRouter API key not configured":**
- Get key from [openrouter.ai/keys](https://openrouter.ai/keys)
- Enter in web interface
- Click "Save Configuration"

**Configuration not saving:**
- Check file permissions on `config.json`
- Ensure middleware has write access

**Training won't start:**
- Check CEREBRUM is running (http://localhost:8000)
- Verify LLM source is accessible
- Check middleware logs for errors

## 📁 Files

- `web_interface.html` - Control panel UI
- `control-panel.js` - Interface JavaScript
- `config.json` - Configuration storage
- `middleware.py` - API server (port 8032)

## 🔐 Security Notes

- API keys are stored in `config.json` (keep this file secure)
- The web interface runs locally only (not exposed to internet)
- Use environment variables for production deployments

## 🎓 Next Steps

1. Try both Ollama and OpenRouter
2. Experiment with different models
3. Monitor conversations in CEREBRUM's API Viewer
4. Adjust training parameters based on results

Enjoy the enhanced LLM Trainer! 🚀
