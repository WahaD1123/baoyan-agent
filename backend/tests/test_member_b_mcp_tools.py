from app.models import Advisor, Document, StudentProfile
from app.tools.member_b_tools import (
    advisor_list,
    advisor_match,
    knowledge_add_text,
    knowledge_list_documents,
    knowledge_query,
    member_b_tool_names,
)


def test_member_b_tool_manifest_contains_core_capabilities() -> None:
    assert set(member_b_tool_names()) == {
        "knowledge.add_text",
        "knowledge.add_url",
        "knowledge.query",
        "knowledge.list_documents",
        "advisor.add_url",
        "advisor.list",
        "advisor.match",
    }


def test_knowledge_add_text_and_list(monkeypatch) -> None:
    documents: list[Document] = []
    workflows = []

    monkeypatch.setattr("app.tools.member_b_tools.store.documents", documents)
    monkeypatch.setattr("app.tools.member_b_tools.store.add_document", lambda doc: documents.insert(0, doc) or doc)
    monkeypatch.setattr("app.tools.member_b_tools.store.add_workflow", lambda workflow: workflows.append(workflow) or workflow)
    monkeypatch.setattr("app.tools.member_b_tools.store.refresh_documents", lambda: documents)

    result = knowledge_add_text(
        title="Direct PhD experience",
        doc_type="experience",
        content="This post discusses whether students should choose direct PhD.",
    )
    listed = knowledge_list_documents()

    assert result["document"]["title"] == "Direct PhD experience"
    assert result["document"]["doc_type"] == "experience"
    assert listed["count"] == 1
    assert listed["documents"][0]["title"] == "Direct PhD experience"
    assert workflows


def test_knowledge_query_returns_answer_documents_and_workflow(monkeypatch) -> None:
    document = Document(
        title="Summer camp notice",
        doc_type="notice",
        content="Applicants need resume and transcript.",
    )

    monkeypatch.setattr("app.tools.member_b_tools.route_documents_by_library", lambda question, docs, top_k: [document])
    monkeypatch.setattr("app.tools.member_b_tools.route_chunks_for_documents", lambda question, docs, top_k: [])
    monkeypatch.setattr("app.tools.member_b_tools.store.add_workflow", lambda workflow: workflow)

    result = knowledge_query("What materials are required?", top_k=1)

    assert result["question"] == "What materials are required?"
    assert result["documents"][0]["title"] == "Summer camp notice"
    assert result["workflow"]["type"] == "knowledge"
    assert "answer" in result


def test_advisor_list_and_match(monkeypatch) -> None:
    advisor = Advisor(
        name="Prof. Zhang",
        university="Target University",
        research_areas=["machine learning"],
        summary="Works on reliable ML systems.",
    )
    profile = StudentProfile(
        research_interests=["machine learning"],
        preferred_schools=["Target University"],
    )

    monkeypatch.setattr("app.tools.member_b_tools.store.advisors", [advisor])
    monkeypatch.setattr("app.tools.member_b_tools.store.add_workflow", lambda workflow: workflow)

    listed = advisor_list()
    matched = advisor_match(profile.model_dump(mode="json"), top_k=1)

    assert listed["count"] == 1
    assert listed["advisors"][0]["name"] == "Prof. Zhang"
    assert matched["matches"][0]["advisor"]["name"] == "Prof. Zhang"
    assert matched["matches"][0]["score"] >= 60
