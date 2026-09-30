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
},
{
    "description": "Fetch a single scientific paper by URL (or bare DOI) using Claude's "
    "native server-side web fetch. Use this after web_search_claude or a "
    "datalake hit gives you an arXiv, DOI, Science, Nature, ACS, Elsevier, "
    "or other journal link. Returns extracted paper text (title, abstract, "
    "methods, numbers). Does not accept keyword queries — pass one http(s) "
    "URL only.",
    "name": "fetch_paper_url",
    "optional_parameters": [
        {
            "default": 1,
            "description": "Maximum number of fetches Claude may perform for this "
            "URL before the API itself rejects further fetches "
            "(max_uses_exceeded).",
            "name": "max_uses",
            "type": "int",
        }
    ],
    "required_parameters": [
        {
            "default": None,
            "description": "Full paper URL (https://arxiv.org/abs/..., "
            "https://doi.org/..., https://www.science.org/...) or a bare "
            "DOI such as 10.1126/science.xxxx. Not a search phrase.",
            "name": "url",
            "type": "str",
        }
    ],
},]