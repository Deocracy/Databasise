"""``hipporag/qa-reader`` — the answer-generation step of HippoRAG 2, the 14th node of this wiring
(Phase 12 D-19, HIPP-13; recorded in ``evidence/HIPPORAG-PORT-RECORD.md`` as a divergence from the
governing 13 positions). Ported from upstream ``HippoRAG.qa`` (``src/hipporag/HippoRAG.py:1117-1172``)
and its ``rag_qa_musique`` prompt template (``src/hipporag/prompts/templates/rag_qa_musique.py``),
OSU-NLP-Group/HippoRAG at commit d5c8329, MIT licence. The system text, the one-shot pair and the
"Wikipedia Title:" per-passage prefix are kept verbatim.

The node reads the hydrated passages ``assemble-result`` passes it and the query text
(``config["query"]``), sends [system, one-shot user, one-shot assistant, user] to the LLM client, and
answers the text after ``Answer:`` (the whole response when the marker is absent, as upstream does).
With no passage content it makes no call and answers ``PROMPTS["fail_response"]``, the same no-context
answer LightRAG's generator gives.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.parts_core.lightrag.prompts import PROMPTS
from databasise.runner.trace import TokenAccounting

_NAME_AT_VERSION = "hipporag/qa-reader@0.1.0"

_ONE_SHOT_DOCS = (
    """Wikipedia Title: The Last Horse\nThe Last Horse (Spanish:El último caballo) is a 1950 Spanish comedy film directed by Edgar Neville starring Fernando Fernán Gómez.\n"""
    """Wikipedia Title: Southampton\nThe University of Southampton, which was founded in 1862 and received its Royal Charter as a university in 1952, has over 22,000 students. The university is ranked in the top 100 research universities in the world in the Academic Ranking of World Universities 2010. In 2010, the THES - QS World University Rankings positioned the University of Southampton in the top 80 universities in the world. The university considers itself one of the top 5 research universities in the UK. The university has a global reputation for research into engineering sciences, oceanography, chemistry, cancer sciences, sound and vibration research, computer science and electronics, optoelectronics and textile conservation at the Textile Conservation Centre (which is due to close in October 2009.) It is also home to the National Oceanography Centre, Southampton (NOCS), the focus of Natural Environment Research Council-funded marine research.\n"""
    """Wikipedia Title: Stanton Township, Champaign County, Illinois\nStanton Township is a township in Champaign County, Illinois, USA. As of the 2010 census, its population was 505 and it contained 202 housing units.\n"""
    """Wikipedia Title: Neville A. Stanton\nNeville A. Stanton is a British Professor of Human Factors and Ergonomics at the University of Southampton. Prof Stanton is a Chartered Engineer (C.Eng), Chartered Psychologist (C.Psychol) and Chartered Ergonomist (C.ErgHF). He has written and edited over a forty books and over three hundered peer-reviewed journal papers on applications of the subject. Stanton is a Fellow of the British Psychological Society, a Fellow of The Institute of Ergonomics and Human Factors and a member of the Institution of Engineering and Technology. He has been published in academic journals including "Nature". He has also helped organisations design new human-machine interfaces, such as the Adaptive Cruise Control system for Jaguar Cars.\n"""
    """Wikipedia Title: Finding Nemo\nFinding Nemo Theatrical release poster Directed by Andrew Stanton Produced by Graham Walters Screenplay by Andrew Stanton Bob Peterson David Reynolds Story by Andrew Stanton Starring Albert Brooks Ellen DeGeneres Alexander Gould Willem Dafoe Music by Thomas Newman Cinematography Sharon Calahan Jeremy Lasky Edited by David Ian Salter Production company Walt Disney Pictures Pixar Animation Studios Distributed by Buena Vista Pictures Distribution Release date May 30, 2003 (2003 - 05 - 30) Running time 100 minutes Country United States Language English Budget $$94 million Box office $$940.3 million"""
)

_QA_SYSTEM = (
    'As an advanced reading comprehension assistant, your task is to analyze text passages and corresponding questions meticulously. '
    'Your response start after "Thought: ", where you will methodically break down the reasoning process, illustrating how you arrive at conclusions. '
    'Conclude with "Answer: " to present a concise, definitive response, devoid of additional elaborations.'
)

_ONE_SHOT_INPUT = (
    f"{_ONE_SHOT_DOCS}"
    "\n\nQuestion: "
    "When was Neville A. Stanton's employer founded?"
    '\nThought: '
)

_ONE_SHOT_OUTPUT = (
    "The employer of Neville A. Stanton is University of Southampton. The University of Southampton was founded in 1862. "
    "\nAnswer: 1862."
)


async def _qa_body(ctx: NodeContext) -> dict[str, Any]:
    query = str((ctx.config or {}).get("query", ""))
    items = (ctx.inputs.get("assemble-result") or {}).get("items", [])
    passages = [str(item.get("content", "")) for item in items if item.get("content")]
    if not passages:
        return {"completion": PROMPTS["fail_response"], "tokens": TokenAccounting(counted_by="none")}

    prompt_user = "".join(f"Wikipedia Title: {passage}\n\n" for passage in passages)
    prompt_user += "Question: " + query + "\nThought: "
    result = await ctx.clients["llm"].chat(
        [
            {"role": "system", "content": _QA_SYSTEM},
            {"role": "user", "content": _ONE_SHOT_INPUT},
            {"role": "assistant", "content": _ONE_SHOT_OUTPUT},
            {"role": "user", "content": prompt_user},
        ]
    )
    parts = result.text.split("Answer:")
    answer = parts[1].strip() if len(parts) > 1 else result.text
    return {
        "completion": answer,
        "tokens": result.tokens,
        "resolved_model_identity": result.resolved_model_identity,
    }


HIPPORAG_QA_READER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="generator",
    structural_depth="opaque",
    effects=["calls_llm"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_qa_body,
)
