# utils/domain_strategy_service.py
"""
Domain Strategy Service - Supabase Integration

Manages domain-specific scraping strategies with:
- Persistent storage in Supabase
- Performance tracking (success/failure counts)
- Automatic strategy optimization
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
    fact_logger.logger.warning("âš ï¸ Supabase not available, using in-memory strategy cache")


class DomainStrategyService:
    """
    Service for managing domain-specific scraping strategies.
    
    Features:
    - Persistent storage in Supabase
    - Performance tracking
    - Automatic strategy optimization
    - Graceful fallback to in-memory cache
    """
    
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.in_memory_cache: Dict[str, Dict] = {}
        self.cache_enabled = False
        
        # Initialize Supabase if available
        if SUPABASE_AVAILABLE:
            self._init_supabase()
        else:
            fact_logger.logger.info("ðŸ“ Using in-memory strategy cache (Supabase not configured)")
            self.cache_enabled = True
    
    def _init_supabase(self):
        """Initialize Supabase client"""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
            
            if supabase_url and supabase_key:
                self.supabase = create_client(supabase_url, supabase_key)
                
                # Test connection
                self._test_connection()
                
                fact_logger.logger.info("âœ… Domain strategy service connected to Supabase")
            else:
                fact_logger.logger.warning("âš ï¸ Supabase credentials not found, using in-memory cache")
                self.cache_enabled = True
                
        except Exception as e:
            fact_logger.logger.warning(f"âš ï¸ Failed to initialize Supabase: {e}")
            fact_logger.logger.info("ðŸ“ Falling back to in-memory strategy cache")
            self.cache_enabled = True
    
    def _test_connection(self):
        """Test Supabase connection"""
        try:
            if self.supabase:
                # Try a simple query to verify table exists
                self.supabase.table('domain_scraping_strategies').select('domain').limit(1).execute()
        except Exception as e:
            fact_logger.logger.warning(f"âš ï¸ Supabase connection test failed: {e}")
            fact_logger.logger.info("ðŸ’¡ Make sure 'domain_scraping_strategies' table exists")
            self.cache_enabled = True
    
    def get_strategy(self, domain: str) -> Optional[str]:
        """
        Get the best-known strategy for a domain.
        
        Args:
            domain: Domain name (e.g., "reuters.com")
            
        Returns:
            Strategy name ("basic", "advanced", "scrapingbee") or None if unknown
        """
        try:
            # Try Supabase first
            if self.supabase and not self.cache_enabled:
                result = self.supabase.table('domain_scraping_strategies').select(
                    'strategy, success_count, total_attempts'
                ).eq('domain', domain).limit(1).execute()
                
                if result.data and len(result.data) > 0:
                    record = result.data[0]
                    strategy = record['strategy']
                    success_count = record.get('success_count', 0) or 0
                    total_attempts = record.get('total_attempts', 0) or 0
                    
                    # Compute success rate from counts
                    success_rate = (success_count / total_attempts * 100) if total_attempts > 0 else 0
                    
                    # Use strategy if success rate is decent or too few attempts to judge
                    if success_rate >= 50 or total_attempts < 3:
                        fact_logger.logger.debug(
                            f"Retrieved strategy for {domain}: {strategy} "
                            f"({success_rate:.0f}% success, {total_attempts} attempts)"
                        )
                        return strategy
                    else:
                        fact_logger.logger.debug(
                            f"Strategy for {domain} has low success rate "
                            f"({success_rate:.0f}%), will try all strategies"
                        )
                        return None
                
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
        Save/update the best-known strategy for a domain (simple upsert).
        
        Called by the scraper after a successful scrape to remember
        which strategy worked. Delegates to record_success with
        minimal overhead.
        
        Args:
            domain: Domain name (e.g., "reuters.com")
            strategy: Strategy that worked ("basic", "advanced", "scrapingbee")
        """
        try:
            if self.supabase and not self.cache_enabled:
                # Check if domain already has a record
                existing = self.supabase.table('domain_scraping_strategies').select(
                    'strategy, success_count, total_attempts'
                ).eq('domain', domain).limit(1).execute()
                
                if existing.data and len(existing.data) > 0:
                    record = existing.data[0]
                    old_strategy = record.get('strategy')
                    
                    if old_strategy == strategy:
                        # Same strategy -- just bump success count
                        self.supabase.table('domain_scraping_strategies').update({
                            'success_count': record['success_count'] + 1,
                            'total_attempts': record['total_attempts'] + 1,
                            'last_success_at': datetime.utcnow().isoformat(),
                        }).eq('domain', domain).execute()
                    else:
                        # Strategy changed -- update and reset counts
                        self.supabase.table('domain_scraping_strategies').update({
                            'strategy': strategy,
                            'success_count': 1,
                            'failure_count': 0,
                            'total_attempts': 1,
                            'last_success_at': datetime.utcnow().isoformat(),
                        }).eq('domain', domain).execute()
                        
                        fact_logger.logger.info(
                            f"Strategy changed for {domain}: {old_strategy} -> {strategy}"
                        )
                else:
                    # New domain -- insert
                    self.supabase.table('domain_scraping_strategies').insert({
                        'domain': domain,
                        'strategy': strategy,
                        'success_count': 1,
                        'failure_count': 0,
                        'total_attempts': 1,
                        'last_success_at': datetime.utcnow().isoformat(),
                    }).execute()
                    
                    fact_logger.logger.info(f"New strategy learned: {domain} -> {strategy}")
            
            # Always update in-memory cache
            self.in_memory_cache[domain] = {
                'strategy': strategy,
                'success_count': self.in_memory_cache.get(domain, {}).get('success_count', 0) + 1,
                'failure_count': self.in_memory_cache.get(domain, {}).get('failure_count', 0),
            }
            
        except Exception as e:
            fact_logger.logger.debug(f"Error saving strategy for {domain}: {e}")
            # Still update in-memory cache
            self.in_memory_cache[domain] = {
                'strategy': strategy,
                'success_count': 1,
                'failure_count': 0,
            }

    def record_success(
        self,
        domain: str,
        strategy: str,
        scrape_time_ms: int
    ):
        """
        Record a successful scrape.
        
        Args:
            domain: Domain name
            strategy: Strategy that worked
            scrape_time_ms: Time taken in milliseconds
        """
        try:
            # Update Supabase
            if self.supabase and not self.cache_enabled:
                # Check if domain exists
                existing = self.supabase.table('domain_scraping_strategies').select(
                    'success_count, failure_count, total_attempts, avg_scrape_time_ms'
                ).eq('domain', domain).eq('strategy', strategy).execute()
                
                if existing.data and len(existing.data) > 0:
                    # Update existing record
                    record = existing.data[0]
                    new_success = record['success_count'] + 1
                    new_total = record['total_attempts'] + 1
                    
                    # Calculate new average time
                    old_avg = record.get('avg_scrape_time_ms', 0) or 0
                    old_count = record['success_count']
                    new_avg = int((old_avg * old_count + scrape_time_ms) / new_success)
                    
                    self.supabase.table('domain_scraping_strategies').update({
                        'success_count': new_success,
                        'total_attempts': new_total,
                        'avg_scrape_time_ms': new_avg,
                        'last_success_at': datetime.utcnow().isoformat(),
                    }).eq('domain', domain).eq('strategy', strategy).execute()
                    
                    fact_logger.logger.debug(
                        f"âœ… Updated {domain} success: {new_success}/{new_total} "
                        f"({new_success/new_total*100:.1f}%)"
                    )
                else:
                    # Create new record
                    self.supabase.table('domain_scraping_strategies').insert({
                        'domain': domain,
                        'strategy': strategy,
                        'success_count': 1,
                        'failure_count': 0,
                        'total_attempts': 1,
                        'avg_scrape_time_ms': scrape_time_ms,
                        'last_success_at': datetime.utcnow().isoformat(),
                    }).execute()
                    
                    fact_logger.logger.info(f"ðŸ’¾ New strategy learned: {domain} â†’ {strategy}")
            
            # Always update in-memory cache
            if domain not in self.in_memory_cache:
                self.in_memory_cache[domain] = {
                    'strategy': strategy,
                    'success_count': 0,
                    'failure_count': 0,
                }
            
            self.in_memory_cache[domain]['strategy'] = strategy
            self.in_memory_cache[domain]['success_count'] += 1
            
        except Exception as e:
            fact_logger.logger.debug(f"Error recording success for {domain}: {e}")
            
            # Still update in-memory cache as fallback
            if domain not in self.in_memory_cache:
                self.in_memory_cache[domain] = {'strategy': strategy, 'success_count': 1}
            else:
                self.in_memory_cache[domain]['strategy'] = strategy
                self.in_memory_cache[domain]['success_count'] += 1
    
    def record_failure(
        self,
        domain: str,
        strategy: str
    ):
        """
        Record a failed scrape attempt.
        
        Args:
            domain: Domain name
            strategy: Strategy that failed
        """
        try:
            # Update Supabase
            if self.supabase and not self.cache_enabled:
                # Check if domain exists
                existing = self.supabase.table('domain_scraping_strategies').select(
                    'success_count, failure_count, total_attempts'
                ).eq('domain', domain).eq('strategy', strategy).execute()
                
                if existing.data and len(existing.data) > 0:
                    # Update existing record
                    record = existing.data[0]
                    new_failure = record['failure_count'] + 1
                    new_total = record['total_attempts'] + 1
                    
                    self.supabase.table('domain_scraping_strategies').update({
                        'failure_count': new_failure,
                        'total_attempts': new_total,
                        'last_failure_at': datetime.utcnow().isoformat(),
                    }).eq('domain', domain).eq('strategy', strategy).execute()
                    
                    success_rate = (record['success_count'] / new_total * 100) if new_total > 0 else 0
                    
                    fact_logger.logger.debug(
                        f"âŒ Updated {domain} failure: {record['success_count']}/{new_total} "
                        f"({success_rate:.1f}%)"
                    )
                else:
                    # Create record with failure
                    self.supabase.table('domain_scraping_strategies').insert({
                        'domain': domain,
                        'strategy': strategy,
                        'success_count': 0,
                        'failure_count': 1,
                        'total_attempts': 1,
                        'last_failure_at': datetime.utcnow().isoformat(),
                    }).execute()
            
            # Update in-memory cache
            if domain not in self.in_memory_cache:
                self.in_memory_cache[domain] = {
                    'strategy': strategy,
                    'success_count': 0,
                    'failure_count': 0,
                }
            
            self.in_memory_cache[domain]['failure_count'] += 1
            
        except Exception as e:
            fact_logger.logger.debug(f"Error recording failure for {domain}: {e}")
            
            # Still update in-memory cache
            if domain not in self.in_memory_cache:
                self.in_memory_cache[domain] = {'strategy': strategy, 'failure_count': 1}
            else:
                self.in_memory_cache[domain]['failure_count'] += 1
    
    def get_all_strategies(self) -> Dict[str, str]:
        """
        Get all learned domain strategies.
        
        Returns:
            Dict mapping domain to strategy
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
        Get strategy usage statistics.
        
        Returns:
            Dict with strategy performance metrics
        """
        try:
            if self.supabase and not self.cache_enabled:
                # Get aggregate statistics
                result = self.supabase.table('domain_scraping_strategies').select(
                    'strategy, success_count, failure_count, total_attempts'
                ).execute()
                
                if result.data:
                    # Aggregate by strategy
                    stats = {}
                    for record in result.data:
                        strategy = record['strategy']
                        if strategy not in stats:
                            stats[strategy] = {
                                'domains': 0,
                                'total_success': 0,
                                'total_failure': 0,
                                'total_attempts': 0,
                            }
                        
                        stats[strategy]['domains'] += 1
                        stats[strategy]['total_success'] += record['success_count']
                        stats[strategy]['total_failure'] += record['failure_count']
                        stats[strategy]['total_attempts'] += record['total_attempts']
                    
                    # Calculate success rates
                    for strategy, data in stats.items():
                        if data['total_attempts'] > 0:
                            data['success_rate'] = (
                                data['total_success'] / data['total_attempts'] * 100
                            )
                        else:
                            data['success_rate'] = 0
                    
                    return stats
            
            # Fallback to in-memory cache statistics
            return self._calculate_memory_stats()
            
        except Exception as e:
            fact_logger.logger.debug(f"Error getting statistics: {e}")
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
            
            stats[strategy]['domains'] += 1
            stats[strategy]['total_success'] += data.get('success_count', 0)
            stats[strategy]['total_failure'] += data.get('failure_count', 0)
            stats[strategy]['total_attempts'] += (
                data.get('success_count', 0) + data.get('failure_count', 0)
            )
        
        # Calculate success rates
        for strategy, data in stats.items():
            if data['total_attempts'] > 0:
                data['success_rate'] = (
                    data['total_success'] / data['total_attempts'] * 100
                )
            else:
                data['success_rate'] = 0
        
        return stats
    
    def get_top_performers(self, limit: int = 10) -> List[Dict]:
        """
        Get top performing domains by success rate.
        
        Args:
            limit: Number of results to return
            
        Returns:
            List of domain performance records
        """
        try:
            if self.supabase and not self.cache_enabled:
                result = self.supabase.table('domain_scraping_strategies').select(
                    'domain, strategy, success_count, total_attempts'
                ).order('success_rate', desc=True).limit(limit).execute()
                
                if result.data:
                    return result.data
            
            return []
            
        except Exception as e:
            fact_logger.logger.debug(f"Error getting top performers: {e}")
            return []
    
    def get_poor_performers(self, limit: int = 10, min_attempts: int = 5) -> List[Dict]:
        """
        Get domains with poor success rates.
        
        Args:
            limit: Number of results to return
            min_attempts: Minimum attempts to be considered
            
        Returns:
            List of underperforming domain records
        """
        try:
            if self.supabase and not self.cache_enabled:
                result = self.supabase.rpc(
                    'get_poor_performers',
                    {'min_attempts': min_attempts, 'result_limit': limit}
                ).execute()
                
                if result.data:
                    return result.data
            
            return []
            
        except Exception as e:
            fact_logger.logger.debug(f"Error getting poor performers: {e}")
            return []
    
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
                
                fact_logger.logger.info(f"ðŸ”„ Reset strategy learning for {domain}")
            
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
