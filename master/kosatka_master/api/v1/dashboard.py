from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["dashboard"])

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent.parent / "templates"))


@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Render the analytics dashboard.
    Note: Real-time data is fetched via JS from /api/v1/stats/realtime.
    Auth is handled via query param ?key=... or header in the JS fetch.
    """
    # Simple check for dashboard access if desired, but JS fetch is protected.
    return templates.TemplateResponse(request=request, name="dashboard.html")
