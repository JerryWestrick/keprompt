#!/usr/bin/env python3
import sys, json
from typing import Any, Dict
from playwright.sync_api import sync_playwright

FUNCTIONS = [
    {
        "name": "render_url_to_markdown",
        "description": (
            "Render a web page in a real browser and return the visible content "
            "as markdown-like text. Use this when you need to read or summarize "
            "a web page, especially if it is heavy in JavaScript."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the page to render and read"
                },
                "selector": {
                    "type": "string",
                    "description": (
                        "Optional CSS selector to focus on (defaults to article/main/body)."
                    )
                }
            },
            "required": ["url"],
            "additionalProperties": False
        }
    }
]

def list_functions():
    print(json.dumps(FUNCTIONS))

def render_url_to_markdown(args: Dict[str, Any]):
    url = args["url"]
    selector = args.get("selector")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)

        # heuristic: pick a useful container if selector not provided
        if not selector:
            for s in ["article", "main", "#docs-content", "body"]:
                try:
                    if page.query_selector(s):
                        selector = s
                        break
                except Exception:
                    continue
            if not selector:
                selector = "body"

        el = page.locator(selector)
        html = el.inner_html()

        from markdownify import markdownify as md
        markdown = md(html)

        browser.close()

    result = {
        "markdown": markdown,
        "url": url,
        "selector": selector,
    }
    print(json.dumps(result))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: browser_tool --list-functions | render_url_to_markdown", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--list-functions":
        list_functions()
        sys.exit(0)

    cmd = sys.argv[1]
    raw = sys.stdin.read().strip() or "{}"
    args = json.loads(raw) if raw else {}

    if cmd == "render_url_to_markdown":
        render_url_to_markdown(args)
    else:
        print(json.dumps({"error": f"Unknown function {cmd}"}))
        sys.exit(1)
