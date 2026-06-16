from app.agents.base import BaseAgent


class ProfileAgent(BaseAgent):
    name = "ProfileAgent"
    task = "profile"


class SchoolRecommendAgent(BaseAgent):
    name = "SchoolRecommendAgent"
    task = "school"


class PlannerAgent(BaseAgent):
    name = "PlannerAgent"
    task = "planner"


class KnowledgeAgent(BaseAgent):
    name = "KnowledgeAgent"
    task = "knowledge"


class AdvisorMatchAgent(BaseAgent):
    name = "AdvisorMatchAgent"
    task = "advisor"


class MaterialAgent(BaseAgent):
    name = "MaterialAgent"
    task = "material"


class InterviewAgent(BaseAgent):
    name = "InterviewAgent"
    task = "interview"


class CriticAgent(BaseAgent):
    name = "CriticAgent"
    task = "critic"
