"""Tool registry — import side-effect registers each tool."""
from app.tools import entity_diff, fetch_jd, latex_compile, resume_retriever, skill_taxonomy, web_search  # noqa: F401
from app.tools.registry import Tool, ToolRegistry, registry

__all__ = ["Tool", "ToolRegistry", "registry"]
