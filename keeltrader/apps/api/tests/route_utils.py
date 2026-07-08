"""Helpers for route contract tests across FastAPI/Starlette versions."""

from __future__ import annotations


def route_paths(app) -> set[str]:
    """Return visible route paths, recursively expanding mounted routers."""
    paths: set[str] = set()
    seen: set[int] = set()

    def join_paths(prefix: str, path: str) -> str:
        if not prefix:
            return path or ""
        if not path or path == "/":
            return prefix
        return f"{prefix.rstrip('/')}/{path.lstrip('/')}"

    def visit_routes(routes, prefix: str = "") -> None:
        for route in routes:
            route_id = id(route)
            if route_id in seen:
                continue
            seen.add(route_id)

            raw_path = getattr(route, "path", "")
            current_path = join_paths(prefix, raw_path)
            if current_path:
                paths.add(current_path)

            include_context = getattr(route, "include_context", None)
            original_router = getattr(route, "original_router", None)
            original_routes = getattr(original_router, "routes", None)
            if include_context is not None and original_routes is not None:
                include_prefix = getattr(include_context, "prefix", "")
                visit_routes(original_routes, join_paths(prefix, include_prefix))

            app_routes = getattr(getattr(route, "app", None), "routes", None)
            if app_routes is not None:
                visit_routes(app_routes, current_path)

            child_routes = getattr(route, "routes", None)
            if child_routes is not None:
                visit_routes(child_routes, prefix)

    visit_routes(getattr(app, "routes", []))
    return paths
