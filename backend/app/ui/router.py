from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
ui_router = APIRouter(prefix="/ui", tags=["ui"])


@ui_router.get("", response_class=HTMLResponse)
def ui_home(request: Request):
    return templates.TemplateResponse("ui_home.html", {"request": request})
