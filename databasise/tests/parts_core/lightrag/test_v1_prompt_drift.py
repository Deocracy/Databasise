"""D-16 drift guard: every v1 prompt string the LightRAG query parts duplicate equals the constant
``v1/lightrag/prompt.py`` assigns to ``PROMPTS[name]``, read with ``ast`` (lightrag is never
imported, per ``tools/check_import_boundary.py``).
"""

from __future__ import annotations

import ast
from pathlib import Path

from databasise.parts_core.lightrag import keywords
from databasise.parts_core.lightrag.prompts import PROMPTS

_V1_PROMPT_PY = Path(__file__).resolve().parents[4] / "v1" / "lightrag" / "prompt.py"
_DUPLICATED = {
    "fail_response",
    "rag_response",
    "naive_rag_response",
    "kg_query_context",
    "naive_query_context",
    "keywords_extraction",
}


def _v1_prompt_constants() -> dict[str, str]:
    tree = ast.parse(_V1_PROMPT_PY.read_text(encoding="utf-8"))
    found: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id == "PROMPTS"
            and isinstance(target.slice, ast.Constant)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            found[target.slice.value] = node.value.value
    return found


def test_the_duplicated_prompt_set_is_exactly_the_six_query_prompts():
    assert set(PROMPTS) == _DUPLICATED


def test_every_duplicated_prompt_is_byte_identical_to_v1():
    v1 = _v1_prompt_constants()
    for name, text in PROMPTS.items():
        assert name in v1, name
        assert text == v1[name], name


def test_the_keyword_extractor_sends_v1s_keywords_extraction_prompt():
    assert keywords._KEYWORDS_EXTRACTION_PROMPT == _v1_prompt_constants()["keywords_extraction"]
