"""
FastAPI Main Application
Member 360° Health Intelligence Assistant
"""
import os
import logging
import math
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes_members import router as members_router
from app.api.routes_ai import router as ai_router
from app.api.routes_health import router as health_router
from app.api.routes_requests import router as requests_router
from app.database.mongodb import get_database
from app.services.member_service import search_members, count_members, get_member_by_id
from app.services.request_service import search_requests, count_requests
from app.services.aggregation_service import get_member_360_profile
from app.services.auth import (
    get_secret_key,
    authenticate_admin,
    is_admin_authenticated
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("member360.main")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Member 360 application database...")
    db = get_database()
    logger.info(f"Database initialized: {db.name}")
    yield

app = FastAPI(
    title="Member 360° Health Intelligence Assistant",
    description="Operational healthcare intelligence platform for care coordinators and service representatives.",
    version="1.0.0",
    lifespan=lifespan
)

# Session Middleware (server-side signed session cookie)
app.add_middleware(
    SessionMiddleware,
    secret_key=get_secret_key(),
    session_cookie="member360_admin_session",
    max_age=86400,
    same_site="lax",
    https_only=False
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files & Jinja2 Templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def format_inr(value):
    """Format monetary values in Indian Rupees (INR / ₹) with Indian numbering format."""
    if value is None or value == "":
        return "₹0.00"
    try:
        val = float(value)
        is_negative = val < 0
        val = abs(val)
        s = f"{val:.2f}"
        int_part, dec_part = s.split(".")
        if len(int_part) > 3:
            last_three = int_part[-3:]
            remaining = int_part[:-3]
            groups = []
            while len(remaining) > 2:
                groups.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            if remaining:
                groups.insert(0, remaining)
            formatted_int = ",".join(groups) + "," + last_three
        else:
            formatted_int = int_part
        return f"₹{'-' if is_negative else ''}{formatted_int}.{dec_part}"
    except (ValueError, TypeError):
        return f"₹{value}"

templates.env.filters["inr"] = format_inr

# Mount API Routers
app.include_router(health_router, prefix="/api")
app.include_router(members_router, prefix="/api")
app.include_router(requests_router, prefix="/api")
app.include_router(ai_router, prefix="/api/ai")

# Authentication Routes
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Admin Login Page: public endpoint for authentication."""
    if is_admin_authenticated(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None}
    )

@app.post("/login")
async def login_submit(request: Request):
    """Process admin credentials and initialize authenticated session."""
    from urllib.parse import parse_qs
    from fastapi.responses import JSONResponse

    content_type = request.headers.get("content-type", "")
    username = ""
    password = ""

    if "application/json" in content_type:
        try:
            data = await request.json()
            username = data.get("username", "")
            password = data.get("password", "")
        except Exception:
            pass
    else:
        body = await request.body()
        parsed = parse_qs(body.decode("utf-8"))
        username = parsed.get("username", [""])[0]
        password = parsed.get("password", [""])[0]

    if authenticate_admin(username, password):
        request.session["admin_authenticated"] = True
        request.session["admin_user"] = username
        logger.info(f"Admin '{username}' successfully authenticated.")
        if "application/json" in content_type:
            return JSONResponse(content={"success": True, "message": "Authenticated successfully", "redirect_url": "/"})
        return RedirectResponse(url="/", status_code=303)

    logger.warning(f"Failed login attempt for username '{username}'.")
    if "application/json" in content_type:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Invalid administrator credentials. Please try again."}
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": "Invalid administrator credentials. Please try again.",
            "username": username
        },
        status_code=401
    )

@app.post("/logout")
async def logout_submit(request: Request):
    """Terminate admin session and redirect to login page."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

# Protected Web UI Routes
@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """Homepage: Dashboard overview and quick search (Admin Protected)"""
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    db = get_database()
    total_members = db.members.count_documents({})
    recent_members = search_members(limit=6)
    
    total_open_gaps = db.care_gaps.count_documents({"status": "Open"})
    pending_auths = db.authorizations.count_documents({"status": "Pending"})
    unresolved_interactions = db.interactions.count_documents({"status": {"$in": ["Open", "In Progress"]}})
    pending_org_requests = db.requests.count_documents({"status": {"$in": ["Pending", "In Review"]}})

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "total_members": total_members,
            "recent_members": recent_members,
            "total_open_gaps": total_open_gaps,
            "pending_auths": pending_auths,
            "unresolved_interactions": unresolved_interactions,
            "pending_org_requests": pending_org_requests
        }
    )

@app.get("/requests", response_class=HTMLResponse)
async def requests_page(
    request: Request,
    q: str = "",
    member_id: str = "",
    status: str = "",
    priority: str = "",
    request_type: str = "",
    page: int = 1
):
    """Organization Requests Management & Directory (Admin Protected)"""
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    limit = 15
    skip = (page - 1) * limit
    requests_list = search_requests(
        member_id=member_id or None,
        status=status or None,
        priority=priority or None,
        request_type=request_type or None,
        query=q or None,
        limit=limit,
        skip=skip
    )
    total = count_requests(
        member_id=member_id or None,
        status=status or None,
        priority=priority or None,
        request_type=request_type or None,
        query=q or None
    )
    total_pages = max(1, (total + limit - 1) // limit)

    return templates.TemplateResponse(
        request=request,
        name="requests.html",
        context={
            "requests": requests_list,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "query": q,
            "member_id": member_id,
            "selected_status": status,
            "selected_priority": priority,
            "selected_type": request_type
        }
    )

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = "", page: int = 1):
    """Member directory and search page (Admin Protected)"""
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    limit = 15
    skip = (page - 1) * limit
    members = search_members(query=q, limit=limit, skip=skip)
    total = count_members(query=q)
    total_pages = max(1, (total + limit - 1) // limit)

    return templates.TemplateResponse(
        request=request,
        name="member_search.html",
        context={
            "query": q,
            "members": members,
            "page": page,
            "total_pages": total_pages,
            "total": total
        }
    )

@app.get("/member/{member_id}", response_class=HTMLResponse)
async def member_360_page(request: Request, member_id: str):
    """Comprehensive Member 360° Profile Dashboard (Admin Protected)"""
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    profile = get_member_360_profile(member_id)
    if not profile:
        return templates.TemplateResponse(
            request=request,
            name="member_search.html",
            context={
                "query": member_id,
                "error": f"Member with ID '{member_id}' was not found in records.",
                "members": search_members(limit=10),
                "page": 1,
                "total_pages": 1,
                "total": 0
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="member_360.html",
        context={
            "p": profile,
            "m": profile["member"],
            "stats": profile["stats"]
        }
    )
