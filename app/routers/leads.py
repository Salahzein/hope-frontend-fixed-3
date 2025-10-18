from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
import time
from sqlalchemy.orm import Session
from app.services.reddit_service import RedditService
from app.services.fast_lead_filter import FastLeadFilter
from app.services.business_mapping import get_business_options as get_business_mapping_options, get_industry_options as get_industry_mapping_options
from app.services.tiered_subreddit_mapping import get_beta_subreddits, get_beta_info
from app.services.result_cache import result_cache
from app.models.lead import Lead
from app.database import get_db, User, SearchMetrics
from app.utils.cost_calculator import get_posts_to_scrape, validate_user_limits, get_user_usage_summary

logger = logging.getLogger(__name__)
router = APIRouter()

class LeadSearchRequest(BaseModel):
    problem_description: str
    business: Optional[str] = None
    industry: Optional[str] = None
    user_id: Optional[str] = None
    result_count: int = 100  # Number of results to return (1-150)

class LeadSearchResponse(BaseModel):
    leads: List[Lead]
    total_found: int
    message: str
    timestamp: float  # Unix timestamp when results were fetched
    result_age_hours: float  # Age of results in hours
    tier_info: Optional[dict] = None  # Information about current tier
    results_remaining: int  # Number of results remaining for user
    posts_remaining: int  # Number of posts remaining for user (budget tracking)
    posts_analyzed: int  # Posts analyzed in this search
    search_metrics: Optional[dict] = None  # Detailed metrics for this search

@router.get("/debug/test")
async def debug_test():
    """Simple debug endpoint to test basic functionality"""
    try:
        from app.services.reddit_service import RedditService
        from app.services.fast_lead_filter import FastLeadFilter
        from app.services.tiered_subreddit_mapping import get_beta_info
        
        # Test basic components
        reddit_service = RedditService()
        lead_filter = FastLeadFilter()
        beta_info = get_beta_info('SaaS Companies')
        
        # Test a simple Reddit fetch
        posts = reddit_service.fetch_posts_from_subreddit('SaaS', limit=5, time_range='all_time')
        
        # Test filtering
        leads = lead_filter.filter_posts(posts, 'struggling to get customers', 'SaaS Companies', 'all_time')
        
        return {
            "status": "success",
            "reddit_posts": len(posts),
            "filtered_leads": len(leads),
            "beta_info": beta_info,
            "message": "All components working"
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.post("/search", response_model=LeadSearchResponse)
async def search_leads(request: LeadSearchRequest, db: Session = Depends(get_db)):
    """Search for leads based on business/industry selection and problem description"""
    logger.info(f"Received lead search request: business='{request.business}', industry='{request.industry}', problem='{request.problem_description}', result_count={request.result_count}")
    
    # Validate that either business or industry is selected (but not both)
    if not request.business and not request.industry:
        raise HTTPException(status_code=400, detail="Either business or industry must be selected")
    
    if request.business and request.industry:
        raise HTTPException(status_code=400, detail="Cannot select both business and industry")
    
    if not request.problem_description.strip():
        raise HTTPException(status_code=400, detail="Problem description is required")
    
    # Validate result count
    if request.result_count < 1 or request.result_count > 150:
        raise HTTPException(status_code=400, detail="Result count must be between 1 and 150")
    
    # Check user usage if user_id is provided
    results_remaining = 150  # Default for anonymous users
    posts_remaining = 2250  # Default for anonymous users
    posts_needed = get_posts_to_scrape(request.result_count)
    
    if request.user_id:
        try:
            user = db.query(User).filter(User.id == int(request.user_id)).first()
            if user:
                # Validate user limits using cost calculator
                is_valid, error_msg, _, remaining_results, remaining_posts = validate_user_limits(
                    user.results_used, user.posts_analyzed, request.result_count
                )
                
                if not is_valid:
                    raise HTTPException(status_code=400, detail=error_msg)
                
                results_remaining = remaining_results
                posts_remaining = remaining_posts
        except (ValueError, TypeError):
            # Invalid user_id format, continue as anonymous user
            pass
    
    try:
        # Initialize services
        reddit_service = RedditService()
        lead_filter = FastLeadFilter()
        
        # Get beta subreddits for the business type
        business_type = request.business or request.industry
        print(f"🚀 BETA ROUTER DEBUG: About to call get_beta_subreddits with business_type='{business_type}'")
        
        # Get beta information for response
        beta_info = get_beta_info(business_type)
        subreddits = beta_info["subreddits"]
        
        print(f"🚀 BETA ROUTER DEBUG: Got subreddits: {subreddits}")
        logger.info(f"Beta Search: Searching in {len(subreddits)} subreddits: {subreddits}")
        
        # Beta quality notice
        quality_notice = f" (Beta Quality - {beta_info['quality_note']})"
        
        # Initialize filter_metrics to avoid NameError
        filter_metrics = None
        
        # Check cache first
        cached_result = result_cache.get_cached_results(
            request.problem_description, 
            business_type, 
            "all_time",  # Fixed time range for beta
            request.user_id or "anonymous",
            request.result_count  # Include result_count in cache key
        )
        
        if cached_result is not None:
            # Return cached results
            leads, result_age_hours = cached_result
            logger.info(f"📦 Using cached results (age: {result_age_hours:.1f} hours)")
            # Set default metrics for cached results
            filter_metrics = {
                "tokens_used": 0,
                "cost": 0.0,
                "model_used": "cached",
                "posts_analyzed": 0,
                "results_returned": len(leads)
            }
        else:
            # Fetch fresh results with calculated posts needed
            posts_per_sub = max(1, posts_needed // len(subreddits))  # Distribute posts across subreddits
            logger.info(f"🔄 Fetching fresh results from Reddit: {posts_needed} total posts ({posts_per_sub} per sub)")
            posts = reddit_service.fetch_posts_from_multiple_subreddits(
                subreddits, 
                query=request.problem_description,
                limit_per_sub=posts_per_sub,  # Dynamic limit based on 15:1 ratio
                time_range="all_time"  # Fixed time range for beta
            )
            
            logger.info(f"Fetched {len(posts)} total posts from Reddit")
            
            # Filter posts using fast lead filter
            leads, filter_metrics = lead_filter.filter_posts(posts, request.problem_description, business_type)
            if filter_metrics:
                logger.info(f"📊 Filter metrics: {filter_metrics}")
            
            # Target custom result count (AI will return best available)
            target_leads = leads[:request.result_count]
            
            # Cache the results
            result_cache.cache_results(
                request.problem_description,
                business_type,
                "all_time",
                request.user_id or "anonymous",
                (target_leads, 0.0),  # Cache with fresh age
                request.result_count  # Include result_count in cache key
            )
            
            result_age_hours = 0.0  # Fresh results
        
        # Update user usage tracking - deduct exactly what was requested
        final_results_count = len(target_leads if 'target_leads' in locals() else leads)
        
        # Track detailed metrics for this search
        search_start_time = time.time()
        total_tokens_used = 0
        total_cost = 0.0
        
        # Try to extract OpenAI metrics from the lead filter
        try:
            # Get metrics from OpenAI service if available
            if hasattr(lead_filter, 'openai_service') and lead_filter.openai_service:
                # This would need to be implemented in the OpenAI service to return cumulative metrics
                pass
        except Exception as e:
            logger.warning(f"Could not extract OpenAI metrics: {e}")
        
        if request.user_id:
            try:
                # Try to find user in database first (for authenticated users)
                user = db.query(User).filter(User.id == int(request.user_id)).first()
                if user:
                    # Update both results and posts analyzed - deduct what was REQUESTED, not what was returned
                    user.results_used += request.result_count  # Deduct what user requested
                    user.posts_analyzed += posts_needed  # Track actual posts analyzed
                    user.total_tokens_used += total_tokens_used
                    user.total_cost += total_cost
                    db.commit()
                    
                    # Recalculate remaining after update
                    results_remaining = 150 - user.results_used
                    posts_remaining = 2250 - user.posts_analyzed
                    
                    logger.info(f"Updated authenticated user {user.id} usage: {user.results_used}/150 results, {user.posts_analyzed}/2250 posts analyzed (deducted {request.result_count} requested results)")
                else:
                    # Anonymous user - return default usage data (frontend will handle tracking)
                    logger.info(f"Anonymous user {request.user_id} - usage tracking handled by frontend")
                    results_remaining = 150  # Default for anonymous users
                    posts_remaining = 2250   # Default for anonymous users
            except (ValueError, TypeError):
                # Invalid user ID format - treat as anonymous
                logger.info(f"Invalid user ID format {request.user_id} - treating as anonymous")
                results_remaining = 150
                posts_remaining = 2250
        
        # Create detailed search metrics record
        search_duration_ms = int((time.time() - search_start_time) * 1000)
        
        # Use filter metrics if available, otherwise fallback to default values
        if filter_metrics:
            tokens_used = filter_metrics.get("tokens_used", 0)
            cost = filter_metrics.get("cost", 0.0)
            model_used = filter_metrics.get("model_used", "unknown")
            posts_analyzed = filter_metrics.get("posts_analyzed", posts_needed)
        else:
            tokens_used = 0
            cost = 0.0
            model_used = "unknown"
            posts_analyzed = posts_needed
        
        try:
            search_metrics = SearchMetrics(
                user_id=int(request.user_id) if request.user_id and request.user_id.isdigit() else None,
                user_session_id=request.user_id if not (request.user_id and request.user_id.isdigit()) else None,
                problem_description=request.problem_description,
                business_type=business_type,
                result_count_requested=request.result_count,
                result_count_returned=final_results_count,
                posts_scraped=len(posts) if 'posts' in locals() else 0,
                posts_analyzed=posts_analyzed,
                tokens_used=tokens_used,
                cost=cost,
                model_used=model_used,
                search_duration_ms=search_duration_ms
            )
            db.add(search_metrics)
            db.commit()
            logger.info(f"📊 Search metrics recorded: {final_results_count} results, {posts_analyzed} posts, {tokens_used} tokens, ${cost:.4f}")
        except Exception as e:
            logger.error(f"Failed to record search metrics: {e}")
            # Don't fail the search if metrics recording fails
        
        # Add timestamp information
        current_timestamp = time.time()
        
        selection_type = request.business or request.industry
        return LeadSearchResponse(
            leads=target_leads if 'target_leads' in locals() else leads,
            total_found=final_results_count,
            message=f"Found {final_results_count} high-quality leads for '{selection_type}' with problem: '{request.problem_description}'{quality_notice}",
            timestamp=current_timestamp,
            result_age_hours=result_age_hours,
            tier_info=beta_info,
            results_remaining=results_remaining,
            posts_remaining=posts_remaining,
            posts_analyzed=posts_analyzed,
            search_metrics={
                "tokens_used": tokens_used,
                "cost": round(cost, 4),
                "model_used": model_used,
                "search_duration_ms": search_duration_ms,
                "posts_scraped": len(posts) if 'posts' in locals() else 0,
                "posts_analyzed": posts_analyzed
            }
        )
        
    except Exception as e:
        logger.error(f"Error in lead search: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/business-options")
async def get_business_options():
    """Get available business options"""
    return {"businesses": get_business_mapping_options()}

@router.get("/industry-options")
async def get_industry_options():
    """Get available industry options"""
    return {"industries": get_industry_mapping_options()}

@router.get("/usage/{user_id}")
async def get_user_usage(user_id: int, db: Session = Depends(get_db)):
    """Get comprehensive user usage statistics including budget tracking"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Use the comprehensive usage summary
        usage_summary = get_user_usage_summary(user.results_used, user.posts_analyzed)
        
        return {
            "user_id": user.id,
            **usage_summary
        }
    except Exception as e:
        logger.error(f"Error getting user usage: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "leads"}

@router.get("/debug/tiered-system")
async def debug_tiered_system():
    """Debug endpoint to test tiered system"""
    try:
        from app.services.tiered_subreddit_mapping import get_tiered_subreddits
        tier_1 = get_tiered_subreddits("SaaS Companies", 1)
        tier_2 = get_tiered_subreddits("SaaS Companies", 2)
        return {
            "status": "success",
            "tier_1": tier_1,
            "tier_2": tier_2,
            "message": "Tiered system is working"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Tiered system has an error"
        }

@router.get("/debug/cache-stats")
async def debug_cache_stats():
    """Debug endpoint to check cache statistics"""
    try:
        stats = result_cache.get_cache_stats()
        return {
            "status": "success",
            "cache_stats": stats,
            "message": "Cache statistics retrieved"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Cache stats error"
        }

@router.get("/api/debug/ai-config")
async def debug_ai_config():
    """Debug endpoint to check current AI configuration"""
    try:
        from app.core.ai_config import get_ai_config
        # from app.services.fast_lead_filter import FastLeadFilter
        
        ai_config = get_ai_config()
        filter_instance = LeadFilter()
        
        return {
            "status": "success",
            "ai_config": ai_config,
            "filter_instance": {
                "use_openai": filter_instance.use_openai,
                "use_improved_ai": filter_instance.use_improved_ai,
                "ai_threshold": filter_instance.ai_threshold,
                "openai_available": filter_instance.openai_service is not None,
                "ai_enhancer_available": filter_instance.ai_enhancer is not None,
                "simple_filter_available": filter_instance.simple_filter is not None
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Debug config error"
        }