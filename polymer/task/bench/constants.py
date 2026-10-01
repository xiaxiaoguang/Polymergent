DATASETS = (
    "KnowledgeQA",
    "StructQA",
    "ProtocolQA",
    "PropQA",
    "DbQA",
    "MmQA",
    "SynthesisDesign",
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
    "propertyqa": "PropQA",
    "propertyprediction": "PropQA",
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
    "synthesisdesign": "SynthesisDesign",
    "all": "All",
}

ANSWER_TYPE_ALIASES = {
    "numeric": "exactMatch",
    "number": "exactMatch",
}

REFRAIN_TEXT = "Insufficient information to answer the question."

EXTRA_TASK_FILES = (
    "tasks.json",
    "tasks2.json",
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

TASK_VIEW_FILES = (
    "tasks_knowledge_reasoning.json",
    "tasks_material_identification.json",
    "tasks_property_prediction.json",
    "tasks_reaction_and_design.json",
    "tasks_structure_reasoning.json",
    "tasks_synthesis_protocol.json",
    "tasks_level_1.json",
    "tasks_level_2.json",
    "tasks_level_3.json",
    "tasks_level_4.json",
)

TASK_FAMILY_VIEW_FILES = TASK_VIEW_FILES[:6]
TASK_DIFFICULTY_VIEW_FILES = TASK_VIEW_FILES[6:]


def normalize_category(value: str | None) -> str | None:
    if value is None:
        return None
    key = str(value).strip()
    return CATEGORY_ALIASES.get(key.lower(), key)


def normalize_answer_type(value: str | None) -> str | None:
    if value is None:
        return None
    key = str(value).strip()
    if key in ANSWER_TYPES:
        return key
    return ANSWER_TYPE_ALIASES.get(key.lower(), key)
