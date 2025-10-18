"""
Business-specific keyword mappings for AI scoring
Each business/industry has specific keywords that indicate relevance
"""

from typing import Dict, List

# Business-specific keyword mappings (specific businesses)
BUSINESS_KEYWORDS: Dict[str, List[str]] = {
    "Gyms / Fitness Studios": [
        "gym", "fitness", "trainer", "workout", "members", "membership", "exercise", 
        "personal training", "fitness studio", "gym owner", "fitness business", 
        "personal trainer", "workout studio", "fitness center", "health club"
    ],
    "SaaS Companies": [
        "saas", "software", "app", "application", "platform", "subscription", "mrr", "arr", 
        "api", "dashboard", "tech", "startup", "software company", "web app", "mobile app", 
        "cloud", "b2b", "enterprise", "integration", "automation"
    ],
    "E-commerce Stores": [
        "ecommerce", "shopify", "amazon", "etsy", "store", "products", "inventory", 
        "shipping", "retail", "online store", "dropshipping", "fulfillment", "merchandise", 
        "marketplace", "seller", "vendor", "product catalog"
    ],
    "Marketing Agencies": [
        "agency", "client", "campaign", "creative", "brand", "marketing", "seo", "ppc", 
        "advertising", "digital marketing", "social media", "content marketing", "email marketing", 
        "marketing agency", "ad agency", "creative agency", "marketing services"
    ],
    "Freelance Designers": [
        "freelance", "designer", "design", "graphic design", "ui", "ux", "logo", "branding", 
        "visual", "creative", "portfolio", "client work", "design project", "freelance designer", 
        "graphic designer", "web design"
    ],
    "Coffee Shops / Cafés": [
        "coffee", "cafe", "café", "coffee shop", "barista", "espresso", "latte", "coffee business", 
        "cafe owner", "coffee shop owner", "roastery", "coffee roaster", "coffee house", "beverage"
    ],
    "Online Course Creators": [
        "course", "online course", "education", "teaching", "learning", "student", "curriculum", 
        "course creator", "online education", "elearning", "training", "workshop", "tutorial", 
        "educational content", "course platform"
    ],
    "Local Service Businesses": [
        "local business", "service business", "contractor", "plumber", "electrician", "handyman", 
        "home improvement", "local services", "service provider", "home services", "maintenance", 
        "repair", "installation", "local contractor"
    ],
    "App Developers": [
        "app developer", "mobile app", "ios", "android", "app development", "programming", 
        "coding", "developer", "software developer", "app store", "mobile development", 
        "app creation", "app building", "mobile app developer"
    ],
    "Consultants / Coaches": [
        "consultant", "coach", "consulting", "coaching", "advisor", "mentor", "business coach", 
        "life coach", "consulting business", "coaching business", "professional services", 
        "business advisor", "strategy consultant"
    ]
}

# Industry-specific keyword mappings (broader categories)
INDUSTRY_KEYWORDS: Dict[str, List[str]] = {
    "Fitness": [
        "fitness", "gym", "workout", "exercise", "training", "health", "wellness", "personal training", 
        "fitness business", "gym owner", "fitness studio", "health club", "fitness center"
    ],
    "SaaS / Tech": [
        "saas", "software", "tech", "technology", "app", "application", "platform", "startup", 
        "software company", "tech company", "web app", "mobile app", "cloud", "b2b", "enterprise"
    ],
    "E-commerce": [
        "ecommerce", "online store", "retail", "shopping", "products", "marketplace", "seller", 
        "vendor", "shopify", "amazon", "etsy", "dropshipping", "fulfillment", "merchandise"
    ],
    "Marketing & Advertising": [
        "marketing", "advertising", "agency", "digital marketing", "social media", "seo", "ppc", 
        "content marketing", "email marketing", "brand", "campaign", "creative", "marketing agency"
    ],
    "Education / Edtech": [
        "education", "learning", "teaching", "course", "online course", "student", "elearning", 
        "training", "workshop", "tutorial", "educational", "course creator", "online education"
    ],
    "Food & Beverage": [
        "food", "restaurant", "cafe", "coffee", "beverage", "dining", "food business", "restaurant owner", 
        "coffee shop", "cafe owner", "food service", "culinary", "catering", "food truck"
    ],
    "Local Services": [
        "local business", "service", "contractor", "home improvement", "maintenance", "repair", 
        "installation", "local services", "service provider", "home services", "local contractor"
    ],
    "Finance / Fintech": [
        "finance", "financial", "fintech", "banking", "investment", "money", "financial services", 
        "fintech company", "financial advisor", "investment", "trading", "cryptocurrency", "fintech"
    ],
    "Freelancers / Creatives": [
        "freelance", "freelancer", "creative", "design", "designer", "artist", "creative services", 
        "freelance work", "creative business", "design business", "creative professional"
    ],
    "Consulting / Coaching": [
        "consulting", "coaching", "consultant", "coach", "advisor", "mentor", "professional services", 
        "business consulting", "life coaching", "business coach", "strategy consultant", "business advisor"
    ]
}

def get_keywords_for_business(business_type: str) -> List[str]:
    """Get keywords for a specific business type"""
    return BUSINESS_KEYWORDS.get(business_type, [])

def get_keywords_for_industry(industry_type: str) -> List[str]:
    """Get keywords for a specific industry type"""
    return INDUSTRY_KEYWORDS.get(industry_type, [])

def get_keywords_for_selection(business: str = None, industry: str = None) -> List[str]:
    """Get keywords based on business or industry selection"""
    if business:
        return get_keywords_for_business(business)
    elif industry:
        return get_keywords_for_industry(industry)
    else:
        return []  # No keywords if no selection

def calculate_business_relevance_score(post_text: str, target_keywords: List[str]) -> int:
    """Calculate how well a post matches the target business/industry keywords"""
    if not target_keywords:
        return 0
    
    post_lower = post_text.lower()
    matches = sum(1 for keyword in target_keywords if keyword in post_lower)
    
    # Calculate percentage of keywords matched
    match_percentage = (matches / len(target_keywords)) * 100
    
    # Boost score for multiple matches
    if matches >= 3:
        match_percentage += 20  # Bonus for multiple keyword matches
    elif matches >= 2:
        match_percentage += 10  # Small bonus for 2+ matches
    
    return min(100, int(match_percentage))
