DATASETS = (
    "KnowledgeQA",
    "StructQA",
    "ProtocolQA",
    "PropQA",
    "DbQA",
    "MmQA",
    "All",
)

ANSWER_TYPES = ("multipleChoice", "exactMatch", "ranking")

CATEGORY_ALIASES = {
    "knowledgeqa": "KnowledgeQA",
    "knowledge": "KnowledgeQA",
    "hle": "KnowledgeQA",
    "conceptual": "KnowledgeQA",
    "conknow": "KnowledgeQA",
    "structqa": "StructQA",
    "structure": "StructQA",
    "seqqa": "StructQA",
    "strund": "StructQA",
    "mechanism": "StructQA",
    "protocolqa": "ProtocolQA",
    "protocol": "ProtocolQA",
    "safe": "ProtocolQA",
    "propqa": "PropQA",
    "property": "PropQA",
    "proppred": "PropQA",
    "propcopr": "PropQA",
    "propcompr": "PropQA",
    "rank": "PropQA",
    "ranking": "PropQA",
    "dbqa": "DbQA",
    "database": "DbQA",
    "spectrum": "DbQA",
    "spectrumqa": "DbQA",
    "table": "DbQA",
    "raw": "DbQA",
    "mmqa": "MmQA",
    "multimodal": "MmQA",
    "visionqa": "MmQA",
    "all": "All",
}

REFRAIN_TEXT = "Insufficient information to answer the question."

EXTRA_TASK_FILES = (
    "tasks.json",
    "tasks_v2.json",
    "external_tasks.json",
    "hard_tasks.json",
    "easy_passed.json",
    "tasks.jsonl",
    "test.json",
    "test.jsonl",
    "test.parquet",
    "polyreal.json",
    "PolyReal.json",
    "polybench.json",
    "polybench.jsonl",
    "polybench.parquet",
)
