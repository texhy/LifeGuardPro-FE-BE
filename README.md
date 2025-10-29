# 🚀 LifeGuard-Pro FastAPI Backend

**Phase 1 Complete** - FastAPI backend with full chatbot integration

## **Quick Start**

###  **1. Activate Environment**
```bash
cd "/home/hassan/Desktop/Classic SH/LifeGuardPro -- Backend/Testing Research/lifeguard-pro-api"
source .venv/bin/activate
```

### **2. Run FastAPI Server**
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at: http://localhost:8000

### **3. Test API**

**Open another terminal and test:**

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Create session
curl -X POST http://localhost:8000/api/v1/session/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "Test User",
    "user_email": "test@example.com",
    "user_phone": "555-1234"
  }'

# Send chat message (replace SESSION_ID with actual session_id from above)
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID_HERE",
    "message": "What is CPO certification?"
  }'
```

## **API Documentation**

When server is running in development mode, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## **Project Structure**

```
lifeguard-pro-api/
├── api/
│   ├── main.py              # FastAPI app
│   ├── routes/              # API endpoints
│   ├── schemas/             # Pydantic models
│   ├── middleware.py        # Custom middleware
│   └── dependencies.py      # Shared dependencies
│
├── core/                    # Chatbot logic (from test_chatbot)
│   ├── graph.py             # LangGraph workflow
│   ├── planner_node.py
│   ├── executor_node.py
│   ├── react_responder.py
│   └── rag_executor.py
│
├── services/                # Business logic layer
│   ├── chat_service.py      # Chat orchestration
│   └── session_service.py   # Session management
│
├── config/                  # Configuration
│   ├── database.py          # DB connection
│   └── settings.py          # Environment settings
│
├── tools/                   # Agent tools (from test_chatbot)
├── nodes/                   # Graph nodes (from test_chatbot)
├── retrieval/               # RAG pipeline (from test_chatbot)
├── utils/                   # Utilities (from test_chatbot)
│
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## **API Endpoints**

### **Health**
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health with DB stats

### **Session**
- `POST /api/v1/session/create` - Create new chat session
- `GET /api/v1/session/{session_id}` - Get session details
- `DELETE /api/v1/session/{session_id}` - Delete session

### **Chat**
- `POST /api/v1/chat/message` - Send message, get response
- `GET /api/v1/chat/{session_id}/history` - Get conversation history

## **Environment Variables**

See `.env` file for configuration. Key variables:

- `OPENAI_API_KEY` - Your OpenAI API key
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL connection
- `API_PORT` - API server port (default: 8000)
- `ENVIRONMENT` - development or production
- `COVE_ENABLED` - Enable/disable CoVe verification (default: false for speed)

## **Features**

✅ FastAPI REST API
✅ Complete LangGraph integration
✅ 4-node workflow (guardrails → planner → executor → responder)
✅ Advanced RAG pipeline (MQE + Hybrid + RRF + MMR)
✅ 4 active tools (RAG, Pricing, Quote, Booking)
✅ Session management
✅ Pydantic validation
✅ CORS enabled
✅ Swagger/ReDoc documentation
✅ Logging middleware
✅ Rate limiting

## **Next Steps**

After testing the API:

1. **Build Frontend** - Create React/Vue chat interface
2. **Deploy to VPS** - Follow VPS_DEPLOYMENT_PLAN.md from test_chatbot
3. **Add SSL** - Configure HTTPS with Let's Encrypt
4. **Monitoring** - Set up logging and monitoring
5. **Production** - Deploy to production environment

## **Development**

### **Install Dependencies**
```bash
pip install -r requirements.txt
```

### **Run in Development Mode**
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### **Run in Production Mode**
```bash
# Update .env: ENVIRONMENT=production
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## **Testing**

Test with curl:
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Detailed health
curl http://localhost:8000/api/v1/health/detailed
```

## **Troubleshooting**

**Database connection failed:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -h localhost -U postgres -d vector_db
```

**Module not found:**
```bash
# Activate virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Port already in use:**
```bash
# Kill process on port 8000
sudo lsof -t -i:8000 | xargs kill -9

# Or use a different port
uvicorn api.main:app --reload --port 8001
```

---

**Created:** October 28, 2025  
**Status:** ✅ Phase 1 Complete - Ready for testing

