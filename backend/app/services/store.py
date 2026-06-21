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
            name="张三",
            university="厦门大学",
            major="计算机科学与技术",
            rank_percent=8,
            gpa=3.82,
            english_score="CET-6 523",
            research_interests=["机器学习", "大模型智能体", "AI系统"],
            projects=[
                (
                    "多智能体保研助手：负责申请材料生成与模拟面试模块；使用 Python、FastAPI、React、"
                    "OpenAI Agents SDK 和 MCP Streamable HTTP；实现受约束 Planner→MCP Tool→Generate→"
                    "Critic→Revise 工作流，提供导师邮件、简历亮点、个人陈述和面试题 4 类输出；"
                    "C 模块 11 项自动化测试通过。"
                ),
                (
                    "课程推荐系统：使用 Python、Pandas、scikit-learn，基于 TF-IDF 课程文本特征与"
                    "余弦相似度完成内容推荐；清洗 1200 条匿名选课记录，离线 Top-5 命中率 78%，"
                    "较热门课程基线提升 12 个百分点；负责数据清洗、特征工程、接口封装与评估。"
                ),
            ],
            competitions=["2025 年第十六届蓝桥杯 Python 程序设计大学 B 组省级二等奖"],
            publications=[
                (
                    "AAAI 2026 论文《Tool-Grounded Planning for Reliable Multi-Agent Assistants》"
                    "第二作者；负责基线复现、消融实验、错误案例分析与实验章节撰写；"
                    "主要方法在内部测试集的任务成功率较基线提升 8.6 个百分点。"
                )
            ],
            target_regions=["上海", "北京"],
            preferred_schools=["上海交通大学", "浙江大学"],
            notes=(
                "核心课程：机器学习 93 分、数据结构 91 分、操作系统 89 分。"
                "常用邮箱 zhangsan.demo@example.com，联系电话 138-0000-0000。"
                "计划申请上海交通大学人工智能方向王老师课题组，关注可信智能体与 AI 系统。"
            ),
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
            [advisor.model_dump(mode="json") for advisor in self._sample_advisors()],
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
