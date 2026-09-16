"""Loader for know-how documents."""

import glob
import os
from pathlib import Path


class KnowHowLoader:
    """Load and manage know-how documents for the agent."""

    def __init__(self, know_how_dir: str | None = None):
        """Initialize the know-how loader.

        Args:
            know_how_dir: Directory containing know-how documents.
                         If None, uses the default know_how directory.

        """
        if know_how_dir is None:
            current_dir = Path(__file__).parent
            know_how_dir = str(current_dir)

        self.know_how_dir = know_how_dir
        self.documents = {}
        self._load_documents()

    def _load_documents(self):
        """Load all markdown documents from the know-how directory."""
        pattern = os.path.join(self.know_how_dir, "*.md")
        md_files = glob.glob(pattern)

        for filepath in md_files:
            filename = os.path.basename(filepath)
            filename_without_ext = os.path.splitext(filename)[0]

            if filename.upper() in ["README.MD", "QUICK_START.MD"] or filename_without_ext.isupper():
                continue

            with open(filepath) as f:
                content = f.read()

            title, description, metadata = self._extract_metadata(content, filename)

            if "short_description" in metadata and metadata["short_description"]:
                description = metadata["short_description"]

            doc_id = os.path.splitext(filename)[0]
            self.documents[doc_id] = {
                "id": doc_id,
                "name": title,
                "description": description,
                "content": content,
                "content_without_metadata": self._strip_metadata(content),
                "filepath": filepath,
                "metadata": metadata,
            }

    def _extract_metadata(self, content: str, filename: str) -> tuple[str, str, dict]:
        lines = content.split("\n")

        title = None
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        if title is None:
            title = filename.replace("_", " ").replace(".md", "").title()

        metadata = {}
        in_metadata = False
        current_field = None

        for _i, line in enumerate(lines):
            if line.startswith("## Metadata"):
                in_metadata = True
                continue
            elif in_metadata:
                if line.startswith("##") and "Metadata" not in line:
                    break
                elif line.startswith("**") and "**:" in line:
                    field_match = line.split("**")[1]
                    current_field = field_match.lower().replace(" ", "_")
                    colon_idx = line.find("**:")
                    if colon_idx != -1:
                        value_part = line[colon_idx + 3 :].strip()
                        if value_part:
                            metadata[current_field] = value_part
                        else:
                            metadata[current_field] = ""
                elif current_field and line.strip() and not line.startswith("---"):
                    if current_field not in metadata:
                        metadata[current_field] = ""
                    if line.startswith("- "):
                        if metadata[current_field]:
                            metadata[current_field] += ", " + line[2:].strip()
                        else:
                            metadata[current_field] = line[2:].strip()
                    elif not line.startswith("```"):
                        if metadata[current_field]:
                            metadata[current_field] += " " + line.strip()
                        else:
                            metadata[current_field] = line.strip()

        description = ""
        in_overview = False
        overview_lines = []

        for _i, line in enumerate(lines):
            if line.startswith("## Overview"):
                in_overview = True
                continue
            elif in_overview:
                if line.startswith("##"):
                    break
                elif line.strip():
                    overview_lines.append(line.strip())

        if overview_lines:
            description = " ".join(overview_lines)
        else:
            found_title = False
            for line in lines:
                if line.startswith("# "):
                    found_title = True
                    continue
                if found_title and line.strip() and not line.startswith("#"):
                    description = line.strip()
                    break

        if len(description) > 200:
            description = description[:197] + "..."

        return title, description, metadata

    def _strip_metadata(self, content: str) -> str:
        lines = content.split("\n")
        result_lines = []
        in_metadata = False
        skip_until_separator = False
        found_first_h1 = False

        for line in lines:
            if line.startswith("# ") and not found_first_h1:
                result_lines.append(line)
                found_first_h1 = True
                continue

            if line.startswith("## Metadata"):
                in_metadata = True
                continue

            if line.strip() == "---":
                if not in_metadata:
                    skip_until_separator = True
                    continue
                else:
                    in_metadata = False
                    skip_until_separator = False
                    continue

            if in_metadata or skip_until_separator:
                if line.startswith("##") and "Metadata" not in line:
                    in_metadata = False
                    skip_until_separator = False
                    result_lines.append(line)
                continue

            result_lines.append(line)

        result = "\n".join(result_lines)
        while "\n\n\n\n" in result:
            result = result.replace("\n\n\n\n", "\n\n\n")
        return result.strip()

    def get_all_documents(self) -> list[dict]:
        return list(self.documents.values())

    def get_document_by_id(self, doc_id: str) -> dict | None:
        return self.documents.get(doc_id)

    def get_document_summaries(self) -> list[dict]:
        return [
            {"id": doc["id"], "name": doc["name"], "description": doc["description"]}
            for doc in self.documents.values()
        ]

    def add_custom_document(self, doc_id: str, name: str, description: str, content: str, metadata: dict | None = None):
        if metadata is None:
            metadata = {}
        self.documents[doc_id] = {
            "id": doc_id,
            "name": name,
            "description": description,
            "content": content,
            "filepath": None,
            "metadata": metadata,
        }

    def get_document_metadata(self, doc_id: str) -> dict | None:
        doc = self.documents.get(doc_id)
        return doc.get("metadata", {}) if doc else None

    def print_document_info(self, doc_id: str):
        doc = self.documents.get(doc_id)
        if not doc:
            print(f"Document '{doc_id}' not found")
            return
        print("=" * 70)
        print(f"📚 {doc['name']}")
        print("=" * 70)
        print(f"\nDescription: {doc['description']}")

    def remove_document(self, doc_id: str):
        if doc_id in self.documents:
            del self.documents[doc_id]

    def reload(self):
        self.documents = {}
        self._load_documents()