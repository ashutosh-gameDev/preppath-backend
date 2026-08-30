"""
Study tools registry. Per the brief, v1 ships the architecture (this
endpoint + a `component_key` the frontend maps to a component) rather than
building every tool - only the Study Timer is actually implemented in v1.
Adding a new tool later is a matter of appending to this list and adding the
matching frontend component; no backend/schema change needed.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/tools", tags=["tools"])

TOOLS = [
    {
        "key": "study-timer",
        "name": "Study Timer",
        "description": "Track focused study sessions with a simple stopwatch.",
        "icon": "timer",
        "available": True,
    },
    {
        "key": "pomodoro",
        "name": "Pomodoro Timer",
        "description": "25/5 focus-break cycles.",
        "icon": "clock",
        "available": False,
    },
    {
        "key": "calculator",
        "name": "Calculator",
        "description": "Quick calculations while practicing quant.",
        "icon": "calculator",
        "available": False,
    },
    {
        "key": "notes",
        "name": "Notes",
        "description": "Jot down quick notes per topic.",
        "icon": "notebook",
        "available": False,
    },
    {
        "key": "flashcards",
        "name": "Flashcards",
        "description": "Spaced-repetition flashcards.",
        "icon": "layers",
        "available": False,
    },
    {
        "key": "study-planner",
        "name": "Study Planner",
        "description": "Plan your week across subjects.",
        "icon": "calendar",
        "available": False,
    },
]


@router.get("")
def list_tools():
    return TOOLS
