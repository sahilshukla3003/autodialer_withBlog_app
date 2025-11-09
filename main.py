from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import json
import csv
import io
import re
from datetime import datetime
from typing import Optional
import google.generativeai as genai
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from pathlib import Path
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()
print("Loading environment variables...")

# Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Debug: Print what we loaded
print(f"TWILIO_ACCOUNT_SID loaded: {'Yes' if TWILIO_ACCOUNT_SID else 'No'}")
print(f"TWILIO_AUTH_TOKEN loaded: {'Yes' if TWILIO_AUTH_TOKEN else 'No'}")
print(f"TWILIO_PHONE_NUMBER loaded: {'Yes' if TWILIO_PHONE_NUMBER else 'No'}")
print(f"GEMINI_API_KEY loaded: {'Yes' if GEMINI_API_KEY else 'No'}")

# Initialize FastAPI
app = FastAPI(title="AI Autodialer & Blog Generator")

# Setup Templates
templates = Jinja2Templates(directory="templates")

# Data storage paths
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

PHONE_NUMBERS_FILE = DATA_DIR / "phone_numbers.json"
BLOG_POSTS_FILE = DATA_DIR / "blog_posts.json"
CALL_LOGS_FILE = DATA_DIR / "call_logs.json"

# Initialize JSON files
def init_json_files():
    """Initialize JSON storage files"""
    for file_path in [PHONE_NUMBERS_FILE, BLOG_POSTS_FILE, CALL_LOGS_FILE]:
        if not file_path.exists():
            with open(file_path, 'w') as f:
                json.dump([], f)
            print(f"Created: {file_path}")

init_json_files()

# Initialize Twilio
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        # Test connection
        twilio_client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        print("✓ Twilio connected successfully")
    except Exception as e:
        print(f"⚠ Twilio connection failed: {e}")
        twilio_client = None
else:
    print("⚠ Twilio not configured - missing credentials")

# Initialize Gemini - FIXED WITH BETTER ERROR HANDLING
gemini_model = None
gemini_error = None

if GEMINI_API_KEY:
    print(f"Attempting to configure Gemini with API key: {GEMINI_API_KEY[:10]}...")
    try:
        # Configure API
        genai.configure(api_key=GEMINI_API_KEY)
        print("✓ Gemini API configured")
        
        # List available models
        print("Checking available models...")
        available_models = []
        try:
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    available_models.append(model.name)
                    print(f"  Found model: {model.name}")
        except Exception as e:
            print(f"Could not list models: {e}")
        
        # Try different model names
        model_names = [
            'gemini-1.5-flash',
            'gemini-1.5-pro', 
            'gemini-pro',
            'models/gemini-1.5-flash',
            'models/gemini-1.5-pro',
            'models/gemini-pro'
        ]
        
        # Add available models to try list
        model_names.extend(available_models)
        
        for model_name in model_names:
            try:
                print(f"Trying model: {model_name}")
                test_model = genai.GenerativeModel(model_name)
                
                # Quick test generation
                test_response = test_model.generate_content("Say 'Hello'")
                
                if test_response and test_response.text:
                    gemini_model = test_model
                    print(f"✓ Gemini AI connected successfully with model: {model_name}")
                    print(f"✓ Test response: {test_response.text[:50]}...")
                    break
                    
            except Exception as model_error:
                print(f"  Model {model_name} failed: {str(model_error)[:100]}")
                continue
        
        if not gemini_model:
            gemini_error = "No working model found. Available models: " + ", ".join(available_models[:3])
            print(f"⚠ {gemini_error}")
            
    except Exception as e:
        gemini_error = str(e)
        print(f"⚠ Gemini configuration error: {gemini_error}")
else:
    gemini_error = "API key not provided"
    print("⚠ GEMINI_API_KEY not set in .env file")


# ==================== PYDANTIC MODELS ====================

class AICallRequest(BaseModel):
    command: str

class GenerateArticleRequest(BaseModel):
    title: str
    description: str = ""

class GenerateBulkRequest(BaseModel):
    prompt: str


# ==================== JSON FILE OPERATIONS ====================

def load_phone_numbers():
    """Load phone numbers from JSON"""
    try:
        with open(PHONE_NUMBERS_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading phone numbers: {e}")
        return []

def save_phone_numbers(data):
    """Save phone numbers to JSON"""
    try:
        with open(PHONE_NUMBERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Saved {len(data)} phone numbers")
    except Exception as e:
        print(f"Error saving phone numbers: {e}")

def load_blog_posts():
    """Load blog posts from JSON"""
    try:
        with open(BLOG_POSTS_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading blog posts: {e}")
        return []

def save_blog_posts(data):
    """Save blog posts to JSON"""
    try:
        with open(BLOG_POSTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Saved {len(data)} blog posts")
    except Exception as e:
        print(f"Error saving blog posts: {e}")

def update_call_status_by_sid(call_sid: str, status: str, duration: int = 0):
    """Update call status by Twilio call SID - FIXED"""
    try:
        phone_numbers = load_phone_numbers()
        updated = False
        
        for phone in phone_numbers:
            if phone.get('call_sid') == call_sid:
                phone['status'] = status
                phone['duration'] = duration
                updated = True
                print(f"✓ Updated {phone['number']}: {status} ({duration}s)")
                break
        
        if updated:
            save_phone_numbers(phone_numbers)
        else:
            print(f"⚠ Call SID {call_sid} not found")
            
        return updated
    except Exception as e:
        print(f"Error updating call status: {e}")
        return False


# ==================== DASHBOARD ====================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard"""
    phone_numbers = load_phone_numbers()
    
    total = len(phone_numbers)
    completed = len([p for p in phone_numbers if p.get('status') == 'completed'])
    failed = len([p for p in phone_numbers if p.get('status') in ['failed', 'busy', 'no-answer']])
    pending = len([p for p in phone_numbers if p.get('status') == 'pending'])
    
    stats = {
        'total': total,
        'completed': completed,
        'failed': failed,
        'pending': pending,
        'success_rate': f"{(completed/total*100):.1f}%" if total > 0 else "0%"
    }
    
    recent_calls = sorted(phone_numbers, key=lambda x: x.get('created_at', ''), reverse=True)[:15]
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "recent_calls": recent_calls
    })


# ==================== AUTODIALER ENDPOINTS ====================

@app.post("/api/upload_numbers")
async def upload_numbers(
    file: UploadFile = File(None),
    numbers_text: str = Form(None)
):
    """Upload phone numbers via CSV or text"""
    try:
        phone_numbers = load_phone_numbers()
        count = 0
        
        if file:
            contents = await file.read()
            stream = io.StringIO(contents.decode("utf8"))
            csv_reader = csv.reader(stream)
            
            for row in csv_reader:
                if row and row[0].strip():
                    number = row[0].strip()
                    if not any(p['number'] == number for p in phone_numbers):
                        phone_numbers.append({
                            'id': len(phone_numbers) + 1,
                            'number': number,
                            'status': 'pending',
                            'duration': 0,
                            'call_sid': None,
                            'created_at': datetime.utcnow().isoformat(),
                            'called_at': None,
                            'notes': ''
                        })
                        count += 1
        
        elif numbers_text:
            for number in numbers_text.split('\n'):
                number = number.strip()
                if number and not any(p['number'] == number for p in phone_numbers):
                    phone_numbers.append({
                        'id': len(phone_numbers) + 1,
                        'number': number,
                        'status': 'pending',
                        'duration': 0,
                        'call_sid': None,
                        'created_at': datetime.utcnow().isoformat(),
                        'called_at': None,
                        'notes': ''
                    })
                    count += 1
        
        save_phone_numbers(phone_numbers)
        return {"success": True, "message": f"✓ {count} numbers uploaded", "count": count}
    
    except Exception as e:
        print(f"Upload error: {e}")
        return {"success": False, "message": str(e)}


@app.post("/api/ai_call")
async def ai_call(request: AICallRequest):
    """AI-powered call using natural language"""
    try:
        command = request.command
        print(f"AI Command: {command}")
        
        # Extract phone number
        phone_match = re.search(r'[\+\d][\d\s\-\(\)]{8,}', command)
        
        if not phone_match:
            return {"success": False, "message": "❌ Could not find phone number"}
        
        number = re.sub(r'[\s\-\(\)]', '', phone_match.group().strip())
        print(f"Extracted: {number}")
        
        if not twilio_client:
            return {"success": False, "message": "❌ Twilio not configured"}
        
        phone_numbers = load_phone_numbers()
        phone = next((p for p in phone_numbers if p['number'] == number), None)
        
        if not phone:
            phone = {
                'id': max([p['id'] for p in phone_numbers], default=0) + 1,
                'number': number,
                'status': 'pending',
                'duration': 0,
                'call_sid': None,
                'created_at': datetime.utcnow().isoformat(),
                'called_at': None,
                'notes': ''
            }
            phone_numbers.append(phone)
        
        try:
            # Get server URL (for production, set this in .env)
            server_url = os.getenv("SERVER_URL", "http://your-domain.com")
            
            call = twilio_client.calls.create(
                url=f"{server_url}/api/voice",
                to=number,
                from_=TWILIO_PHONE_NUMBER,
                status_callback=f"{server_url}/api/call_status",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST'
            )
            
            phone['call_sid'] = call.sid
            phone['status'] = 'calling'
            phone['called_at'] = datetime.utcnow().isoformat()
            save_phone_numbers(phone_numbers)
            
            print(f"✓ Call initiated: {call.sid}")
            
            return {
                "success": True,
                "message": f"✓ Calling {number}...",
                "call_sid": call.sid
            }
        
        except Exception as call_error:
            phone['status'] = 'failed'
            phone['notes'] = str(call_error)
            save_phone_numbers(phone_numbers)
            return {"success": False, "message": f"❌ {str(call_error)}"}
    
    except Exception as e:
        print(f"Error: {e}")
        return {"success": False, "message": f"❌ {str(e)}"}


@app.post("/api/bulk_call")
async def bulk_call():
    """Start bulk calling"""
    try:
        if not twilio_client:
            return {"success": False, "message": "❌ Twilio not configured"}
        
        phone_numbers = load_phone_numbers()
        pending = [p for p in phone_numbers if p.get('status') == 'pending']
        
        if not pending:
            return {"success": False, "message": "No pending numbers"}
        
        server_url = os.getenv("SERVER_URL", "http://your-domain.com")
        
        for phone in pending:
            try:
                call = twilio_client.calls.create(
                    url=f"{server_url}/api/voice",
                    to=phone['number'],
                    from_=TWILIO_PHONE_NUMBER,
                    status_callback=f"{server_url}/api/call_status",
                    status_callback_event=['completed'],
                    status_callback_method='POST'
                )
                phone['call_sid'] = call.sid
                phone['status'] = 'calling'
                phone['called_at'] = datetime.utcnow().isoformat()
            except Exception as e:
                phone['status'] = 'failed'
                phone['notes'] = str(e)
        
        save_phone_numbers(phone_numbers)
        return {"success": True, "message": f"✓ Started calling {len(pending)} numbers"}
    
    except Exception as e:
        return {"success": False, "message": str(e)}


# ==================== TWILIO WEBHOOKS - FIXED ====================

@app.post("/api/voice")
@app.get("/api/voice")
async def voice_handler():
    """TwiML voice response"""
    resp = VoiceResponse()
    resp.say(
        "Hello! This is an automated test call from the AI Autodialer system. "
        "This is a demonstration call for testing purposes. Thank you and goodbye!",
        voice='alice',
        language='en-US'
    )
    return Response(content=str(resp), media_type="application/xml")


@app.post("/api/call_status")
async def call_status_webhook(request: Request):
    """
    Twilio status callback webhook - FIXED
    This endpoint receives call status updates from Twilio
    """
    try:
        form_data = await request.form()
        
        call_sid = form_data.get('CallSid', '')
        call_status = form_data.get('CallStatus', '')
        call_duration = form_data.get('CallDuration', '0')
        
        print(f"📞 Webhook received: SID={call_sid}, Status={call_status}, Duration={call_duration}s")
        
        # Update status in JSON file
        updated = update_call_status_by_sid(call_sid, call_status, int(call_duration))
        
        if updated:
            print(f"✓ Status updated successfully")
        else:
            print(f"⚠ Could not find call to update")
        
        return JSONResponse({"status": "ok"})
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.post("/api/simulate_call_complete/{phone_id}")
async def simulate_call_complete(phone_id: int):
    """Simulate call completion for testing - FIXED"""
    try:
        phone_numbers = load_phone_numbers()
        
        for phone in phone_numbers:
            if phone['id'] == phone_id:
                import random
                statuses = ['completed', 'failed', 'busy', 'no-answer']
                new_status = random.choice(statuses)
                new_duration = random.randint(10, 180)
                
                phone['status'] = new_status
                phone['duration'] = new_duration
                
                save_phone_numbers(phone_numbers)
                
                print(f"✓ Simulated: {phone['number']} -> {new_status} ({new_duration}s)")
                
                return {
                    "success": True, 
                    "message": f"✓ Updated: {phone['number']} → {new_status}"
                }
        
        return {"success": False, "message": "Phone number not found"}
    
    except Exception as e:
        print(f"Simulation error: {e}")
        return {"success": False, "message": str(e)}


@app.get("/api/call_stats")
async def call_stats():
    """Get real-time call statistics"""
    phone_numbers = load_phone_numbers()
    
    total = len(phone_numbers)
    completed = len([p for p in phone_numbers if p.get('status') == 'completed'])
    failed = len([p for p in phone_numbers if p.get('status') in ['failed', 'busy', 'no-answer']])
    pending = len([p for p in phone_numbers if p.get('status') == 'pending'])
    calling = len([p for p in phone_numbers if p.get('status') == 'calling'])
    
    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "calling": calling,
        "success_rate": f"{(completed/total*100):.1f}%" if total > 0 else "0%"
    }


@app.get("/api/export_calls")
async def export_calls():
    """Export to CSV"""
    try:
        phone_numbers = load_phone_numbers()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Phone Number', 'Status', 'Duration', 'Called At'])
        
        for call in phone_numbers:
            writer.writerow([
                call['number'],
                call['status'],
                call['duration'],
                call.get('called_at', 'N/A')
            ])
        
        return {"success": True, "csv": output.getvalue()}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/clear_all")
async def clear_all():
    """Clear all numbers"""
    try:
        save_phone_numbers([])
        return {"success": True, "message": "✓ All cleared"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ==================== BLOG ENDPOINTS - FIXED ====================

@app.get("/blog", response_class=HTMLResponse)
async def blog_page(request: Request):
    """Blog listing page"""
    posts = load_blog_posts()
    posts = sorted(posts, key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Pass gemini status to template
    gemini_status = {
        'configured': gemini_model is not None,
        'error': gemini_error
    }
    
    return templates.TemplateResponse("blog.html", {
        "request": request,
        "posts": posts,
        "gemini_status": gemini_status
    })


@app.post("/api/generate_article")
async def generate_article(request: GenerateArticleRequest):
    """Generate single article - FIXED"""
    try:
        print(f"Generate request: {request.title}")
        
        if not gemini_model:
            error_msg = f"❌ Gemini not available. Error: {gemini_error or 'Not configured'}"
            print(error_msg)
            return {"success": False, "message": error_msg}
        
        prompt = f"""Write a comprehensive technical blog post about: {request.title}

{f'Context: {request.description}' if request.description else ''}

Requirements:
- Professional, informative tone
- Include code examples where relevant
- Use ## for section headings
- Length: 1000-1500 words
- Practical examples and tips
- Brief conclusion

Write the complete article:"""

        print("Calling Gemini API...")
        response = gemini_model.generate_content(prompt)
        
        if not response or not response.text:
            return {"success": False, "message": "❌ Empty response from Gemini"}
        
        content = response.text
        print(f"✓ Generated {len(content)} characters")
        
        slug = re.sub(r'[^a-z0-9]+', '-', request.title.lower()).strip('-')[:100]
        
        posts = load_blog_posts()
        
        if any(p['slug'] == slug for p in posts):
            slug = f"{slug}-{int(datetime.utcnow().timestamp())}"
        
        post = {
            'id': max([p['id'] for p in posts], default=0) + 1,
            'title': request.title,
            'slug': slug,
            'content': content,
            'description': request.description[:500] if request.description else request.title[:200],
            'created_at': datetime.utcnow().isoformat(),
            'views': 0
        }
        
        posts.append(post)
        save_blog_posts(posts)
        
        return {
            "success": True,
            "message": "✓ Article generated",
            "slug": slug,
            "title": request.title
        }
    
    except Exception as e:
        print(f"Generation error: {e}")
        return {"success": False, "message": f"❌ Error: {str(e)}"}


@app.post("/api/generate_articles_bulk")
async def generate_articles_bulk(request: GenerateBulkRequest):
    """Generate multiple articles - FIXED"""
    try:
        if not gemini_model:
            return {"success": False, "message": f"❌ Gemini not available: {gemini_error}"}
        
        articles = []
        for line in request.prompt.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '|' in line:
                parts = line.split('|', 1)
                title = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else ''
            else:
                title = line
                description = ''
            
            if title:
                articles.append({'title': title, 'description': description})
        
        if not articles:
            return {"success": False, "message": "No articles found"}
        
        posts = load_blog_posts()
        results = []
        
        for idx, article in enumerate(articles, 1):
            try:
                print(f"[{idx}/{len(articles)}] {article['title']}")
                
                prompt = f"""Write a technical blog post: {article['title']}
{f"Details: {article['description']}" if article['description'] else ''}

Requirements:
- Professional tone
- Code examples
- ## headings
- 800-1200 words
- Practical tips

Write the article:"""

                response = gemini_model.generate_content(prompt)
                content = response.text
                
                slug = re.sub(r'[^a-z0-9]+', '-', article['title'].lower()).strip('-')[:100]
                if any(p['slug'] == slug for p in posts):
                    slug = f"{slug}-{int(datetime.utcnow().timestamp())}"
                
                post = {
                    'id': max([p['id'] for p in posts], default=0) + 1,
                    'title': article['title'],
                    'slug': slug,
                    'content': content,
                    'description': article['description'][:500] if article['description'] else article['title'][:200],
                    'created_at': datetime.utcnow().isoformat(),
                    'views': 0
                }
                
                posts.append(post)
                results.append({'title': article['title'], 'success': True, 'slug': slug})
                
            except Exception as e:
                results.append({'title': article['title'], 'success': False, 'error': str(e)})
        
        save_blog_posts(posts)
        
        successful = len([r for r in results if r['success']])
        return {
            "success": True,
            "message": f"✓ Generated {successful}/{len(articles)}",
            "results": results
        }
    
    except Exception as e:
        return {"success": False, "message": f"❌ {str(e)}"}


@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(slug: str, request: Request):
    """View blog post"""
    posts = load_blog_posts()
    post = next((p for p in posts if p['slug'] == slug), None)
    
    if not post:
        return HTMLResponse("<h1>404 - Not Found</h1>", status_code=404)
    
    post['views'] = post.get('views', 0) + 1
    save_blog_posts(posts)
    
    return templates.TemplateResponse("blog_post.html", {
        "request": request,
        "post": post
    })


@app.get("/api/health")
async def health_check():
    """System health check"""
    model_info = "Not configured"
    if gemini_model:
        try:
            model_info = getattr(gemini_model, '_model_name', 'Connected')
        except:
            model_info = "Connected"
    
    return {
        "status": "✓ Running",
        "twilio": {
            "configured": twilio_client is not None,
            "status": "✓ Connected" if twilio_client else "✗ Not configured"
        },
        "gemini": {
            "configured": gemini_model is not None,
            "status": f"✓ Model: {model_info}" if gemini_model else f"✗ Error: {gemini_error}",
            "model": model_info if gemini_model else None
        },
        "storage": "✓ JSON Files",
        "data": {
            "phone_numbers": len(load_phone_numbers()),
            "blog_posts": len(load_blog_posts())
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("🚀 AI AUTODIALER & BLOG GENERATOR")
    print("="*70)
    print("📍 Dashboard:  http://localhost:8000")
    print("📍 Blog:       http://localhost:8000/blog")
    print("📍 Health:     http://localhost:8000/api/health")
    print("="*70)
    print("\nConfiguration Status:")
    print(f"  Gemini: {'✓ Connected' if gemini_model else f'✗ {gemini_error}'}")
    print(f"  Twilio: {'✓ Connected' if twilio_client else '✗ Not configured'}")
    print("="*70)
    
    if not gemini_model:
        print("\n⚠️  WARNING: Gemini API not working!")
        print(f"   Error: {gemini_error}")
        print("   1. Check your .env file has GEMINI_API_KEY")
        print("   2. Get key from: https://makersuite.google.com/app/apikey")
        print("   3. Restart the application")
    
    if not twilio_client:
        print("\n⚠️  WARNING: Twilio not configured!")
        print("   Set credentials in .env to enable calling")
    
    print("\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
