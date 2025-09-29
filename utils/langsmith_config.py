# utils/langsmith_config.py
from langsmith import Client
from langchain.callbacks import LangChainTracer
from langchain.callbacks.manager import CallbackManager
import os

class LangSmithConfig:
    """Configure LangSmith tracing for all LangChain operations"""

    def __init__(self):
        self.client = Client()
        self.project_name = os.getenv("LANGCHAIN_PROJECT", "fact-checker")

        # Verify connection
        try:
            self.client.read_project(project_name=self.project_name)
            fact_logger.logger.info(f"✅ Connected to LangSmith project: {self.project_name}")
        except Exception as e:
            fact_logger.logger.warning(f"⚠️ LangSmith project not found, creating: {self.project_name}")
            self.client.create_project(project_name=self.project_name)

    def get_callbacks(self, run_name: str = None):
        """Get callback manager with LangSmith tracer"""
        tracer = LangChainTracer(
            project_name=self.project_name,
            client=self.client
        )

        if run_name:
            tracer.name = run_name

        return CallbackManager([tracer])

    def create_session(self, session_id: str, metadata: dict = None):
        """Create a LangSmith session for grouping related traces"""
        self.client.create_run(
            name=f"fact-check-session-{session_id}",
            run_type="chain",
            project_name=self.project_name,
            inputs={"session_id": session_id},
            extra=metadata or {}
        )

        fact_logger.logger.info(
            f"📊 Created LangSmith session: {session_id}",
            extra={"session_id": session_id, "metadata": metadata}
        )

langsmith_config = LangSmithConfig()