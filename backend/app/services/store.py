import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.models import Advisor, Document, StudentProfile, WorkflowRun


class JsonStore:
    def __init__(self) -> None:
        self.store_dir = Path(__file__).resolve().parents[3] / "data" / "store"
        self.seed_dir = Path(__file__).resolve().parents[3] / "data" / "seed"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.seed_dir.mkdir(parents=True, exist_ok=True)
        self.documents_path = self.store_dir / "documents.json"
        self.seed_documents_path = self.seed_dir / "boardcaster_documents.json"
        self.advisors_path = self.store_dir / "advisors.json"
        self.workflows_path = self.store_dir / "workflows.json"
        self.settings = get_settings()
        self.profile = self._sample_profile()
        self.documents = self._load_documents()
        self.advisors = self._load_advisors()
        self.workflows = self._load_workflows()
        self.purge_demo_content(save=True)

    def _sample_profile(self) -> StudentProfile:
        return StudentProfile(
            name="Demo Student",
            university="Xiamen University",
            major="Computer Science",
            rank_percent=8,
            research_interests=["machine learning", "agent systems"],
            projects=["Multi-agent baoyan assistant", "Course recommendation system"],
            competitions=["Lanqiao Cup provincial prize"],
            preferred_schools=["Shanghai Jiao Tong University", "Zhejiang University"],
        )

    def _sample_documents(self) -> list[Document]:
        return [
            Document(
                title="SJTU CS Summer Camp Notice",
                doc_type="notice",
                content="Requires resume, transcript, ranking certificate, research statement, and possible coding test.",
                source="sample",
                source_type="sample",
                keywords=["SJTU", "resume", "coding test", "summer camp"],
                extracted={
                    "materials": ["resume", "transcript", "ranking certificate", "research statement"],
                    "exam_format": ["coding test", "professional interview"],
                },
            ),
            Document(
                title="Advisor Wang homepage note",
                doc_type="advisor",
                content="Research areas include machine learning systems, LLM agents, and trustworthy AI applications.",
                source="sample",
                source_type="sample",
                keywords=["advisor", "LLM", "agent", "machine learning"],
                extracted={
                    "name": "Prof. Wang",
                    "research_areas": ["machine learning systems", "LLM agents"],
                },
            ),
        ]

    def _sample_advisors(self) -> list[Advisor]:
        return [
            Advisor(
                name="Prof. Wang",
                university="Shanghai Jiao Tong University",
                research_areas=["machine learning", "LLM agents", "AI systems"],
                homepage="https://example.edu/wang",
                summary="Works on agent systems and applied machine learning.",
                representative_works=["Agent systems for trustworthy AI"],
                suitable_background="Students with ML projects and system-building experience.",
            ),
            Advisor(
                name="Prof. Chen",
                university="Zhejiang University",
                research_areas=["database", "information retrieval", "RAG"],
                homepage="https://example.edu/chen",
                summary="Works on retrieval systems and data management.",
                representative_works=["Retrieval-augmented data management"],
                suitable_background="Students interested in databases, search, and RAG systems.",
            ),
        ]

    def _read_json(self, path: Path, default: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

    def _write_json(self, path: Path, records: list[dict[str, Any]]) -> None:
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_documents(self) -> list[Document]:
        from app.tools.document_processing import prepare_document

        default_records = self._seed_documents()
        if not default_records and self.settings.load_sample_data:
            default_records = [doc.model_dump(mode="json") for doc in self._sample_documents()]
        records = self._read_json(self.documents_path, default_records)
        documents = [Document.model_validate(record) for record in records]
        return [prepare_document(document) if not document.chunks else document for document in documents]

    def refresh_documents(self) -> list[Document]:
        self.documents = self._load_documents()
        return self.documents

    def _load_advisors(self) -> list[Advisor]:
        records = self._read_json(
            self.advisors_path,
            [advisor.model_dump(mode="json") for advisor in self._sample_advisors()] if self.settings.load_sample_data else [],
        )
        return [Advisor.model_validate(record) for record in records]

    def _load_workflows(self) -> list[WorkflowRun]:
        records = self._read_json(self.workflows_path, [])
        return [WorkflowRun.model_validate(record) for record in records]

    def save_documents(self) -> None:
        self._write_json(self.documents_path, [doc.model_dump(mode="json") for doc in self.documents])

    def save_advisors(self) -> None:
        self._write_json(self.advisors_path, [advisor.model_dump(mode="json") for advisor in self.advisors])

    def save_workflows(self) -> None:
        self._write_json(
            self.workflows_path,
            [workflow.model_dump(mode="json") for workflow in self.workflows[:100]],
        )

    def add_document(self, document: Document) -> Document:
        self.documents.insert(0, document)
        self.save_documents()
        return document

    def add_advisor(self, advisor: Advisor) -> Advisor:
        self.advisors.insert(0, advisor)
        self.save_advisors()
        return advisor

    def add_workflow(self, workflow: WorkflowRun) -> WorkflowRun:
        self.workflows.insert(0, workflow)
        self.save_workflows()
        return workflow

    def replace_documents(self, documents: list[Document]) -> list[Document]:
        self.documents = documents
        self.save_documents()
        return self.documents

    def purge_demo_content(self, save: bool = False) -> int:
        before = len(self.documents)
        self.documents = [document for document in self.documents if not _is_demo_document(document)]
        removed = before - len(self.documents)
        if removed and save:
            self.save_documents()
        return removed

    def _seed_documents(self) -> list[dict[str, Any]]:
        return self._read_json(self.seed_documents_path, [])


def _is_demo_document(document: Document) -> bool:
    title = document.title.strip().lower()
    source = document.source.strip().lower()
    return (
        document.source_type == "sample"
        or source in {"sample", "test"}
        or title.startswith("test ")
        or "summer camp notice" in title and source == "sample"
    )


store = JsonStore()
