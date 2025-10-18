"""
Cost and Usage Calculator for Beta Users
Handles consistent post-to-result ratios and budget tracking
"""

def get_posts_to_scrape(result_count: int) -> int:
    """
    Calculate posts to scrape based on consistent 15:1 ratio
    This ensures predictable costs and fair resource allocation
    
    Args:
        result_count: Number of results user wants (1-150)
    
    Returns:
        Number of posts to scrape from Reddit
    
    Examples:
        - 20 results = 300 posts (15:1 ratio)
        - 50 results = 750 posts (15:1 ratio)
        - 100 results = 1500 posts (15:1 ratio)
        - 150 results = 2250 posts (15:1 ratio)
    """
    return result_count * 15

def get_estimated_cost(result_count: int) -> float:
    """
    Estimate cost based on posts analyzed (for internal tracking)
    
    Args:
        result_count: Number of results requested
    
    Returns:
        Estimated cost in USD
    """
    posts_analyzed = get_posts_to_scrape(result_count)
    # Rough estimate: $0.002 per post analyzed
    return posts_analyzed * 0.002

def validate_user_limits(user_results_used: int, user_posts_analyzed: int, 
                        requested_results: int) -> tuple[bool, str, int, int]:
    """
    Validate if user can make the requested search within their limits
    
    Args:
        user_results_used: Total results user has already used
        user_posts_analyzed: Total posts user has already analyzed
        requested_results: Results user is requesting now
    
    Returns:
        (is_valid, error_message, posts_needed, remaining_results, remaining_posts)
    """
    MAX_RESULTS = 150
    MAX_POSTS = 2250  # 150 results * 15 ratio
    
    posts_needed = get_posts_to_scrape(requested_results)
    
    # Check results limit
    if user_results_used + requested_results > MAX_RESULTS:
        remaining_results = MAX_RESULTS - user_results_used
        return False, f"Request would exceed beta limit. You have {remaining_results} results remaining, but requested {requested_results}", posts_needed, remaining_results, MAX_POSTS - user_posts_analyzed
    
    # Check posts limit (more important for budget)
    if user_posts_analyzed + posts_needed > MAX_POSTS:
        remaining_posts = MAX_POSTS - user_posts_analyzed
        max_results_with_remaining_posts = remaining_posts // 15
        return False, f"Request would exceed budget limit. You have {remaining_posts} posts remaining (max {max_results_with_remaining_posts} results), but requested {requested_results} results", posts_needed, MAX_RESULTS - user_results_used, remaining_posts
    
    # Calculate remaining after this request
    new_results_used = user_results_used + requested_results
    new_posts_analyzed = user_posts_analyzed + posts_needed
    
    remaining_results = MAX_RESULTS - new_results_used
    remaining_posts = MAX_POSTS - new_posts_analyzed
    
    return True, "Valid request", posts_needed, remaining_results, remaining_posts

def get_user_usage_summary(user_results_used: int, user_posts_analyzed: int) -> dict:
    """
    Get comprehensive usage summary for a user
    
    Args:
        user_results_used: Total results user has used
        user_posts_analyzed: Total posts user has analyzed
    
    Returns:
        Dictionary with usage summary
    """
    MAX_RESULTS = 150
    MAX_POSTS = 2250
    
    results_remaining = MAX_RESULTS - user_results_used
    posts_remaining = MAX_POSTS - user_posts_analyzed
    
    return {
        "results_used": user_results_used,
        "results_remaining": results_remaining,
        "results_limit": MAX_RESULTS,
        "results_percentage": round((user_results_used / MAX_RESULTS) * 100, 1),
        
        "posts_analyzed": user_posts_analyzed,
        "posts_remaining": posts_remaining,
        "posts_limit": MAX_POSTS,
        "posts_percentage": round((user_posts_analyzed / MAX_POSTS) * 100, 1),
        
        "estimated_cost_used": round(get_estimated_cost(user_results_used), 2),
        "estimated_cost_remaining": round(get_estimated_cost(results_remaining), 2),
        "max_estimated_cost": round(get_estimated_cost(MAX_RESULTS), 2)
    }
