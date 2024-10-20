from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client
from dotenv import load_dotenv
import os

app = FastAPI()

load_dotenv()
url = os.getenv("URL")
key = os.getenv("KEY")

app.mount(
    "/static/",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(
    directory="templates"
)
supabase: Client = create_client(url, key)

@app.get('/')
async def read_posts(request: Request):
    response = supabase.table("Posts").select("*").order("created_at", desc=True).execute()
    posts = response.data
    return templates.TemplateResponse("index.html", {"request" : request, "posts" : posts})

@app.get('/new')
async def new_post_form(request: Request):
    return templates.TemplateResponse("new_post.html", {"request" : request})

@app.get('/contact')
async def new_post_form(request: Request):
    return templates.TemplateResponse("contact.html", {"request" : request})

@app.get('/about')
async def new_post_form(request: Request):
    return templates.TemplateResponse("about.html", {"request" : request})

@app.get('/post/{post_id}')
async def get_post(request: Request, post_id: int):
    response = supabase.from_("Posts").select("*").eq("id", post_id).single().execute()
    post = response.data

    if not post:
        raise HTTPException(status_code=404, detail="post not found!")
    
    return templates.TemplateResponse("post_detail.html", {"request" : request, "post" : post})

@app.post('/create')
async def create_post(title: str = Form(...), content: str = Form(...)):
    supabase.table("Posts").insert({"title" : title, "content" : content}).execute()
    return RedirectResponse("/", status_code=303)