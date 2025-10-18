import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
from app.services.business_keywords import get_keywords_for_selection, calculate_business_relevance_score, BUSINESS_KEYWORDS, INDUSTRY_KEYWORDS

logger = logging.getLogger(__name__)

@dataclass
class EnhancedQuery:
    original_problem: str
    enhanced_problem: str
    keywords: List[str]
    business_context: str
    urgency_indicators: List[str]

@dataclass
class RelevanceScore:
    overall_score: int  # 0-100
    keyword_match: int  # 0-100
    struggle_detection: int  # 0-100
    business_relevance: int  # 0-100
    urgency_level: str  # "High", "Medium", "Low"

@dataclass
class BusinessContext:
    business_type: str
    problem_category: str
    specific_issues: List[str]
    confidence: float

class AIEnhancer:
    """
    AI-powered service for enhancing search queries and analyzing content relevance.
    Uses Cursor's AI capabilities to improve lead finding accuracy.
    """
    
    def __init__(self, use_improved_scoring: bool = True):
        logger.info(f"AIEnhancer initialized. Using {'improved' if use_improved_scoring else 'original'} AI scoring.")
        self.use_improved_scoring = use_improved_scoring
        
        # Enhanced struggle indicators with context
        self.struggle_indicators = {
            "high_urgency": [
                "struggling", "struggle", "desperate", "urgent", "failing", "lost",
                "can't", "cannot", "can not", "help", "advice", "stuck", "frustrated",
                "overwhelmed", "declining", "losing", "first client", "first customer",
                "no customers", "no clients", "getting clients", "customer acquisition",
                "lead generation", "need help", "looking for", "how to", "what should",
                "any advice", "trouble", "problem", "issue"
            ],
            "medium_urgency": [
                "challenging", "difficult", "hard", "tough", "slow", "low", "few",
                "not enough", "lack of", "need more", "want to improve", "trying to",
                "working on", "focusing on"
            ],
            "business_keywords": [
                "revenue", "sales", "profit", "growth", "marketing", "advertising",
                "clients", "customers", "leads", "conversion", "retention", "churn",
                "pricing", "competition", "market", "brand", "website", "online",
                "digital", "social media", "email", "content", "seo", "ppc"
            ]
        }
        
        # Business context patterns
        self.business_patterns = {
            "saas": ["saas", "software", "app", "platform", "subscription", "mrr", "arr"],
            "ecommerce": ["ecommerce", "shopify", "amazon", "etsy", "store", "products", "inventory"],
            "agency": ["agency", "client", "campaign", "creative", "brand", "marketing"],
            "fitness": ["gym", "fitness", "trainer", "workout", "members", "membership"],
            "consulting": ["consulting", "consultant", "client", "project", "strategy"],
            "freelance": ["freelance", "freelancer", "client", "project", "gig"]
        }
        
        # Success story patterns to penalize (NEW)
        self.success_story_patterns = {
            "revenue_indicators": ["hit $", "made $", "reached $", "grew to $", "earned $", "revenue", "mrr", "arr"],
            "success_phrases": ["here's what worked", "here's how i", "my advice is", "try this", "what you should do"],
            "past_tense_success": ["i grew", "i built", "i launched", "i created", "i developed", "i achieved"],
            "teaching_indicators": ["here's what", "let me share", "i want to tell", "here's my story", "here's how"],
            "promotion_indicators": ["i will not promote", "not promoting", "no promotion"]
        }
        
        # Active struggle patterns to boost (NEW)
        self.active_struggle_patterns = {
            "present_tense_questions": ["how do i", "what should i", "any advice", "can someone help", "need help with"],
            "current_problems": ["i'm struggling", "i can't", "i need help", "stuck with", "can't figure out"],
            "direct_help_requests": ["help me", "advice needed", "any suggestions", "what should i do"]
        }

    def enhance_query(self, problem: str, business_type: str) -> EnhancedQuery:
        """
        Enhance the user's problem description using AI to extract better keywords
        and understand the business context.
        """
        try:
            # Extract keywords from the problem
            keywords = self._extract_keywords(problem)
            
            # Enhance the problem description
            enhanced_problem = self._enhance_problem_description(problem, business_type)
            
            # Detect urgency indicators
            urgency_indicators = self._detect_urgency_indicators(problem)
            
            # Determine business context
            business_context = self._determine_business_context(problem, business_type)
            
            return EnhancedQuery(
                original_problem=problem,
                enhanced_problem=enhanced_problem,
                keywords=keywords,
                business_context=business_context,
                urgency_indicators=urgency_indicators
            )
            
        except Exception as e:
            logger.error(f"Error enhancing query: {e}")
            # Fallback to basic processing
            return EnhancedQuery(
                original_problem=problem,
                enhanced_problem=problem,
                keywords=self._extract_keywords(problem),
                business_context=business_type,
                urgency_indicators=[]
            )

    def analyze_post_relevance(self, post: Dict[str, Any], keywords: List[str], business_type: str = None, industry_type: str = None) -> RelevanceScore:
        """
        Analyze a Reddit post to determine its relevance using AI-powered scoring.
        """
        try:
            post_text = f"{post.get('title', '')} {post.get('text', '')}".lower()
            
            # Calculate keyword match score
            keyword_score = self._calculate_keyword_match(post_text, keywords)
            
            # Calculate struggle detection score
            struggle_score = self._calculate_struggle_detection(post_text)
            
            # Calculate business relevance score using business-specific keywords
            business_score = self._calculate_business_relevance(post_text, business_type, industry_type)
            
            # Determine urgency level
            urgency_level = self._determine_urgency_level(post_text)
            
            # Calculate overall score (weighted average)
            if self.use_improved_scoring:
                # IMPROVED WEIGHTS: Prioritize struggle detection
                overall_score = int(
                    (keyword_score * 0.3) + 
                    (struggle_score * 0.6) + 
                    (business_score * 0.1)
                )
            else:
                # ORIGINAL WEIGHTS
                overall_score = int(
                    (keyword_score * 0.4) + 
                    (struggle_score * 0.4) + 
                    (business_score * 0.2)
                )
            
            return RelevanceScore(
                overall_score=overall_score,
                keyword_match=keyword_score,
                struggle_detection=struggle_score,
                business_relevance=business_score,
                urgency_level=urgency_level
            )
            
        except Exception as e:
            logger.error(f"Error analyzing post relevance: {e}")
            return RelevanceScore(
                overall_score=0,
                keyword_match=0,
                struggle_detection=0,
                business_relevance=0,
                urgency_level="Low"
            )

    def extract_business_context(self, post_text: str) -> BusinessContext:
        """
        Extract business context from a post to understand what type of business
        and what specific problems are mentioned.
        """
        try:
            text_lower = post_text.lower()
            
            # Determine business type
            business_type = self._identify_business_type(text_lower)
            
            # Identify problem category
            problem_category = self._identify_problem_category(text_lower)
            
            # Extract specific issues
            specific_issues = self._extract_specific_issues(text_lower)
            
            # Calculate confidence
            confidence = self._calculate_context_confidence(text_lower, business_type)
            
            return BusinessContext(
                business_type=business_type,
                problem_category=problem_category,
                specific_issues=specific_issues,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error extracting business context: {e}")
            return BusinessContext(
                business_type="Unknown",
                problem_category="General",
                specific_issues=[],
                confidence=0.0
            )

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        # Remove common stopwords and extract meaningful words
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "cannot"}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if word not in stopwords and len(word) > 2]
        
        return list(set(keywords))  # Remove duplicates

    def _enhance_problem_description(self, problem: str, business_type: str) -> str:
        """Enhance the problem description with related terms."""
        # This is where we would use Cursor's AI to enhance the description
        # For now, we'll use a rule-based approach
        
        enhancements = {
            "client acquisition": ["customer acquisition", "lead generation", "finding clients", "getting customers"],
            "marketing": ["advertising", "promotion", "brand awareness", "lead generation"],
            "sales": ["revenue", "conversions", "closing deals", "customer acquisition"],
            "growth": ["scaling", "expansion", "increasing revenue", "business development"]
        }
        
        enhanced = problem
        for key, values in enhancements.items():
            if key in problem.lower():
                enhanced += f" {', '.join(values)}"
        
        return enhanced

    def _detect_urgency_indicators(self, text: str) -> List[str]:
        """Detect urgency indicators in the text."""
        found_indicators = []
        text_lower = text.lower()
        
        for category, indicators in self.struggle_indicators.items():
            for indicator in indicators:
                if indicator in text_lower:
                    found_indicators.append(indicator)
        
        return list(set(found_indicators))

    def _determine_business_context(self, problem: str, business_type: str) -> str:
        """Determine the business context from the problem and business type."""
        return f"{business_type} - {problem}"

    def _calculate_keyword_match(self, post_text: str, keywords: List[str]) -> int:
        """Calculate how well the post matches the keywords."""
        if not keywords:
            return 0
        
        matches = sum(1 for keyword in keywords if keyword in post_text)
        return min(100, int((matches / len(keywords)) * 100))

    def _calculate_struggle_detection(self, post_text: str) -> int:
        """Calculate struggle detection score with improved logic."""
        if not self.use_improved_scoring:
            # Original logic
            score = 0
            
            # High urgency indicators
            for indicator in self.struggle_indicators["high_urgency"]:
                if indicator in post_text:
                    score += 20
            
            # Medium urgency indicators
            for indicator in self.struggle_indicators["medium_urgency"]:
                if indicator in post_text:
                    score += 10
            
            # Question marks indicate asking for help
            if "?" in post_text:
                score += 15
            
            return min(100, score)
        
        # IMPROVED LOGIC
        score = 0
        
        # BOOST: Active struggle patterns (+25 points each)
        for category, patterns in self.active_struggle_patterns.items():
            for pattern in patterns:
                if pattern in post_text:
                    score += 25
        
        # BOOST: Original struggle indicators (reduced weight)
        for indicator in self.struggle_indicators["high_urgency"]:
            if indicator in post_text:
                score += 15  # Reduced from 20
        
        for indicator in self.struggle_indicators["medium_urgency"]:
            if indicator in post_text:
                score += 8   # Reduced from 10
        
        # BOOST: Question marks (increased weight)
        if "?" in post_text:
            score += 20  # Increased from 15
        
        # PENALIZE: Success story patterns (-30 points each)
        for category, patterns in self.success_story_patterns.items():
            for pattern in patterns:
                if pattern in post_text:
                    score -= 30
        
        # PENALIZE: Revenue numbers in title (-25 points)
        if re.search(r'\$\d+[k|m]?', post_text):
            score -= 25
        
        # PENALIZE: "I will not promote" (often success stories)
        if "i will not promote" in post_text:
            score -= 15
        
        return max(0, min(100, score))  # Ensure score stays between 0-100

    def _calculate_business_relevance(self, post_text: str, business_type: str = None, industry_type: str = None) -> int:
        """Calculate business relevance score using business-specific keywords."""
        if not self.use_improved_scoring:
            # Original logic - generic business keywords
            score = 0
            for keyword in self.struggle_indicators["business_keywords"]:
                if keyword in post_text:
                    score += 5
            return min(100, score)
        
        # IMPROVED LOGIC - Business-specific keywords
        if not business_type and not industry_type:
            return 0  # No business context, no business relevance
        
        # Get business-specific keywords
        target_keywords = get_keywords_for_selection(business=business_type, industry=industry_type)
        
        if not target_keywords:
            return 0  # No keywords defined for this business/industry
        
        # Calculate relevance using business-specific keywords
        business_relevance = calculate_business_relevance_score(post_text, target_keywords)
        
        # Additional penalty for conflicting business types
        conflict_penalty = self._calculate_business_conflict_penalty(post_text, business_type, industry_type)
        
        final_score = max(0, business_relevance - conflict_penalty)
        return min(100, final_score)
    
    def _calculate_business_conflict_penalty(self, post_text: str, business_type: str, industry_type: str) -> int:
        """Calculate penalty for posts that clearly belong to different business types."""
        penalty = 0
        
        # Get all other business keywords (excluding the target one)
        all_businesses = list(BUSINESS_KEYWORDS.keys()) if business_type else list(INDUSTRY_KEYWORDS.keys())
        target = business_type or industry_type
        
        if target in all_businesses:
            other_businesses = [b for b in all_businesses if b != target]
            
            # Check for strong indicators of other business types
            for other_business in other_businesses[:3]:  # Check top 3 most conflicting
                other_keywords = get_keywords_for_selection(business=other_business) if business_type else get_keywords_for_selection(industry=other_business)
                
                # If post has multiple keywords from a different business type, penalize
                matches = sum(1 for keyword in other_keywords if keyword in post_text)
                if matches >= 2:  # 2+ keywords from different business type
                    penalty += 15
        
        return penalty

    def _determine_urgency_level(self, post_text: str) -> str:
        """Determine the urgency level of the post."""
        high_urgency_count = sum(1 for indicator in self.struggle_indicators["high_urgency"] if indicator in post_text)
        medium_urgency_count = sum(1 for indicator in self.struggle_indicators["medium_urgency"] if indicator in post_text)
        
        if high_urgency_count >= 2:
            return "High"
        elif high_urgency_count >= 1 or medium_urgency_count >= 2:
            return "Medium"
        else:
            return "Low"

    def _identify_business_type(self, text: str) -> str:
        """Identify the business type from the text."""
        for business_type, patterns in self.business_patterns.items():
            if any(pattern in text for pattern in patterns):
                return business_type.title()
        return "General Business"

    def _identify_problem_category(self, text: str) -> str:
        """Identify the problem category."""
        categories = {
            "Client Acquisition": ["client", "customer", "lead", "acquisition", "getting clients"],
            "Marketing": ["marketing", "advertising", "promotion", "brand"],
            "Sales": ["sales", "revenue", "conversion", "closing"],
            "Growth": ["growth", "scaling", "expansion", "development"],
            "Operations": ["operations", "process", "efficiency", "workflow"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return "General Problem"

    def _extract_specific_issues(self, text: str) -> List[str]:
        """Extract specific issues mentioned in the text."""
        issues = []
        
        # Look for common problem patterns
        problem_patterns = [
            r"struggling with (\w+)",
            r"problem with (\w+)",
            r"issue with (\w+)",
            r"trouble with (\w+)",
            r"can't (\w+)",
            r"cannot (\w+)"
        ]
        
        for pattern in problem_patterns:
            matches = re.findall(pattern, text)
            issues.extend(matches)
        
        return list(set(issues))

    def _calculate_context_confidence(self, text: str, business_type: str) -> float:
        """Calculate confidence in the business context analysis."""
        if business_type == "Unknown":
            return 0.0
        
        # Simple confidence calculation based on keyword density
        business_keywords = self.business_patterns.get(business_type.lower(), [])
        if not business_keywords:
            return 0.5
        
        matches = sum(1 for keyword in business_keywords if keyword in text)
        return min(1.0, matches / len(business_keywords))
