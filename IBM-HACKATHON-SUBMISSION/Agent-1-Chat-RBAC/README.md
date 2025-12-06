# Agent 1: 💬 Chat & RBAC Control System

**Purpose:** AI-powered healthcare chat with role-based access control

## Quick Start

```bash
# Navigate to Agent 1
cd Agent-1-Chat-RBAC/mcp-server

# Start server
python run.py
```

## Features

✅ **Granite LLM Integration** - Local 8.1B parameter model, 128K context
✅ **5 Role Profiles** - Admin, Physician, Nurse, Patient, Auditor
✅ **Session Tracking** - IP logging, timestamps, activity monitoring
✅ **Real-time Audit** - All interactions immutably logged
✅ **OAuth SSO** - Google & Microsoft authentication
✅ **Fallback Chain** - Granite → Gemini → Text fallbacks

## Architecture

- **Frontend:** React-based chat interface with RBAC dashboard
- **Backend:** FastAPI REST API with WebSocket support
- **AI:** IBM Granite-3.1-8B local model
- **Database:** PostgreSQL with audit trail
- **Cache:** Redis for sessions

## Key Endpoints

- `POST /auth/login` - Email/password authentication
- `POST /api/chat/send` - Send message, get AI response
- `GET /api/chat/history` - Retrieve conversation history
- `POST /auth/google` - Google OAuth callback
- `GET /api/chat/greeting` - TTS greeting generation

## Files

```
mcp-server/
├── run.py                 # Server entry point
├── app/
│   ├── main.py           # FastAPI app setup
│   ├── routes/
│   │   ├── chat.py       # Chat routes
│   │   └── auth.py       # Authentication
│   ├── services/
│   │   ├── granite_model.py      # Granite LLM service
│   │   ├── watson_api.py         # AI orchestration
│   │   └── rbac_service.py       # Role management
│   └── security/
│       ├── rbac_manager.py       # RBAC logic
│       └── audit_logger.py       # Audit trails
├── models/
│   └── granite-3.1-8b-instruct/  # Local model weights
└── static/
    ├── chat.html         # Chat interface
    ├── login.html        # Login page
    └── js/css/           # Assets
```

## System Prompts by Role

```
🏥 Admin: "System administrator focused on compliance and operations"
👨‍⚕️ Physician: "Clinical decision support with medical knowledge"
👩‍⚕️ Nurse: "Care coordination and patient monitoring"
👤 Patient: "Empathetic health advisor without diagnosis"
📋 Auditor: "Regulatory review and compliance verification"
```

## Configuration

See `app/config.ini` for:
- Granite model path
- Database connection
- OAuth credentials
- API endpoints

## Testing

1. Login with test credentials
2. Send chat messages
3. Check `/docs` for API testing
4. Monitor audit logs in database

---

See main README for system-wide architecture.
