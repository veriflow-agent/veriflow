import os
from pathlib import Path
from datetime import datetime

class FileManager:
    """Manage temporary storage of scraped content"""

    def __init__(self, temp_dir: str = "temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)

    def create_session(self) -> str:
        """Create unique session directory"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_path = self.temp_dir / session_id
        session_path.mkdir(exist_ok=True)
        return session_id

    def save_excerpt(self, session_id: str, fact_id: str, 
                     url: str, content: str):
        """Save highlighted excerpt to file"""
        session_path = self.temp_dir / session_id

        # Sanitize URL for filename
        filename = f"{fact_id}_{self._sanitize_url(url)}.txt"
        filepath = session_path / filename

        # Write with metadata header
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"SOURCE: {url}\n")
            f.write(f"FACT_ID: {fact_id}\n")
            f.write(f"EXTRACTED: {datetime.now().isoformat()}\n")
            f.write("---\n")
            f.write(content)

    def _sanitize_url(self, url: str) -> str:
        """Convert URL to safe filename"""
        return url.replace('https://', '').replace('http://', '')\
                  .replace('/', '_')[:50]

    def cleanup_old_sessions(self, days: int = 1):
        """Remove sessions older than specified days"""
        # Implementation for cleanup
        pass