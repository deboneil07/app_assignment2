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
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")  # Add this line

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

# Route to fetch and show all posts ("/")
@app.get("/")
async def read_posts(request: Request):
    posts = supabase.table("Posts").select("*").order("created_at", desc=True).execute().data
    return templates.TemplateResponse("index.html", {"request": request, "posts": posts})

# Route for user registration ("/register")
@app.get("/register")
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_user(request: Request, username: str = Form(...), password: str = Form(...)):
    if username in users_db:
        # Return the registration form again with an error message
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists"})
    
    # Register the new user
    users_db[username] = password
    # Redirect to login page after successful registration
    return RedirectResponse("/login", status_code=303)

# Route for user login ("/login")
@app.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Check if the user exists and the password matches
    if username not in users_db or users_db[username] != password:
        # Return login form again with an error message if authentication fails
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    
    # Successful login, redirect to homepage
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key="session", value=username)  # Set a simple session cookie
    return response

# Route for creating a new post ("/new_post")
@app.get("/new_post")
async def new_post_form(request: Request):
    session_user = request.cookies.get("session")
    if not session_user:
        # Redirect to login if not authenticated
        return RedirectResponse("/login")
    
    # Render the form for creating a new post
    return templates.TemplateResponse("new_post.html", {"request": request})


@app.post("/new_post")
async def new_post(request: Request, title: str = Form(...), content: str = Form(...)):
    session_user = request.cookies.get("session")
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Mocked user ID from session (you can fetch the user details from your user management system)
    user_id = session_user  # Assuming the session contains the user ID

    # Insert post into Supabase
    try:
        response = supabase.table("Posts").insert({
            "title": title,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),  # Convert datetime to ISO format
            # "user_id": user_id  # Assuming you want to track which user created the post
        }).execute()

        # Check if insert was successful
        if response.data is not None and len(response.data) > 0:  # Check if data is returned
            return RedirectResponse("/", status_code=303)
        else:
            raise HTTPException(status_code=500, detail="Failed to create post")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/like_post/{post_id}")
async def like_post(post_id: int, request: Request):
    session_user = request.cookies.get("session")
    if not session_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Increment the like count for the post
    try:
        # Fetch the current like count
        current_post = supabase.table("Posts").select("likes").eq("id", post_id).execute().data[0]

        # Update the like count
        new_like_count = current_post['likes'] + 1
        response = supabase.table("Posts").update({"likes": new_like_count}).eq("id", post_id).execute()

        # Check if the update was successful
        if response.data is None:
            raise HTTPException(status_code=500, detail="Failed to like post")

        # Return the updated like count
        return {"likes": new_like_count}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


# Route for logging out and redirecting to login page
@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse("/login", status_code=303)
