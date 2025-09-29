# Use your existing BrowserlessRestaurantScraper
# Just modify to accept Railway Browserless endpoint

class FactCheckScraper(BrowserlessRestaurantScraper):
    """
    Adapted scraper for fact-checking URLs
    Inherits Railway Browserless integration
    """

    async def scrape_urls_for_facts(self, urls: List[str]) -> Dict[str, str]:
        """
        Scrape multiple URLs and return clean content
        Returns: {url: scraped_content}
        """
        results = {}

        for url in urls:
            try:
                content = await self._extract_content_structure_preserving(url)
                if content:
                    results[url] = content
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                results[url] = ""

        return results