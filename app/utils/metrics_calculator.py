"""
Comprehensive Metrics Calculator for OpenAI Usage and Costs
Tracks detailed metrics for both individual users and platform-wide statistics
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import User, SearchMetrics
import logging

logger = logging.getLogger(__name__)

class MetricsCalculator:
    """Calculate comprehensive metrics for OpenAI usage and costs"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_metrics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive metrics for a specific user"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}
            
            # Get search metrics for this user
            search_metrics = self.db.query(SearchMetrics).filter(
                SearchMetrics.user_id == user_id
            ).all()
            
            # Calculate totals
            total_searches = len(search_metrics)
            total_results_requested = sum(sm.result_count_requested for sm in search_metrics)
            total_results_returned = sum(sm.result_count_returned for sm in search_metrics)
            total_posts_scraped = sum(sm.posts_scraped for sm in search_metrics)
            total_posts_analyzed = sum(sm.posts_analyzed for sm in search_metrics)
            total_tokens_used = sum(sm.tokens_used for sm in search_metrics)
            total_cost = sum(sm.cost for sm in search_metrics)
            
            # Calculate averages
            avg_cost_per_search = total_cost / total_searches if total_searches > 0 else 0
            avg_tokens_per_search = total_tokens_used / total_searches if total_searches > 0 else 0
            avg_results_per_search = total_results_returned / total_searches if total_searches > 0 else 0
            
            # Calculate remaining limits
            results_remaining = 150 - user.results_used
            posts_remaining = 2250 - user.posts_analyzed
            
            return {
                "user_info": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "company": user.company,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                },
                "usage_summary": {
                    "results_used": user.results_used,
                    "results_remaining": results_remaining,
                    "posts_analyzed": user.posts_analyzed,
                    "posts_remaining": posts_remaining,
                    "total_tokens_used": user.total_tokens_used,
                    "total_cost": round(user.total_cost, 4)
                },
                "search_statistics": {
                    "total_searches": total_searches,
                    "total_results_requested": total_results_requested,
                    "total_results_returned": total_results_returned,
                    "total_posts_scraped": total_posts_scraped,
                    "total_posts_analyzed": total_posts_analyzed,
                    "total_tokens_used": total_tokens_used,
                    "total_cost": round(total_cost, 4)
                },
                "averages": {
                    "avg_cost_per_search": round(avg_cost_per_search, 4),
                    "avg_tokens_per_search": round(avg_tokens_per_search, 1),
                    "avg_results_per_search": round(avg_results_per_search, 1),
                    "avg_posts_per_search": round(total_posts_analyzed / total_searches, 1) if total_searches > 0 else 0
                },
                "recent_searches": [
                    {
                        "id": sm.id,
                        "problem_description": sm.problem_description[:100] + "..." if len(sm.problem_description) > 100 else sm.problem_description,
                        "business_type": sm.business_type,
                        "results_returned": sm.result_count_returned,
                        "posts_analyzed": sm.posts_analyzed,
                        "tokens_used": sm.tokens_used,
                        "cost": round(sm.cost, 4),
                        "created_at": sm.created_at.isoformat()
                    }
                    for sm in search_metrics[-10:]  # Last 10 searches
                ]
            }
            
        except Exception as e:
            logger.error(f"Error calculating user metrics: {e}")
            return {"error": str(e)}
    
    def get_platform_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive platform-wide metrics"""
        try:
            # Date range for filtering
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get all search metrics in date range
            search_metrics = self.db.query(SearchMetrics).filter(
                SearchMetrics.created_at >= start_date
            ).all()
            
            # Get all users
            all_users = self.db.query(User).all()
            
            # Calculate totals
            total_searches = len(search_metrics)
            total_users = len(all_users)
            total_results_requested = sum(sm.result_count_requested for sm in search_metrics)
            total_results_returned = sum(sm.result_count_returned for sm in search_metrics)
            total_posts_scraped = sum(sm.posts_scraped for sm in search_metrics)
            total_posts_analyzed = sum(sm.posts_analyzed for sm in search_metrics)
            total_tokens_used = sum(sm.tokens_used for sm in search_metrics)
            total_cost = sum(sm.cost for sm in search_metrics)
            
            # Calculate user totals
            total_user_results_used = sum(user.results_used for user in all_users)
            total_user_posts_analyzed = sum(user.posts_analyzed for user in all_users)
            total_user_tokens_used = sum(user.total_tokens_used for user in all_users)
            total_user_cost = sum(user.total_cost for user in all_users)
            
            # Calculate averages
            avg_cost_per_search = total_cost / total_searches if total_searches > 0 else 0
            avg_tokens_per_search = total_tokens_used / total_searches if total_searches > 0 else 0
            avg_searches_per_user = total_searches / total_users if total_users > 0 else 0
            
            # Find most expensive operations
            expensive_searches = sorted(search_metrics, key=lambda x: x.cost, reverse=True)[:10]
            
            # Business type breakdown
            business_types = {}
            for sm in search_metrics:
                if sm.business_type:
                    if sm.business_type not in business_types:
                        business_types[sm.business_type] = {
                            "searches": 0,
                            "cost": 0.0,
                            "tokens": 0
                        }
                    business_types[sm.business_type]["searches"] += 1
                    business_types[sm.business_type]["cost"] += sm.cost
                    business_types[sm.business_type]["tokens"] += sm.tokens_used
            
            return {
                "platform_overview": {
                    "total_users": total_users,
                    "total_searches": total_searches,
                    "date_range_days": days,
                    "period_start": start_date.isoformat(),
                    "period_end": datetime.utcnow().isoformat()
                },
                "usage_totals": {
                    "total_results_requested": total_results_requested,
                    "total_results_returned": total_results_returned,
                    "total_posts_scraped": total_posts_scraped,
                    "total_posts_analyzed": total_posts_analyzed,
                    "total_tokens_used": total_tokens_used,
                    "total_cost": round(total_cost, 4)
                },
                "user_totals": {
                    "total_user_results_used": total_user_results_used,
                    "total_user_posts_analyzed": total_user_posts_analyzed,
                    "total_user_tokens_used": total_user_tokens_used,
                    "total_user_cost": round(total_user_cost, 4)
                },
                "averages": {
                    "avg_cost_per_search": round(avg_cost_per_search, 4),
                    "avg_tokens_per_search": round(avg_tokens_per_search, 1),
                    "avg_searches_per_user": round(avg_searches_per_user, 1),
                    "avg_results_per_search": round(total_results_returned / total_searches, 1) if total_searches > 0 else 0,
                    "avg_posts_per_search": round(total_posts_analyzed / total_searches, 1) if total_searches > 0 else 0
                },
                "business_type_breakdown": {
                    business_type: {
                        "searches": data["searches"],
                        "cost": round(data["cost"], 4),
                        "tokens": data["tokens"],
                        "avg_cost_per_search": round(data["cost"] / data["searches"], 4) if data["searches"] > 0 else 0
                    }
                    for business_type, data in business_types.items()
                },
                "most_expensive_searches": [
                    {
                        "id": sm.id,
                        "user_id": sm.user_id,
                        "problem_description": sm.problem_description[:100] + "..." if len(sm.problem_description) > 100 else sm.problem_description,
                        "business_type": sm.business_type,
                        "results_returned": sm.result_count_returned,
                        "tokens_used": sm.tokens_used,
                        "cost": round(sm.cost, 4),
                        "created_at": sm.created_at.isoformat()
                    }
                    for sm in expensive_searches
                ]
            }
            
        except Exception as e:
            logger.error(f"Error calculating platform metrics: {e}")
            return {"error": str(e)}
    
    def get_daily_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Get daily breakdown of metrics"""
        try:
            daily_data = {}
            
            for i in range(days):
                date = datetime.utcnow() - timedelta(days=i)
                start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = start_of_day + timedelta(days=1)
                
                search_metrics = self.db.query(SearchMetrics).filter(
                    SearchMetrics.created_at >= start_of_day,
                    SearchMetrics.created_at < end_of_day
                ).all()
                
                daily_data[date.strftime("%Y-%m-%d")] = {
                    "searches": len(search_metrics),
                    "results_returned": sum(sm.result_count_returned for sm in search_metrics),
                    "posts_analyzed": sum(sm.posts_analyzed for sm in search_metrics),
                    "tokens_used": sum(sm.tokens_used for sm in search_metrics),
                    "cost": round(sum(sm.cost for sm in search_metrics), 4)
                }
            
            return daily_data
            
        except Exception as e:
            logger.error(f"Error calculating daily metrics: {e}")
            return {"error": str(e)}
