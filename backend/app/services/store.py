from app.models import Advisor, Document, StudentProfile, WorkflowRun


class InMemoryStore:
    def __init__(self) -> None:
        self.profile = StudentProfile(
            name="Demo Student",
            university="Xiamen University",
            major="Computer Science",
            rank_percent=8,
            research_interests=["machine learning", "agent systems"],
            projects=["Multi-agent baoyan assistant", "Course recommendation system"],
            competitions=["Lanqiao Cup provincial prize"],
            preferred_schools=["Shanghai Jiao Tong University", "Zhejiang University"],
        )
        self.documents: list[Document] = [
            Document(
                title="SJTU CS Summer Camp Notice",
                doc_type="notice",
                content="Requires resume, transcript, ranking certificate, research statement, and possible coding test.",
                source="sample",
                keywords=["SJTU", "resume", "coding test", "summer camp"],
            ),
            Document(
                title="Advisor Wang homepage note",
                doc_type="advisor",
                content="Research areas include machine learning systems, LLM agents, and trustworthy AI applications.",
                source="sample",
                keywords=["advisor", "LLM", "agent", "machine learning"],
            ),
        ]
        self.advisors: list[Advisor] = [
            Advisor(
                name="Prof. Wang",
                university="Shanghai Jiao Tong University",
                research_areas=["machine learning", "LLM agents", "AI systems"],
                homepage="https://example.edu/wang",
                summary="Works on agent systems and applied machine learning.",
            ),
            Advisor(
                name="Prof. Chen",
                university="Zhejiang University",
                research_areas=["database", "information retrieval", "RAG"],
                homepage="https://example.edu/chen",
                summary="Works on retrieval systems and data management.",
            ),
        ]
        self.workflows: list[WorkflowRun] = []

    def add_workflow(self, workflow: WorkflowRun) -> WorkflowRun:
        self.workflows.insert(0, workflow)
        return workflow


store = InMemoryStore()
