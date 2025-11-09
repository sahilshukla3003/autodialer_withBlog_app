
# 🚀 AI Autodialer & Blog Generator

A complete FastAPI application with **AI-powered calling** and **automatic blog generation**.

## ✨ Features

### 📞 Autodialer
- ✅ Upload 100+ phone numbers (CSV or paste)
- ✅ AI voice commands: "call +918001234567"
- ✅ Bulk calling functionality
- ✅ Real-time call tracking & status updates
- ✅ Call logs with duration tracking
- ✅ Export to CSV
- ✅ Test mode for development

### 📝 Blog Generator
- ✅ Single article generation
- ✅ Bulk generate from title list
- ✅ Google Gemini AI powered
- ✅ Automatic content creation
- ✅ View tracking
- ✅ SEO-friendly slugs

### 💾 Storage
- ✅ Zero database setup - JSON file storage
- ✅ Easy backup and portability
- ✅ Instant deployment

## 📦 Installation

1. Create project folder
mkdir task2_autodialer && cd task2_autodialer

2. Install dependencies
pip install -r requirements.txt

3. Create .env file
cp .env.example .env

Edit .env and add your API keys
4. Create folders
mkdir -p data templates

5. Add all template files
6. Run
python main.py



## 🔑 API Keys Setup

### Gemini API (Free)
1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy and paste into `.env` as `GEMINI_API_KEY`

### Twilio (Free Trial)
1. Sign up at https://www.twilio.com/try-twilio
2. Get your Account SID, Auth Token, and Phone Number
3. Add to `.env` file

## 🌐 Access

- **Dashboard**: http://localhost:8000
- **Blog**: http://localhost:8000/blog
- **Health Check**: http://localhost:8000/api/health
- **API Docs**: http://localhost:8000/docs

## 📁 Data Storage

All data stored in JSON files:
- `data/phone_numbers.json` - Call records
- `data/blog_posts.json` - Blog articles
- `data/call_logs.json` - Call history

## 🧪 Testing

### Test AI Voice Command
"make a call to +918001234567"
"call +919876543210"



### Test Blog Generation
Title: "Python Best Practices"
Description: "Tips for clean code"



### Use Test Numbers
**IMPORTANT**: Use 1-800 numbers for testing!
+18001234567
+18009876543



## 🔌 API Endpoints

### Autodialer
- `POST /api/upload_numbers` - Upload phone numbers
- `POST /api/ai_call` - AI voice command
- `POST /api/bulk_call` - Bulk calling
- `GET /api/call_stats` - Get statistics
- `GET /api/export_calls` - Export CSV
- `POST /api/clear_all` - Clear all

### Blog
- `POST /api/generate_article` - Generate single
- `POST /api/generate_articles_bulk` - Generate multiple
- `GET /blog/{slug}` - View article
- `DELETE /api/blog/{id}` - Delete article

## 🚦 Health Check

curl http://localhost:8000/api/health



## 📝 Usage Examples

### Upload Numbers (curl)
curl -X POST http://localhost:8000/api/upload_numbers
-F "numbers_=+918001234567
+918009876543"



### Generate Article (curl)
curl -X POST http://localhost:8000/api/generate_article
-H "Content-Type: application/json"
-d '{"title":"Python Tips","description":"Best practices"}'



## ⚙️ Requirements

- Python 3.8+
- FastAPI
- Twilio account (optional)
- Gemini API key (optional)

## 🐛 Troubleshooting

### Gemini "404 models/gemini-pro not found"
**Fixed!** The app now automatically detects working models.

### Twilio Errors
- Check credentials in `.env`
- Verify phone number format (+1234567890)
- Use test numbers (1-800-xxx-xxxx)

### Dashboard Not Updating
- Auto-refreshes every 30 seconds
- Click "Test: Simulate Call" to test status updates

## 📄 License

MIT - Free to use

## 🤝 Support

If you encounter issues:
1. Check `.env` file has correct API keys
2. Visit http://localhost:8000/api/health
3. Check console logs for errors

---

**Made with ❤️ using FastAPI + Gemini AI + Twilio**
Quick Start Commands:
bash
# Setup
pip install -r requirements.txt

# Run
python main.py

# Visit
http://localhost:8000
