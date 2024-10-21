from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware  # Add this import
from typing import Optional
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client, Client

app = FastAPI()

load_dotenv()
url = os.getenv("URL")
key = os.getenv("KEY")
supabase: Client = create_client(url, key)

# Add the session middleware (secret_key should be a strong random key)
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In-memory database for user credentials (for manual auth)
users_db = {}

# Dependency function to check login status
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

# Route for login page ("/")
@app.get("/")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Route for handling login ("/")
@app.post("/")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Check if the user exists and the password matches
    if username not in users_db or users_db[username] != password:
        # Return login form again with an error message if authentication fails
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    
    # Successful login, redirect to posts page
    response = RedirectResponse("/posts", status_code=303)
    response.set_cookie(key="session", value=username)  # Set a simple session cookie
    return response

# Route to fetch and show all posts ("/posts")
@app.get("/posts")
async def read_posts(request: Request):
    session_user = request.cookies.get("session")
    if not session_user:
        return RedirectResponse("/")
    
    # Fetch posts from Supabase
    posts = supabase.table("Posts").select("*").order("created_at", desc=True).execute().data
    return templates.TemplateResponse("index.html", {"request": request, "posts": posts})

# Route for user registration ("/register")
@app.get("/register")
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_user(request: Request, username: str = Form(...), password: str = Form(...)):
    if username in users_db:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists"})
    
    users_db[username] = password
    return RedirectResponse("/", status_code=303)

# Route for creating a new post ("/new_post")
@app.get("/new_post")
async def new_post_form(request: Request):
    session_user = request.cookies.get("session")
    if not session_user:
        return RedirectResponse("/")
    
    return templates.TemplateResponse("new_post.html", {"request": request})

@app.post("/new_post")
async def new_post(request: Request, title: str = Form(...), content: str = Form(...)):
    session_user = request.cookies.get("session")
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Insert post into Supabase
    try:
        response = supabase.table("Posts").insert({
            "title": title,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        if response.data is not None and len(response.data) > 0:
            return RedirectResponse("/posts", status_code=303)
        else:
            raise HTTPException(status_code=500, detail="Failed to create post")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/like_post/{post_id}")
async def like_post(post_id: int, request: Request):
    # Check if the user is logged in (optional)
    session_user = request.cookies.get("session")
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Fetch the post from Supabase
    post = supabase.table("Posts").select("*").eq("id", post_id).execute().data
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Increment the like count
    updated_post = supabase.table("Posts").update({
        "likes": post[0]["likes"] + 1
    }).eq("id", post_id).execute()

    if updated_post.data is not None and len(updated_post.data) > 0:
        return updated_post.data[0]  # Return the updated post data

    raise HTTPException(status_code=500, detail="Failed to like post")

# Route for logging out ("/logout")
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()  # Clear the session
    return RedirectResponse("/", status_code=303)
