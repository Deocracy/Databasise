"""Spike 007: prompt designs under test. Pure text transforms, no model.

All exact strings live here so the README and the logs can quote them byte for byte.
Embedder-side designs follow the Qwen3-Embedding documented convention:
queries wrapped as "Instruct: <instruction>\\nQuery: <query>", documents bare.
Generative-side designs vary doc_prefix (SCORE-IO-SPEC section 4, `P`) and the
trailing marker/suffix read with LAST pooling on MiniCPM5-2B.
"""

MARKER = "\u27e6EMB\u27e7"  # literal fallback marker per SCORE-IO-SPEC section 2

# --- instruction strings (query side, embedder) ---
VENDOR_INSTR = ("Given a web search query, retrieve relevant passages "
                "that answer the query")
TASK_INSTR = ("Given a question about films and the people who made them, "
              "retrieve the passage that answers the question")
WRONG_INSTR = ("Given a code search query, retrieve relevant code snippets "
               "that implement the required functionality")


def instruct_query(instr: str, q: str) -> str:
    return f"Instruct: {instr}\nQuery: {q}"


def vendor_q(q: str) -> str:
    return instruct_query(VENDOR_INSTR, q)


def task_q(q: str) -> str:
    return instruct_query(TASK_INSTR, q)


def wrong_q(q: str) -> str:
    return instruct_query(WRONG_INSTR, q)


def instr_doc(text: str) -> str:
    """Design 5 document side: task instruction on the document too."""
    return f"Instruct: {TASK_INSTR}\nDocument: {text}"


def titled_doc(title: str, text: str) -> str:
    """Design 6 document side: explicit labelled title prefix."""
    return f"Title: {title}\n{text}"


# --- generative path (MiniCPM5-2B, LAST pooling) ---
SYSTEM_INSTR = "Represent the passage that follows for retrieval."
# Rendered system turn per the model's own chat_template.jinja
# (bos <s> + <|im_start|>system\\n{content}<|im_end|>\\n); v0.1 doc_prefix default.
SYS_PREFIX = "<s><|im_start|>system\n" + SYSTEM_INSTR + "<|im_end|>\n"
TASK_PREFIX = SYSTEM_INSTR + "\n"  # design 7 plain-instruction arm, no template


def gen_bare(text: str) -> str:
    return text + MARKER


def gen_titled(title: str, text: str) -> str:
    return titled_doc(title, text) + MARKER


def gen_sys(text: str) -> str:
    return SYS_PREFIX + text + MARKER


def gen_task(text: str) -> str:
    return TASK_PREFIX + text + MARKER


def gen_eol(text: str) -> str:
    """PromptEOL-style suffix, no marker; last-token state is read."""
    return f'This sentence: "{text}" means in one word:'


def gen_about(text: str) -> str:
    return text + " The passage is about"
