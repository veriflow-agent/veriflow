# app.py
from flask import Flask, render_template, request, jsonify
import asyncio
import os
import re
from dotenv import load_dotenv

# Import your components
from orchestrator.llm_output_orchestrator import FactCheckOrchestrator
from orchestrator.web_search_orchestrator import WebSearchOrchestrator  # ✅ NEW
from utils.logger import fact_logger
from utils.langsmith_config import langsmith_config

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load configuration
class Config:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.browserless_endpoint = os.getenv('BROWSER_PLAYWRIGHT_ENDPOINT_PRIVATE')
        self.tavily_api_key = os.getenv('TAVILY_API_KEY')  # ✅ NEW
        self.langchain_project = os.getenv('LANGCHAIN_PROJECT', 'fact-checker')

        # Validate required env vars
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

        if not self.tavily_api_key:  # ✅ NEW
            fact_logger.logger.warning("⚠️ TAVILY_API_KEY not set - web search pipeline will not work")

        fact_logger.logger.info("✅ Configuration loaded successfully")

config = Config()

# Initialize orchestrators (singleton)
llm_orchestrator = FactCheckOrchestrator(config)
web_search_orchestrator = WebSearchOrchestrator(config) if config.tavily_api_key else None  # ✅ NEW

# ✅ NEW: Helper function for input detection
def detect_input_format(content: str) -> str:
    """
    Detect if input is HTML (LLM output with links) or plain text

    Args:
        content: Input content to analyze

    Returns:
        'html' or 'text'
    """
    # Check for HTML tags
    html_pattern = r'<\s*[a-z][^>]*>'

    # Check for common HTML elements
    has_html_tags = bool(re.search(html_pattern, content, re.IGNORECASE))

    # Check for anchor tags specifically (links)
    has_links = bool(re.search(r'<\s*a\s+[^>]*href\s*=', content, re.IGNORECASE))

    if has_html_tags or has_links:
        fact_logger.logger.info("📋 Detected HTML input format (LLM output with links)")
        return 'html'
    else:
        fact_logger.logger.info("📄 Detected plain text input format (no links)")
        return 'text'

@app.route('/')
def index():
    """Serve the main HTML interface"""
    return render_template('index.html')

@app.route('/api/check', methods=['POST'])
def check_facts():
    """
    Main API endpoint for fact checking
    Automatically detects input format and routes to appropriate pipeline
    """
    try:
        # Get content from request
        content = request.json.get('html_content') or request.json.get('content')

        if not content:
            return jsonify({
                "error": "No content provided"
            }), 400

        fact_logger.logger.info(
            f"📥 Received fact-check request",
            extra={"content_length": len(content)}
        )

        # ✅ DETECT INPUT FORMAT
        input_format = detect_input_format(content)

        # Check if web search orchestrator is available
        if input_format == 'text' and not web_search_orchestrator:
            return jsonify({
                "error": "Web search pipeline not available",
                "message": "TAVILY_API_KEY not configured. Please add it to use plain text verification."
            }), 503

        # Run async orchestrator in new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # ✅ ROUTE TO APPROPRIATE PIPELINE
            if input_format == 'html':
                fact_logger.logger.info("🔗 Using LLM Output pipeline (with links)")
                result = loop.run_until_complete(
                    llm_orchestrator.process(content)
                )
            else:
                fact_logger.logger.info("🔍 Using Web Search pipeline (no links)")
                result = loop.run_until_complete(
                    web_search_orchestrator.process(content)
                )
        finally:
            loop.close()

        # ✅ ADD FORMAT TO RESULT
        result['input_format'] = input_format

        fact_logger.logger.info(
            f"📤 Fact-check complete",
            extra={
                "session_id": result.get('session_id'),
                "total_facts": result['summary']['total_facts'],
                "pipeline": result.get('methodology'),
                "input_format": input_format
            }
        )

        return jsonify(result)

    except Exception as e:
        fact_logger.log_component_error("Flask API", e)
        return jsonify({
            "error": str(e),
            "message": "An error occurred during fact checking"
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({
        "status": "healthy",
        "langsmith_enabled": os.getenv('LANGCHAIN_TRACING_V2') == 'true',
        "browserless_configured": bool(os.getenv('BROWSER_PLAYWRIGHT_ENDPOINT_PRIVATE')),
        "tavily_configured": bool(os.getenv('TAVILY_API_KEY')),  # ✅ NEW
        "pipelines": {
            "llm_output": True,
            "web_search": bool(web_search_orchestrator)
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    fact_logger.logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    fact_logger.logger.info(f"🚀 Starting Flask server on port {port}")
    fact_logger.logger.info(f"🔍 Debug mode: {debug}")
    fact_logger.logger.info(f"📊 LangSmith project: {config.langchain_project}")

    # ✅ NEW: Log which pipelines are available
    if web_search_orchestrator:
        fact_logger.logger.info("✅ Both pipelines available: LLM Output & Web Search")
    else:
        fact_logger.logger.warning("⚠️ Only LLM Output pipeline available (add TAVILY_API_KEY for Web Search)")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )