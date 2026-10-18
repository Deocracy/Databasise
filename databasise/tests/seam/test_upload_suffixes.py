"""11-05 Task 1 (LRAG-08, D-09): a raw upload keeps only a validated suffix from ``file_name``, the
one v1's parser routing needs. The accepted set is pinned to v1's own ``_LEGACY_SUFFIXES`` literal,
read with ``ast`` (lightrag is never imported here)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from databasise.seam.corpus import (
    ACCEPTED_UPLOAD_SUFFIXES,
    generated_on_disk_name,
    upload_suffix,
)
from databasise.seam.refusals import UnsupportedUploadTypeError

_V1_REGISTRY = Path(__file__).resolve().parents[3] / "v1" / "lightrag" / "parser" / "registry.py"


def _v1_legacy_suffixes() -> set[str]:
    for node in ast.walk(ast.parse(_V1_REGISTRY.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_LEGACY_SUFFIXES" for t in node.targets
        ):
            return {elt.value for elt in node.value.args[0].elts}  # frozenset({...})
    raise AssertionError("_LEGACY_SUFFIXES not found in v1/lightrag/parser/registry.py")


def test_the_accepted_suffixes_match_v1s_legacy_parser_suffixes():
    # textpack routes to the native engine by default, so it is never an accepted upload type.
    assert ACCEPTED_UPLOAD_SUFFIXES == {f".{s}" for s in _v1_legacy_suffixes() - {"textpack"}}


@pytest.mark.parametrize(
    ("file_name", "suffix"),
    [
        ("../a.PDF", ".pdf"),
        ("a.[mineru].pdf", ".pdf"),
        ("..\\..\\x.TXT", ".txt"),
        ("notes.md", ".md"),
        ("dir/sub/report.docx", ".docx"),
    ],
)
def test_upload_suffix_keeps_only_the_lower_cased_basename_suffix(file_name, suffix):
    assert upload_suffix(file_name) == suffix
    assert "[" not in generated_on_disk_name("doc1", upload_suffix(file_name))


@pytest.mark.parametrize(
    ("file_name", "suffix"),
    [(None, ""), ("", ""), ("README", ""), ("notes.xyz", ".xyz"), ("a.textpack", ".textpack"), ("x.", "")],
)
def test_an_unsupported_or_missing_suffix_is_refused_by_name(file_name, suffix):
    with pytest.raises(UnsupportedUploadTypeError) as exc_info:
        upload_suffix(file_name)
    assert exc_info.value.suffix == suffix


@pytest.mark.parametrize("file_name", ["a.p df", "a.toolongsuffix", "a.pdf\n", "a.pdfé"])
def test_a_suffix_that_is_not_a_plain_token_is_refused_without_echoing_it(file_name):
    with pytest.raises(UnsupportedUploadTypeError) as exc_info:
        upload_suffix(file_name)
    assert exc_info.value.suffix == ""


def test_generated_on_disk_name_keeps_bin_by_default_and_takes_a_suffix():
    assert generated_on_disk_name("a_kiss-for_corliss") == "a_kiss-for_corliss.bin"
    assert generated_on_disk_name("x", ".txt") == "x.txt"
