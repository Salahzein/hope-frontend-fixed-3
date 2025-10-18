from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# Simplified subreddit mappings for beta launch
# 3 primary subreddits + 1 backup per business/industry type
SIMPLIFIED_SUBREDDIT_MAPPINGS: Dict[str, Dict[str, List[str]]] = {
    # Business Types (Specific)
    "SaaS Companies": {
        "primary": ["SaaS", "startups", "Entrepreneur"],
        "backup": ["IndieDev"]
    },
    "App Developers": {
        "primary": ["SaaS", "startups", "Entrepreneur"],
        "backup": ["IndieDev"]
    },
    "Gyms / Fitness Studios": {
        "primary": ["FitnessBusiness", "GymOwners", "PersonalTraining"],
        "backup": ["Fitness"]
    },
    "E-commerce Stores": {
        "primary": ["ecommerce", "dropshipping", "Shopify"],
        "backup": ["Entrepreneur"]
    },
    "Marketing Agencies": {
        "primary": ["marketing", "SEO", "digital_marketing"],
        "backup": ["advertising"]
    },
    "Freelance Designers": {
        "primary": ["freelance", "graphic_design", "Design"],
        "backup": ["DesignCritiques"]
    },
    "Coffee Shops / Cafés": {
        "primary": ["CoffeeShopOwners", "Coffee", "Barista"],
        "backup": ["CoffeeShopOwners"]
    },
    "Online Course Creators": {
        "primary": ["online_instructors", "InstructionalDesign", "edtech"],
        "backup": ["elearning"]
    },
    "Local Service Businesses": {
        "primary": ["smallbusiness", "Entrepreneur", "LocalSEO"],
        "backup": ["ppc"]
    },
    "Consultants / Coaches": {
        "primary": ["consulting", "Coaching", "Entrepreneur"],
        "backup": ["consultants"]
    },
    "Jobs and Hiring": {
        "primary": ["jobs", "jobhunting", "layoffs"],
        "backup": ["WorkOnline"]
    },
    
    # Industry Types (Broader)
    "Fitness": {
        "primary": ["FitnessBusiness", "GymOwners", "PersonalTraining"],
        "backup": ["Fitness"]
    },
    "SaaS / Tech": {
        "primary": ["SaaS", "startups", "Entrepreneur"],
        "backup": ["IndieDev"]
    },
    "E-commerce": {
        "primary": ["ecommerce", "dropshipping", "Shopify"],
        "backup": ["Entrepreneur"]
    },
    "Marketing & Advertising": {
        "primary": ["marketing", "SEO", "digital_marketing"],
        "backup": ["advertising"]
    },
    "Education / Edtech": {
        "primary": ["online_instructors", "InstructionalDesign", "edtech"],
        "backup": ["elearning"]
    },
    "Food & Beverage": {
        "primary": ["CoffeeShopOwners", "Coffee", "Barista"],
        "backup": ["CoffeeShopOwners"]
    },
    "Local Services": {
        "primary": ["smallbusiness", "Entrepreneur", "LocalSEO"],
        "backup": ["ppc"]
    },
    "Finance / Fintech": {
        "primary": ["Fintech", "PersonalFinance", "FinancialPlanning"],
        "backup": ["Investing"]
    },
    "Freelancers / Creatives": {
        "primary": ["freelance", "graphic_design", "Design"],
        "backup": ["DesignCritiques"]
    },
    "Consulting / Coaching": {
        "primary": ["consulting", "Coaching", "Entrepreneur"],
        "backup": ["consultants"]
    }
}

# In-memory storage for user request counts
user_request_counts: Dict[str, int] = {}

def get_beta_subreddits(business_type: str, use_backup: bool = False) -> List[str]:
    """Get subreddits for beta launch - 3 primary + optional backup"""
    logger.info(f"🔍 BETA SYSTEM: business_type='{business_type}', use_backup={use_backup}")
    print(f"🔍 BETA SYSTEM DEBUG: business_type='{business_type}', use_backup={use_backup}")
    
    if business_type not in SIMPLIFIED_SUBREDDIT_MAPPINGS:
        logger.warning(f"❌ Business type '{business_type}' not found in beta mappings, using fallback")
        print(f"❌ BETA SYSTEM DEBUG: Business type '{business_type}' not found in beta mappings, using fallback")
        from app.services.business_mapping import get_subreddits_for_business
        fallback_subreddits = get_subreddits_for_business(business_type)[:3]  # Take first 3
        print(f"🔄 BETA SYSTEM DEBUG: Fallback subreddits: {fallback_subreddits}")
        return fallback_subreddits
    
    mapping = SIMPLIFIED_SUBREDDIT_MAPPINGS[business_type]
    subreddits = mapping["primary"].copy()
    
    if use_backup:
        subreddits.extend(mapping["backup"])
    
    logger.info(f"✅ BETA SYSTEM: Using subreddits: {subreddits}")
    print(f"✅ BETA SYSTEM DEBUG: Using subreddits: {subreddits}")
    return subreddits

# Keep old function for backward compatibility but redirect to new system
def get_tiered_subreddits(business_type: str, request_number: int) -> List[str]:
    """Legacy function - redirects to new beta system"""
    return get_beta_subreddits(business_type, use_backup=False)

def get_user_request_count(user_id: str) -> int:
    """Get the current request count for a user"""
    return user_request_counts.get(user_id, 0)

def increment_user_request_count(user_id: str) -> int:
    """Increment and return the request count for a user"""
    user_request_counts[user_id] = user_request_counts.get(user_id, 0) + 1
    return user_request_counts[user_id]

def reset_user_request_count(user_id: str):
    """Reset the request count for a user"""
    if user_id in user_request_counts:
        del user_request_counts[user_id]

def get_current_tier(business_type: str, request_number: int) -> int:
    """Get the current tier number for display purposes"""
    if business_type not in TIERED_SUBREDDIT_MAPPINGS:
        return 1  # Default to tier 1 if business type not found
    return min(request_number, 4)  # Ensure tier doesn't exceed 4

def get_beta_info(business_type: str) -> Dict[str, any]:
    """Get beta system information including subreddits and quality note"""
    subreddits = get_beta_subreddits(business_type, use_backup=False)
    
    return {
        "tier": 1,  # Always tier 1 for beta (highest quality)
        "subreddits": subreddits,
        "quality_note": "Beta Quality - Most relevant subreddits for optimal results",
        "is_final_tier": True,
        "posts_per_subreddit": 500,
        "total_posts": len(subreddits) * 500
    }

# Keep old function for backward compatibility
def get_tier_info(business_type: str, request_number: int) -> Dict[str, any]:
    """Legacy function - redirects to new beta system"""
    return get_beta_info(business_type)
