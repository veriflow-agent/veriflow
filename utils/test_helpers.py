# utils/test_helpers.py
from utils.logger import fact_logger
import json

class FactCheckTester:
    """Helper tools for testing and debugging"""

    @staticmethod
    def print_session_summary(result: dict):
        """Pretty print session results"""
        print("\n" + "="*80)
        print(f"SESSION: {result['session_id']}")
        print("="*80)
        print(f"\n📊 SUMMARY:")
        print(f"   Total Facts: {result['summary']['total_facts']}")
        print(f"   Accurate (≥0.9): {result['summary']['accurate']}")
        print(f"   Good Match (0.7-0.9): {result['summary']['good_match']}")
        print(f"   Questionable (<0.7): {result['summary']['questionable']}")
        print(f"   Average Score: {result['summary']['avg_score']:.3f}")
        print(f"   Duration: {result['duration']:.2f}s")
        print(f"\n🔗 LangSmith URL: {result.get('langsmith_url', 'N/A')}")

        print(f"\n📋 FACT DETAILS:")
        for fact in result['facts']:
            print(f"\n   {fact['fact_id']}: {fact['statement'][:80]}...")
            print(f"   Score: {fact['match_score']:.2f} | Confidence: {fact['confidence']:.2f}")
            print(f"   Assessment: {fact['assessment'][:100]}...")
            if fact['discrepancies'] != 'none':
                print(f"   ⚠️  Discrepancies: {fact['discrepancies'][:100]}...")

        print("\n" + "="*80 + "\n")

    @staticmethod
    def export_session_report(result: dict, filepath: str):
        """Export detailed JSON report"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        fact_logger.logger.info(f"📄 Exported report to: {filepath}")