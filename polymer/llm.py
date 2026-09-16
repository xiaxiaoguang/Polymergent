import os
import re
from functools import cache
from typing import TYPE_CHECKING, Literal, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

if TYPE_CHECKING:
    from polymer.config import PolymerConfig

SourceType = Literal["OpenAI", "AzureOpenAI", "Anthropic", "Ollama", "Gemini", "Bedrock", "Groq", "Custom"]
ALLOWED_SOURCES: set[str] = set(SourceType.__args__)

# Output budget per call (thinking + visible text). Claude Opus 5 / Sonnet 5 think by default,
# so the old 8192 cap could be spent on thinking before any <execute> block is written.
ANTHROPIC_MAX_TOKENS = 40000


# ---------------------------------------------------------------------------
# Model capability helpers
# ---------------------------------------------------------------------------
def _is_openai_reasoning_model(model: str) -> bool:
    """gpt-5*, gpt-6*, ... and o1/o3/o4*: Responses API, no temperature/top_p, no `stop`."""
    name = model.lower()
    m = re.match(r"gpt-(\d+)", name)
    return bool((m and int(m.group(1)) >= 5) or re.match(r"o\d", name))


def _claude_rejects_sampling(model: str) -> bool:
    """Claude Opus 4.7+, Sonnet 5+, and 5.x models return 400 for non-default temperature/top_p/top_k.
    Older Claude models accept them, but omitting is always safe, so we omit for every Claude model."""
    return "claude" in model.lower()


def _normalize_agent_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Make Polymer's text-tag loop valid for current chat APIs.

    Polymer stores tool output as AIMessage("<observation>...</observation>"). That (1) looks to the
    model like text it wrote itself and (2) leaves an assistant message last, which is an assistant
    *prefill*: Claude rejects prefill when thinking is on (default on Opus 5 / Sonnet 5) and on Opus 4.7+.
    Only the outgoing request is changed; Polymer's own state/logs are untouched.
    """
    out: list[BaseMessage] = []
    for m in messages:
        if (
            isinstance(m, AIMessage)
            and not m.tool_calls
            and isinstance(m.content, str)
            and m.content.lstrip().startswith("<observation>")
        ):
            m = HumanMessage(content=m.content)
        out.append(m)
    if out and isinstance(out[-1], AIMessage) and not out[-1].tool_calls:
        out.append(HumanMessage(content="Continue."))
    return out


@cache
def _agent_safe(cls: type) -> type:
    """Subclass a LangChain chat model so every request goes through _normalize_agent_messages."""

    class _AgentSafe(cls):  # type: ignore[misc, valid-type]
        def _get_request_payload(self, input_, *, stop=None, **kwargs):  # type: ignore[override]
            messages = _normalize_agent_messages(self._convert_input(input_).to_messages())
            return super()._get_request_payload(messages, stop=stop, **kwargs)

    _AgentSafe.__name__ = cls.__name__
    _AgentSafe.__qualname__ = cls.__qualname__
    return _AgentSafe


def get_llm(
    model: str | None = None,
    temperature: float | None = None,
    stop_sequences: list[str] | None = None,
    source: SourceType | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    config: Optional["PolymerConfig"] = None,
    reasoning_effort: str | None = None,
) -> BaseChatModel:
    """
    Get a language model instance based on the specified model name and source.
    This function supports models from OpenAI, Azure OpenAI, Anthropic, Ollama, Gemini, Bedrock, and custom model serving.
    Args:
        model (str): The model name to use
        temperature (float): Temperature for models that still accept it. Ignored for Claude models and
                             OpenAI reasoning models (gpt-5+, o-series), which reject non-default values.
        stop_sequences (list): Sequences that will stop generation (not supported by OpenAI's Responses API;
                               A1 halts client-side for those models)
        source (str): Source provider: "OpenAI", "AzureOpenAI", "Anthropic", "Ollama", "Gemini", "Bedrock", or "Custom"
                      If None, will attempt to auto-detect from model name
        base_url (str): The base URL for custom model serving (e.g., "http://localhost:8000/v1"), default is None
        api_key (str): The API key for the custom llm
        config (PolymerConfig): Optional configuration object. If provided, unspecified parameters will use config values
        reasoning_effort (str): Optional effort for Claude ("low" | "medium" | "high" | "xhigh" | "max") or
                                OpenAI reasoning models ("none" | "low" | "medium" | "high" | "xhigh" | "max").
                                Falls back to the POLYMER_REASONING_EFFORT env var; None = provider default.
    """
    # Use config values for any unspecified parameters
    if config is not None:
        if model is None:
            model = config.llm_model
        if temperature is None:
            temperature = config.temperature
        if source is None:
            source = config.source
        if base_url is None:
            base_url = config.base_url
        if api_key is None:
            api_key = config.api_key or "EMPTY"
        if reasoning_effort is None:
            reasoning_effort = getattr(config, "reasoning_effort", None)

    # Use defaults if still not specified
    if model is None:
        model = "claude-sonnet-5"
    if temperature is None:
        temperature = 0.7
    if api_key is None:
        api_key = "EMPTY"
    if reasoning_effort is None:
        reasoning_effort = os.getenv("POLYMER_REASONING_EFFORT") or None

    # Auto-detect source from model name if not specified
    if source is None:
        env_source = os.getenv("LLM_SOURCE")
        if env_source in ALLOWED_SOURCES:
            source = env_source
        else:
            if model[:7] == "claude-":
                source = "Anthropic"
            elif model[:7] == "gpt-oss":
                source = "Ollama"
            elif model[:4] == "gpt-" or re.match(r"o\d", model):
                source = "OpenAI"
            elif model.startswith("azure-"):
                source = "AzureOpenAI"
            elif model[:7] == "gemini-":
                source = "Gemini"
            elif "groq" in model.lower():
                source = "Groq"
            elif base_url is not None:
                source = "Custom"
            elif "/" in model or any(
                name in model.lower()
                for name in [
                    "llama",
                    "mistral",
                    "qwen",
                    "gemma",
                    "phi",
                    "dolphin",
                    "orca",
                    "vicuna",
                    "deepseek",
                ]
            ):
                source = "Ollama"
            elif model.startswith(
                ("anthropic.claude-", "amazon.titan-", "meta.llama-", "mistral.", "cohere.", "ai21.", "us.")
            ):
                source = "Bedrock"
            else:
                raise ValueError("Unable to determine model source. Please specify 'source' parameter.")

    # Create appropriate model based on source
    if source == "OpenAI":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(  # noqa: B904
                "langchain-openai package is required for OpenAI models. Install with: pip install -U langchain-openai"
            )
        ChatOpenAI = _agent_safe(ChatOpenAI)  # noqa: N806

        if _is_openai_reasoning_model(model):
            # gpt-5.x / gpt-6.x / o-series: Responses API. Do not send temperature/top_p (400 on
            # gpt-6-astra and non-"none" effort gpt-5.x). The Responses API has no `stop`;
            # langchain-openai drops it, and A1.generate halts at </execute> client-side.
            kwargs = {"reasoning": {"effort": reasoning_effort}} if reasoning_effort else {}
            return ChatOpenAI(
                model=model,
                stop_sequences=stop_sequences,
                use_responses_api=True,
                output_version="v0",
                **kwargs,
            )
        else:
            # Non-reasoning models (gpt-4o, gpt-4.1, ...) on Chat Completions: temperature and stop work.
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                stop_sequences=stop_sequences,
            )

    elif source == "AzureOpenAI":
        try:
            from langchain_openai import AzureChatOpenAI
        except ImportError:
            raise ImportError(  # noqa: B904
                "langchain-openai package is required for Azure OpenAI models. Install with: pip install -U langchain-openai"
            )
        API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-12-01-preview")
        model = model.replace("azure-", "")
        kwargs = {} if _is_openai_reasoning_model(model) else {"temperature": temperature}
        return _agent_safe(AzureChatOpenAI)(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
            azure_deployment=model,
            openai_api_version=API_VERSION,
            **kwargs,
        )

    elif source == "Anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(  # noqa: B904
                "langchain-anthropic package is required for Anthropic models. Install with: pip install -U langchain-anthropic"
            )

        # Ensure ANTHROPIC_API_KEY is loaded from bash_profile if not in environment
        if not os.environ.get("ANTHROPIC_API_KEY"):
            try:
                import subprocess

                result = subprocess.run(
                    ["bash", "-c", "source ~/.bash_profile 2>/dev/null && echo $ANTHROPIC_API_KEY"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.stdout.strip():
                    os.environ["ANTHROPIC_API_KEY"] = result.stdout.strip()
                    print("✓ Loaded ANTHROPIC_API_KEY from ~/.bash_profile")
            except Exception as e:
                print(f"Note: Could not load ANTHROPIC_API_KEY from bash_profile: {e}")

        # No temperature: current Claude models reject non-default sampling params.
        # Thinking is left at the model default (adaptive on Opus 5 / Sonnet 5); stop_sequences still work.
        model_kwargs = {"output_config": {"effort": reasoning_effort}} if reasoning_effort else {}
        return _agent_safe(ChatAnthropic)(
            model=model,
            max_tokens=ANTHROPIC_MAX_TOKENS,
            stop_sequences=stop_sequences,
            model_kwargs=model_kwargs,
        )

    elif source == "Gemini":
        # If you want to use ChatGoogleGenerativeAI, you need to pass the stop sequences upon invoking the model.
        # return ChatGoogleGenerativeAI(
        #     model=model,
        #     temperature=temperature,
        #     google_api_key=api_key,
        # )
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(  # noqa: B904
                "langchain-openai package is required for Gemini models. Install with: pip install langchain-openai"
            )
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            stop_sequences=stop_sequences,
        )

    elif source == "Groq":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(  # noqa: B904
                "langchain-openai package is required for Groq models. Install with: pip install langchain-openai"
            )
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
            stop_sequences=stop_sequences,
        )

    elif source == "Ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError(  # noqa: B904
                "langchain-ollama package is required for Ollama models. Install with: pip install langchain-ollama"
            )
        return ChatOllama(
            model=model,
            temperature=temperature,
        )

    elif source == "Bedrock":
        try:
            from langchain_aws import ChatBedrock
        except ImportError:
            raise ImportError(  # noqa: B904
                "langchain-aws package is required for Bedrock models. Install with: pip install langchain-aws"
            )
        kwargs = {} if _claude_rejects_sampling(model) else {"temperature": temperature}
        return ChatBedrock(
            model=model,
            stop_sequences=stop_sequences,
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            **kwargs,
        )

    elif source == "Custom":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(  # noqa: B904
                "langchain-openai package is required for custom models. Install with: pip install langchain-openai"
            )
        # Custom LLM serving such as SGLang. Must expose an openai compatible API.
        assert base_url is not None, "base_url must be provided for customly served LLMs"
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=8192,
            stop_sequences=stop_sequences,
            base_url=base_url,
            api_key=api_key,
        )
        return llm

    else:
        raise ValueError(
            f"Invalid source: {source}. Valid options are 'OpenAI', 'AzureOpenAI', 'Anthropic', 'Gemini', 'Groq', 'Bedrock', or 'Ollama'"
        )