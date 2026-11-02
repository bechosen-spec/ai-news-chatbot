from backend.app.services.llm import GeneratedAnswer
from backend.app.services.retrieval import Evidence


def validate_citations(answer: GeneratedAnswer, evidence: list[Evidence]) -> tuple[bool, list[str]]:
    allowed = {item.citation_id for item in evidence}
    supplied = set(answer.citation_ids)
    errors: list[str] = []
    unknown = sorted(supplied - allowed)
    if unknown:
        errors.append(f"Unknown citation IDs: {', '.join(unknown)}")
    if evidence and not supplied:
        errors.append("The generated answer did not cite retrieved evidence")
    return not errors, errors
