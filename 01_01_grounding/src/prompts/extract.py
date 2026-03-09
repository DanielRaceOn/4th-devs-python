# -*- coding: utf-8 -*-

#   extract.py

"""
### Description:
Prompt builder for the concept extraction pipeline stage.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Based on:      `src/prompts/extract.js`

"""

from ..schemas.categories import CONCEPT_CATEGORIES

EXTRACTION_GUIDELINES = f"""Goal: extract verifiable claims and key terms that benefit from grounding via web search.

Categories:
- claim: a verifiable statement with facts, dates, counts, or attributions
- definition: an explicit definition or explanation of a term
- term: domain-specific concept or jargon worth grounding
- entity: a named person, organization, product central to the paragraph
- reference: a cited work, paper, or external source
- result: a reported finding or outcome
- method: a procedure, algorithm, or process
- metric: a quantitative measure or threshold
- resource: a dataset, tool, or system

surfaceForms rules (CRITICAL):
- surfaceForms are SHORT KEY PHRASES, NOT entire sentences.
- Ideal length: 3-12 words. Never exceed 15 words.
- Extract the minimal phrase that uniquely identifies the claim.
- GOOD: 'introduced by Google researchers in 2017', 'context windows of 128k tokens'
- BAD: 'The transformer was introduced by Google researchers in 2017.' (too long, includes filler)
- BAD: 'After pre-training, models are fine-tuned using RLHF. Human raters...' (multiple sentences)
- NEVER include markdown syntax (#, ##, *, etc.) in surfaceForms.
- For headers, extract the title text only, without # symbols.

Extraction rules:
- One concept = one verifiable unit. Don't split 'GPT-4 has 128k tokens' into two concepts.
- Don't extract overlapping phrases that would highlight the same text twice.
- Skip generic/obvious statements that don't benefit from web verification.
- needsSearch=true for claims needing verification; false for well-known terms.

Categories: {", ".join(CONCEPT_CATEGORIES)}."""


def build_extract_prompt(
    *,
    paragraph: str,
    paragraph_type: str,
    target_count: str,
    index: int,
    total: int,
) -> str:
    """Build the extraction prompt for a single paragraph.

    Args:
        paragraph: Text of the paragraph to extract from.
        paragraph_type: ``'header'`` or ``'body'``.
        target_count: Target concept count range string, e.g. ``'2-5'``.
        index: Zero-based paragraph index.
        total: Total paragraph count in the document.

    Returns:
        Formatted prompt string.
    """
    return (
        f"You extract concepts and topics from a single paragraph.\n"
        f"Focus entirely on this paragraph. Return JSON only, matching the schema.\n\n"
        f"<guidelines>\n{EXTRACTION_GUIDELINES}\n</guidelines>\n\n"
        f"Document context: paragraph {index + 1} of {total}\n"
        f"Paragraph type: {paragraph_type}\n"
        f"Target concepts: {target_count} (fewer for headers, more for body)\n\n"
        f"--- Paragraph ---\n{paragraph}"
    )
