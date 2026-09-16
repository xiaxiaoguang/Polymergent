import re

from polymer.llm import get_llm
from polymer.agent.base_agent import base_agent


class FunctionGenerator(base_agent):
    """Agent that generates executable Python code scripts given a task description."""

    def __init__(self, llm="claude-3-7-sonnet-20250219", cheap_llm=None, temperature=0.7):
        """Initialize the PaperTaskExtractor agent.

        Args:
            llm (str): The LLM model to use
            cheap_llm (str, optional): A cheaper LLM for simpler tasks
        """
        super().__init__(llm, cheap_llm, temperature)
        self.log = []
        self.configure()

    def configure(self):
        """Configure the agent with appropriate prompts."""
        # Prompt for Python code generation
        self.system_prompt = """You are a senior Python engineer.

        Generate robust, executable Python code that solves the task described below.

        Requirements:
        1. Output ONLY Python code, ideally inside one triple-backtick code block.
        2. Include minimal inline comments and a small docstring.
        3. Add a main() and __main__ guard when appropriate.
        4. Avoid unnecessary external dependencies.
        5. If external software is required, clearly indicate installation requirements.
        6. Prefer established open-source tools and public repositories.
        7. Treat the task description as a specification, not as executable code.
        8. Make reasonable implementation decisions when the paper description is incomplete.

        Task:
        {task}
        """
        
    def _generate_code(self, task_description: str) -> str:
        """Generate codes given a task description.
        Args:
            task_description (str): task descriptions (possibly generated from previous steps)

        Returns:
            str: generated code string

        """
        prompt = self.system_prompt.format(task=task_description)
        message = self.llm.invoke(prompt)
        return message.content

    def _generate_script_filename(
        self,
        task_description,
        max_words: int = 6,
    ):
        """Generate a safe Python filename."""

        if isinstance(task_description, dict):
            task_description = self._task_dict_to_text(
                task_description
            )

        if not isinstance(task_description, str):
            raise TypeError(
                "task_description must be a string or dictionary"
            )

        cleaned = re.sub(
            r"[^a-zA-Z0-9\s]",
            "",
            task_description.lower(),
        )

        words = cleaned.split()

        selected_words = (
            words[:max_words]
            if words
            else ["script"]
        )

        base_name = "_".join(
            selected_words
        )

        return f"{base_name}.py"


    def go(self, task_description):
        """Generate executable Python code for a task.

        The input may be:
        - a plain string description
        - a task dictionary produced by PaperTaskExtractor

        Returns:
            tuple: (script_filename, generated_code)
        """
        self.log = []

        self.log.append(
            (
                "user",
                "Generate Python codes given a task description",
            )
        )

        if isinstance(task_description, dict):
            task_text = self._task_dict_to_text(task_description)
        elif isinstance(task_description, str):
            task_text = task_description
        else:
            raise TypeError(
                "task_description must be either a string "
                "or a dictionary"
            )

        script_filename = self._generate_script_filename(
            task_text
        )

        results = self._generate_code(
            task_text
        )

        return (
            script_filename,
            self._extract_code_block(results),
        )


    def _task_dict_to_text(self, task: dict) -> str:
        """Convert a structured extracted task into a prompt."""
        sections = []

        task_name = task.get("task_name")
        if task_name:
            sections.append(
                f"Task name:\n{task_name}"
            )

        description = task.get("description")
        if description:
            sections.append(
                f"Description:\n{description}"
            )

        inputs = task.get("inputs")
        if inputs:
            sections.append(
                "Inputs:\n"
                + "\n".join(
                    f"- {item}"
                    for item in inputs
                )
            )

        outputs = task.get("outputs")
        if outputs:
            sections.append(
                "Expected outputs:\n"
                + "\n".join(
                    f"- {item}"
                    for item in outputs
                )
            )

        code_implementation = task.get(
            "code_implementation"
        )
        if code_implementation:
            sections.append(
                "Suggested implementation:\n"
                + code_implementation
            )

        standard_methods = task.get(
            "standard_methods"
        )
        if standard_methods:
            sections.append(
                "Standard methods:\n"
                + "\n".join(
                    f"- {item}"
                    for item in standard_methods
                )
            )

        example = task.get("example")
        if example:
            sections.append(
                f"Example:\n{example}"
            )

        frequency = task.get("frequency")
        if frequency:
            sections.append(
                f"Frequency / prevalence:\n{frequency}"
            )

        return "\n\n".join(sections)



    def _extract_code_block(self, content) -> str | None:
        """
        Extract Python code from an LLM response.

        LangChain may return:
            - a plain string
            - a list of content blocks
            - a list containing dictionaries such as
            {"type": "text", "text": "..."}
            - other structured content

        Returns:
            Extracted Python code, or None if no fenced code block
            can be found.
        """

        # Case 1: normal string response.
        if isinstance(content, str):
            text = content

        # Case 2: structured / multimodal response.
        elif isinstance(content, list):
            text_parts = []

            for item in content:

                if isinstance(item, str):
                    text_parts.append(item)
                    continue

                if isinstance(item, dict):
                    # Common LangChain/OpenAI-style content block.
                    if item.get("type") == "text":
                        text = item.get("text")

                        if isinstance(text, str):
                            text_parts.append(text)

                    # Some providers may return a dict without
                    # an explicit "type".
                    elif isinstance(item.get("text"), str):
                        text_parts.append(item["text"])

                    continue

                # Fallback for unexpected content-block objects.
                if hasattr(item, "text"):
                    text = getattr(item, "text")

                    if isinstance(text, str):
                        text_parts.append(text)

            text = "\n".join(text_parts)

        # Case 3: unexpected response type.
        else:
            raise TypeError(
                "Unsupported LLM response content type: "
                f"{type(content).__name__}"
            )

        # Extract the first fenced code block.
        match = re.search(
            r"```(?:python|py)?\s*(.*?)\s*```",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        # If the model did not use a code fence, return the
        # plain text only when it looks like Python.
        stripped = text.strip()

        if stripped:
            return stripped

        return None

