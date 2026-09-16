description = [{
    "description": "Search the web using Claude's native, server-side web search tool, "
    "Returns a short "
    "text summary with citations rather than raw scraped pages.",
    "name": "web_search_claude",
    "optional_parameters": [
        {
            "default": 2,
            "description": "Maximum number of searches Claude may perform for this "
            "query before the API itself rejects further searches "
            "(max_uses_exceeded).",
            "name": "max_uses",
            "type": "int",
        }
    ],
    "required_parameters": [
        {
            "default": None,
            "description": "The search query or question to look up.",
            "name": "query",
            "type": "str",
        }
    ],
},]