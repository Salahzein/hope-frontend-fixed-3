from typing import List, Dict

# Business-specific keyword mappings for content filtering
BUSINESS_MAPPINGS: Dict[str, Dict[str, List[str]]] = {
    "Gyms / Fitness Studios": {
        "keywords": ["gym", "fitness", "workout", "personal training", "fitness studio", "membership", "trainer", "exercise"],
        "subreddits": ["gymowners", "FitnessBusiness", "personaltrainingbiz"]
    },
    "SaaS Companies": {
        "keywords": ["saas", "software", "app", "platform", "subscription", "mrr", "arr", "users", "customers", "startup", "founder"],
        "subreddits": ["SaaS", "startups", "IndieHackers"]
    },
    "E-commerce Stores": {
        "keywords": ["ecommerce", "online store", "shopify", "amazon", "selling", "products", "inventory", "sales", "customers"],
        "subreddits": ["ecommerce", "Shopify", "EntrepreneurRideAlong"]
    },
    "Marketing Agencies": {
        "keywords": ["marketing", "agency", "advertising", "seo", "social media", "campaigns", "clients", "digital marketing"],
        "subreddits": ["agency", "digitalmarketing", "SEO"]
    },
    "Freelance Designers": {
        "keywords": ["freelance", "design", "graphic design", "logo", "branding", "client", "portfolio", "creative"],
        "subreddits": ["freelance", "design", "graphic_design"]
    },
    "Coffee Shops / Cafés": {
        "keywords": ["coffee", "cafe", "restaurant", "food", "beverage", "customers", "menu", "location"],
        "subreddits": ["smallbusiness", "foodbiz", "EntrepreneurRideAlong"]
    },
    "Online Course Creators": {
        "keywords": ["course", "online learning", "education", "teaching", "students", "content", "platform"],
        "subreddits": ["onlinecourses", "edtech", "IndieHackers"]
    },
    "Local Service Businesses": {
        "keywords": ["local business", "service", "contractor", "home improvement", "repair", "cleaning", "maintenance"],
        "subreddits": ["smallbusiness", "HomeImprovement", "EntrepreneurRideAlong"]
    },
    "App Developers": {
        "keywords": ["app", "mobile", "development", "programming", "ios", "android", "users", "downloads"],
        "subreddits": ["startups", "IndieHackers", "EntrepreneurRideAlong"]
    },
    "Consultants / Coaches": {
        "keywords": ["consulting", "coaching", "advisor", "mentor", "client", "consultation", "strategy"],
        "subreddits": ["consulting", "EntrepreneurRideAlong", "indiehackers"]
    },
    "Jobs and Hiring": {
        "keywords": ["job search", "resume help", "interview advice", "job leads", "career change", "unemployment", "job application", "hiring process", "job market", "career advice", "job openings", "job hunting tips"],
        "subreddits": ["jobs", "jobhunting", "layoffs"]
    }
}

# Industry-specific mappings (broader categories)
INDUSTRY_MAPPINGS: Dict[str, Dict[str, List[str]]] = {
    "Fitness": {
        "keywords": ["gym", "fitness", "workout", "personal training", "fitness studio", "membership", "trainer", "exercise"],
        "subreddits": ["gymowners", "FitnessBusiness", "personaltrainingbiz"]
    },
    "SaaS / Tech": {
        "keywords": ["saas", "software", "app", "platform", "subscription", "mrr", "arr", "users", "customers", "startup", "founder"],
        "subreddits": ["SaaS", "startups", "IndieHackers"]
    },
    "E-commerce": {
        "keywords": ["ecommerce", "online store", "shopify", "amazon", "selling", "products", "inventory", "sales", "customers"],
        "subreddits": ["ecommerce", "Shopify", "EntrepreneurRideAlong"]
    },
    "Marketing & Advertising": {
        "keywords": ["marketing", "agency", "advertising", "seo", "social media", "campaigns", "clients", "digital marketing"],
        "subreddits": ["agency", "digitalmarketing", "SEO"]
    },
    "Education / Edtech": {
        "keywords": ["course", "online learning", "education", "teaching", "students", "content", "platform"],
        "subreddits": ["onlinecourses", "edtech", "IndieHackers"]
    },
    "Food & Beverage": {
        "keywords": ["coffee", "cafe", "restaurant", "food", "beverage", "customers", "menu", "location"],
        "subreddits": ["smallbusiness", "foodbiz", "EntrepreneurRideAlong"]
    },
    "Local Services": {
        "keywords": ["local business", "service", "contractor", "home improvement", "repair", "cleaning", "maintenance"],
        "subreddits": ["smallbusiness", "HomeImprovement", "EntrepreneurRideAlong"]
    },
    "Finance / Fintech": {
        "keywords": ["finance", "fintech", "banking", "investment", "money", "financial", "finances"],
        "subreddits": ["financialindependence", "startups", "IndieHackers"]
    },
    "Freelancers / Creatives": {
        "keywords": ["freelance", "design", "graphic design", "logo", "branding", "client", "portfolio", "creative"],
        "subreddits": ["freelance", "design", "graphic_design"]
    }
}

def get_business_options() -> List[str]:
    """Get list of available business options"""
    return list(BUSINESS_MAPPINGS.keys())

def get_industry_options() -> List[str]:
    """Get list of available industry options"""
    return list(INDUSTRY_MAPPINGS.keys())

def get_subreddits_for_business(business_type: str) -> List[str]:
    """Get subreddits for a specific business type"""
    return BUSINESS_MAPPINGS.get(business_type, [])

def get_subreddits_for_industry(industry_type: str) -> List[str]:
    """Get subreddits for a specific industry type"""
    return INDUSTRY_MAPPINGS.get(industry_type, [])

def validate_business_selection(business: str) -> bool:
    """Validate if business selection is valid"""
    return business in BUSINESS_MAPPINGS

def validate_industry_selection(industry: str) -> bool:
    """Validate if industry selection is valid"""
    return industry in INDUSTRY_MAPPINGS
