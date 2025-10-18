"""
Admin endpoints for comprehensive metrics and monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database import get_db, AdminUser
from app.utils.metrics_calculator import MetricsCalculator
from app.utils.cost_calculator import get_user_usage_summary
from app.database import User, SearchMetrics
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/metrics/platform")
async def get_platform_metrics(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get comprehensive platform-wide metrics"""
    try:
        calculator = MetricsCalculator(db)
        metrics = calculator.get_platform_metrics(days)
        
        if "error" in metrics:
            raise HTTPException(status_code=500, detail=metrics["error"])
        
        return {
            "success": True,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting platform metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/daily")
async def get_daily_metrics(
    days: int = Query(7, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get daily breakdown of metrics"""
    try:
        calculator = MetricsCalculator(db)
        metrics = calculator.get_daily_metrics(days)
        
        if "error" in metrics:
            raise HTTPException(status_code=500, detail=metrics["error"])
        
        return {
            "success": True,
            "daily_metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting daily metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/user/{user_id}")
async def get_user_metrics(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get comprehensive metrics for a specific user"""
    try:
        calculator = MetricsCalculator(db)
        metrics = calculator.get_user_metrics(user_id)
        
        if "error" in metrics:
            raise HTTPException(status_code=404, detail=metrics["error"])
        
        return {
            "success": True,
            "user_metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting user metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users")
async def get_all_users(db: Session = Depends(get_db)):
    """Get list of all users with their usage summary"""
    try:
        users = db.query(User).all()
        
        user_list = []
        for user in users:
            usage_summary = get_user_usage_summary(user.results_used, user.posts_analyzed)
            
            user_list.append({
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "company": user.company,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "usage": usage_summary,
                "total_tokens_used": user.total_tokens_used,
                "total_cost": round(user.total_cost, 4),
                "is_active": user.is_active
            })
        
        # Sort by total cost (highest first)
        user_list.sort(key=lambda x: x["total_cost"], reverse=True)
        
        return {
            "success": True,
            "total_users": len(user_list),
            "users": user_list
        }
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/searches/recent")
async def get_recent_searches(
    limit: int = Query(50, description="Number of recent searches to return"),
    db: Session = Depends(get_db)
):
    """Get recent searches with detailed metrics"""
    try:
        searches = db.query(SearchMetrics).order_by(
            SearchMetrics.created_at.desc()
        ).limit(limit).all()
        
        search_list = []
        for search in searches:
            user_info = None
            if search.user:
                user_info = {
                    "id": search.user.id,
                    "email": search.user.email,
                    "name": search.user.name
                }
            
            search_list.append({
                "id": search.id,
                "user": user_info,
                "user_session_id": search.user_session_id,
                "problem_description": search.problem_description,
                "business_type": search.business_type,
                "result_count_requested": search.result_count_requested,
                "result_count_returned": search.result_count_returned,
                "posts_scraped": search.posts_scraped,
                "posts_analyzed": search.posts_analyzed,
                "tokens_used": search.tokens_used,
                "cost": round(search.cost, 4),
                "model_used": search.model_used,
                "search_duration_ms": search.search_duration_ms,
                "created_at": search.created_at.isoformat()
            })
        
        return {
            "success": True,
            "total_searches": len(search_list),
            "searches": search_list
        }
        
    except Exception as e:
        logger.error(f"Error getting recent searches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/costs/summary")
async def get_cost_summary(db: Session = Depends(get_db)):
    """Get cost summary for budget tracking"""
    try:
        # Get total costs from search metrics
        from sqlalchemy import func
        total_cost_from_searches = db.query(func.sum(SearchMetrics.cost)).scalar() or 0
        
        total_tokens_from_searches = db.query(func.sum(SearchMetrics.tokens_used)).scalar() or 0
        
        # Get user totals
        total_user_cost = db.query(func.sum(User.total_cost)).scalar() or 0
        
        total_user_tokens = db.query(func.sum(User.total_tokens_used)).scalar() or 0
        
        # Get today's costs
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_cost = db.query(func.sum(SearchMetrics.cost)).filter(
            SearchMetrics.created_at >= today_start
        ).scalar() or 0
        
        today_tokens = db.query(func.sum(SearchMetrics.tokens_used)).filter(
            SearchMetrics.created_at >= today_start
        ).scalar() or 0
        
        # Get this week's costs
        week_start = today_start - timedelta(days=7)
        week_cost = db.query(func.sum(SearchMetrics.cost)).filter(
            SearchMetrics.created_at >= week_start
        ).scalar() or 0
        
        week_tokens = db.query(func.sum(SearchMetrics.tokens_used)).filter(
            SearchMetrics.created_at >= week_start
        ).scalar() or 0
        
        return {
            "success": True,
            "cost_summary": {
                "total_cost_all_time": round(total_cost_from_searches, 4),
                "total_tokens_all_time": total_tokens_from_searches,
                "user_totals": {
                    "total_cost": round(total_user_cost, 4),
                    "total_tokens": total_user_tokens
                },
                "today": {
                    "cost": round(today_cost, 4),
                    "tokens": today_tokens
                },
                "this_week": {
                    "cost": round(week_cost, 4),
                    "tokens": week_tokens
                },
                "budget_estimate": {
                    "beta_users": 20,
                    "max_cost_per_user": 4.50,
                    "estimated_total_budget": 90.00,
                    "current_usage_percentage": round((total_cost_from_searches / 90.00) * 100, 1)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting cost summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def admin_health_check(db: Session = Depends(get_db)):
    """Health check for admin system"""
    try:
        # Check database connection
        user_count = db.query(User).count()
        search_count = db.query(SearchMetrics).count()
        
        return {
            "success": True,
            "status": "healthy",
            "database": "connected",
            "stats": {
                "total_users": user_count,
                "total_searches": search_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Admin health check failed: {e}")
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
