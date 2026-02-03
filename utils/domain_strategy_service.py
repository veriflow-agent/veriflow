# utils/domain_strategy_service.py
"""
Domain Strategy Service - Supabase Integration

Manages domain-specific scraping strategies with:
- Persistent storage in Supabase (domain, strategy, last_updated_at)
- In-memory performance tracking for the current session
- Fallback to in-memory cache if Supabase unavailable
"""

import time
from typing import Optional, Dict, List
from datetime import datetime
from utils.logger import fact_logger

# Try to import Supabase
SUPABASE_AVAILABLE = False
try:
    from supabase import create_client, Client
    import os
    SUPABASE_AVAILABLE = True
except ImportError:
    fact_logger.logger.warning("Supabase not available, using in-memory strategy cache")


class DomainStrategyService:
    """
    Service for managing domain-specific scraping strategies.

    Supabase table schema:
        domain       VARCHAR  (primary key)
        strategy     VARCHAR  (e.g. "basic", "advanced", "scrapingbee")
        last_updated_at  TIMESTAMP

    In-memory cache tracks per-session stats (success/failure counts)
    that are NOT persisted to Supabase.
    """

    def __init__(self):
        self.supabase: Optional[Client] = None
        self.in_memory_cache: Dict[str, Dict] = {}
        self.cache_enabled = False

        # Initialize Supabase if available
        if SUPABASE_AVAILABLE:
            self._init_supabase()
        else:
            fact_logger.logger.info("Using in-memory strategy cache (Supabase not configured)")
            self.cache_enabled = True

    def _init_supabase(self):
        """Initialize Supabase client"""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

            if supabase_url and supabase_key:
                self.supabase = create_client(supabase_url, supabase_key)
                self._test_connection()
                fact_logger.logger.info("Domain strategy service connected to Supabase")
            else:
                fact_logger.logger.warning("Supabase credentials not found, using in-memory cache")
                self.cache_enabled = True

        except Exception as e:
            fact_logger.logger.warning(f"Failed to initialize Supabase: {e}")
            fact_logger.logger.info("Falling back to in-memory strategy cache")
            self.cache_enabled = True

    def _test_connection(self):
        """Test Supabase connection"""
        try:
            if self.supabase:
                self.supabase.table('domain_scraping_strategies').select('domain').limit(1).execute()
        except Exception as e:
            fact_logger.logger.warning(f"Supabase connection test failed: {e}")
            fact_logger.logger.info("Make sure 'domain_scraping_strategies' table exists")
            self.cache_enabled = True

    # ------------------------------------------------------------------
    # Core methods: get / save
    # ------------------------------------------------------------------

    def get_strategy(self, domain: str) -> Optional[str]:
        """
        Get the best-known strategy for a domain.

        Args:
            domain: Domain name (e.g., "reuters.com")

        Returns:
            Strategy name ("basic", "advanced", "scrapingbee") or None
        """
        try:
            # Try Supabase first
            if self.supabase and not self.cache_enabled:
                result = self.supabase.table('domain_scraping_strategies').select(
                    'strategy'
                ).eq('domain', domain).limit(1).execute()

                if result.data and len(result.data) > 0:
                    strategy = result.data[0]['strategy']
                    fact_logger.logger.debug(
                        f"Retrieved strategy for {domain}: {strategy} (from Supabase)"
                    )
                    return strategy

                return None

            # Fallback to in-memory cache
            elif domain in self.in_memory_cache:
                return self.in_memory_cache[domain].get('strategy')

            return None

        except Exception as e:
            fact_logger.logger.debug(f"Error getting strategy for {domain}: {e}")

            # Fallback to in-memory cache
            if domain in self.in_memory_cache:
                return self.in_memory_cache[domain].get('strategy')

            return None

    def save_strategy(self, domain: str, strategy: str):
        """
        Save/update the best-known strategy for a domain.

        Uses upsert so it works for both new and existing domains.

        Args:
            domain: Domain name (e.g., "reuters.com")
            strategy: Strategy that worked ("basic", "advanced", "scrapingbee")
        """
        try:
            if self.supabase and not self.cache_enabled:
                self.supabase.table('domain_scraping_strategies').upsert({
                    'domain': domain,
                    'strategy': strategy,
                    'last_updated_at': datetime.utcnow().isoformat(),
                }, on_conflict='domain').execute()

                fact_logger.logger.info(f"Saved strategy for {domain}: {strategy}")

            # Always update in-memory cache
            if domain not in self.in_memory_cache:
                self.in_memory_cache[domain] = {
                    'strategy': strategy,
                    'success_count': 0,
                    'failure_count': 0,
                }
            self.in_memory_cache[domain]['strategy'] = strategy

        except Exception as e:
            fact_logger.logger.debug(f"Error saving strategy for {domain}: {e}")
            # Still update in-memory cache
            if domain not in self.in_memory_cache:
                self.in_memory_cache[domain] = {
                    'strategy': strategy,
                    'success_count': 0,
                    'failure_count': 0,
                }
            else:
                self.in_memory_cache[domain]['strategy'] = strategy

    # ------------------------------------------------------------------
    # Session-level tracking (in-memory only, not persisted)
    # ------------------------------------------------------------------

    def record_success(self, domain: str, strategy: str, scrape_time_ms: int = 0):
        """
        Record a successful scrape. Persists strategy to Supabase
        and increments the in-memory session counter.

        Args:
            domain: Domain name
            strategy: Strategy that worked
            scrape_time_ms: Time taken in milliseconds (tracked in-memory only)
        """
        # Persist the winning strategy to Supabase
        self.save_strategy(domain, strategy)

        # Bump in-memory success counter
        if domain not in self.in_memory_cache:
            self.in_memory_cache[domain] = {
                'strategy': strategy,
                'success_count': 0,
                'failure_count': 0,
            }
        self.in_memory_cache[domain]['success_count'] = (
            self.in_memory_cache[domain].get('success_count', 0) + 1
        )

        fact_logger.logger.debug(
            f"Recorded success for {domain} ({strategy}, {scrape_time_ms}ms)"
        )

    def record_failure(self, domain: str, strategy: str):
        """
        Record a failed scrape attempt (in-memory only).

        We do NOT persist failures to Supabase -- the table only
        stores strategies that have actually worked.

        Args:
            domain: Domain name
            strategy: Strategy that failed
        """
        if domain not in self.in_memory_cache:
            self.in_memory_cache[domain] = {
                'strategy': None,
                'success_count': 0,
                'failure_count': 0,
            }
        self.in_memory_cache[domain]['failure_count'] = (
            self.in_memory_cache[domain].get('failure_count', 0) + 1
        )

        fact_logger.logger.debug(f"Recorded failure for {domain} ({strategy})")

    # ------------------------------------------------------------------
    # Bulk queries
    # ------------------------------------------------------------------

    def get_all_strategies(self) -> Dict[str, str]:
        """
        Get all learned domain strategies.

        Returns:
            Dict mapping domain -> strategy
        """
        try:
            if self.supabase and not self.cache_enabled:
                result = self.supabase.table('domain_scraping_strategies').select(
                    'domain, strategy'
                ).execute()

                if result.data:
                    return {r['domain']: r['strategy'] for r in result.data}

            # Fallback to in-memory cache
            return {
                domain: data.get('strategy')
                for domain, data in self.in_memory_cache.items()
                if data.get('strategy')
            }

        except Exception as e:
            fact_logger.logger.debug(f"Error getting all strategies: {e}")
            return {
                domain: data.get('strategy')
                for domain, data in self.in_memory_cache.items()
                if data.get('strategy')
            }

    def get_statistics(self) -> Dict:
        """
        Get strategy usage statistics from the in-memory session cache.

        Returns:
            Dict with strategy performance metrics for the current session
        """
        return self._calculate_memory_stats()

    def _calculate_memory_stats(self) -> Dict:
        """Calculate statistics from in-memory cache"""
        stats = {}

        for domain, data in self.in_memory_cache.items():
            strategy = data.get('strategy')
            if not strategy:
                continue

            if strategy not in stats:
                stats[strategy] = {
                    'domains': 0,
                    'total_success': 0,
                    'total_failure': 0,
                    'total_attempts': 0,
                }

            success = data.get('success_count', 0)
            failure = data.get('failure_count', 0)

            stats[strategy]['domains'] += 1
            stats[strategy]['total_success'] += success
            stats[strategy]['total_failure'] += failure
            stats[strategy]['total_attempts'] += success + failure

        # Calculate success rates
        for strategy, sdata in stats.items():
            if sdata['total_attempts'] > 0:
                sdata['success_rate'] = (
                    sdata['total_success'] / sdata['total_attempts'] * 100
                )
            else:
                sdata['success_rate'] = 0

        return stats

    def get_top_performers(self, limit: int = 10) -> List[Dict]:
        """
        Get domains with known strategies (from Supabase).

        Args:
            limit: Number of results to return

        Returns:
            List of domain strategy records
        """
        try:
            if self.supabase and not self.cache_enabled:
                result = self.supabase.table('domain_scraping_strategies').select(
                    'domain, strategy, last_updated_at'
                ).order('last_updated_at', desc=True).limit(limit).execute()

                if result.data:
                    return result.data

            return []

        except Exception as e:
            fact_logger.logger.debug(f"Error getting top performers: {e}")
            return []

    def get_poor_performers(self, limit: int = 10, min_attempts: int = 5) -> List[Dict]:
        """
        Get domains with poor success rates from in-memory session data.

        Args:
            limit: Number of results to return
            min_attempts: Minimum attempts to be considered

        Returns:
            List of underperforming domain records
        """
        poor = []
        for domain, data in self.in_memory_cache.items():
            success = data.get('success_count', 0)
            failure = data.get('failure_count', 0)
            total = success + failure
            if total >= min_attempts:
                rate = (success / total * 100) if total > 0 else 0
                if rate < 50:
                    poor.append({
                        'domain': domain,
                        'strategy': data.get('strategy'),
                        'success_rate': round(rate, 1),
                        'total_attempts': total,
                    })

        poor.sort(key=lambda x: x['success_rate'])
        return poor[:limit]

    def reset_domain(self, domain: str):
        """
        Reset learning for a specific domain.

        Args:
            domain: Domain to reset
        """
        try:
            if self.supabase and not self.cache_enabled:
                self.supabase.table('domain_scraping_strategies').delete().eq(
                    'domain', domain
                ).execute()

                fact_logger.logger.info(f"Reset strategy learning for {domain}")

            # Remove from in-memory cache
            if domain in self.in_memory_cache:
                del self.in_memory_cache[domain]

        except Exception as e:
            fact_logger.logger.debug(f"Error resetting domain {domain}: {e}")

            # Still remove from cache
            if domain in self.in_memory_cache:
                del self.in_memory_cache[domain]


# Singleton instance
_domain_strategy_service = None

def get_domain_strategy_service() -> DomainStrategyService:
    """Get or create the singleton domain strategy service"""
    global _domain_strategy_service
    if _domain_strategy_service is None:
        _domain_strategy_service = DomainStrategyService()
    return _domain_strategy_service