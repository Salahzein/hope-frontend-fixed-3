"""
Simple Lead Filter - Original High-Quality System
This is the original, effective filtering system that was working well before over-engineering
"""

import re
import logging
from typing import List, Dict, Any, Optional
from app.models.lead import Lead
from app.services.business_keywords import get_keywords_for_selection, calculate_business_relevance_score

logger = logging.getLogger(__name__)

class SimpleLeadFilter:
    """
    Original simple filtering system that was highly effective
    - Direct keyword matching
    - Simple struggle detection
    - Business-specific relevance scoring
    - Higher thresholds for quality
    """
    
    def __init__(self):
        # Original struggle indicators - proven to work well
        self.struggle_indicators = [
            "struggling", "struggle", "help", "advice", "can't", "cannot", "can not",
            "trouble", "problem", "issue", "stuck", "frustrated", "overwhelmed",
            "desperate", "urgent", "failing", "lost", "losing", "declining",
            "first client", "first customer", "no customers", "no clients",
            "getting clients", "customer acquisition", "lead generation",
            "need help", "looking for", "how to", "what should", "any advice"
        ]
    
    def extract_keywords(self, user_input: str) -> List[str]:
        """Extract main keywords from user input - simple and effective"""
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "cannot", "i", "me", "my", "we", "our", "you", "your", "they", "their", "it", "its", "this", "that", "these", "those"}
        
        words = re.findall(r'\b\w+\b', user_input.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        logger.info(f"Extracted keywords from '{user_input}': {keywords}")
        return keywords
    
    def contains_struggle_indicators(self, text: str) -> bool:
        """Check if text contains struggle indicators - must have at least 2"""
        text_lower = text.lower()
        struggle_count = sum(1 for indicator in self.struggle_indicators if indicator in text_lower)
        
        # Must have at least 2 struggle indicators for quality
        has_struggle = struggle_count >= 2
        logger.info(f"Struggle check: Found {struggle_count} indicators, Result: {has_struggle}")
        return has_struggle
    
    def matches_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text matches any of the keywords - simple and direct"""
        if not keywords:
            return True  # If no keywords, match all
        
        text_lower = text.lower()
        matched_keywords = [keyword for keyword in keywords if keyword in text_lower]
        
        has_match = len(matched_keywords) > 0
        logger.info(f"Keyword match: Keywords: {keywords}, Matched: {matched_keywords}, Result: {has_match}")
        return has_match
    
    def calculate_struggle_score(self, text: str) -> int:
        """Calculate struggle score - simple counting"""
        text_lower = text.lower()
        score = 0
        
        # Count struggle indicators
        for indicator in self.struggle_indicators:
            if indicator in text_lower:
                score += 15  # 15 points per indicator
        
        # Bonus for question marks (asking for help)
        if "?" in text:
            score += 10
        
        # Cap at 100
        return min(100, score)
    
    def determine_urgency_level(self, text: str) -> str:
        """Determine urgency level based on struggle indicators"""
        high_urgency_words = ["desperate", "urgent", "failing", "lost", "can't", "cannot", "struggling"]
        medium_urgency_words = ["help", "advice", "trouble", "problem", "issue", "stuck"]
        
        text_lower = text.lower()
        high_count = sum(1 for word in high_urgency_words if word in text_lower)
        medium_count = sum(1 for word in medium_urgency_words if word in text_lower)
        
        if high_count >= 2:
            return "High"
        elif high_count >= 1 or medium_count >= 2:
            return "Medium"
        else:
            return "Low"
    
    def identify_problem_category(self, text: str) -> str:
        """Identify problem category - simple keyword matching"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["client", "customer", "lead", "acquisition"]):
            return "Client Acquisition"
        elif any(word in text_lower for word in ["marketing", "advertising", "promotion", "brand"]):
            return "Marketing"
        elif any(word in text_lower for word in ["sales", "revenue", "conversion", "closing"]):
            return "Sales"
        elif any(word in text_lower for word in ["growth", "scaling", "expansion", "development"]):
            return "Growth"
        else:
            return "General Problem"
    
    def filter_posts(self, posts: List[Dict[str, Any]], user_input: str, business_type: Optional[str] = None, time_range: str = "all_time") -> List[Lead]:
        """
        Filter posts using simple, effective logic
        This is the original system that was working well
        """
        try:
            logger.info(f"Starting simple filtering for {len(posts)} posts")
            
            # Extract keywords from user input
            keywords = self.extract_keywords(user_input)
            
            # Get business-specific keywords
            business_keywords = get_keywords_for_selection(business=business_type) if business_type else []
            
            # Use higher threshold for quality (35+ instead of 20+)
            ai_threshold = 35
            
            logger.info(f"Using simple threshold of {ai_threshold}+ with keywords: {keywords}")
            
            filtered_leads = []
            
            for post in posts:
                # Calculate scores
                struggle_score = self.calculate_struggle_score(post["text"])
                business_score = calculate_business_relevance_score(post["text"], business_keywords) if business_keywords else 50
                
                # Combined score (weighted average) - original formula
                overall_score = int((struggle_score * 0.6) + (business_score * 0.4))
                
                # Only include posts that meet the threshold
                if overall_score >= ai_threshold:
                    logger.info(f"Simple Analysis - Post: {post['title'][:50]}... Score: {overall_score}")
                    
                    # Create snippet (first 200 characters)
                    snippet = post["text"][:200] + "..." if len(post["text"]) > 200 else post["text"]
                    
                    # Find matched keywords for this post
                    text_lower = post["text"].lower()
                    matched_keywords = [keyword for keyword in keywords + business_keywords if keyword in text_lower]
                    
                    lead = Lead(
                        title=post["title"],
                        subreddit=post["subreddit"],
                        snippet=snippet,
                        permalink=post["permalink"],
                        author=post["author"],
                        created_utc=post["created_utc"],
                        score=post["score"],
                        matched_keywords=matched_keywords,
                        ai_relevance_score=overall_score,
                        urgency_level=self.determine_urgency_level(post["text"]),
                        business_context=business_type or "General Business",
                        problem_category=self.identify_problem_category(post["text"])
                    )
                    filtered_leads.append(lead)
            
            # Sort by relevance score (highest first)
            filtered_leads.sort(key=lambda x: x.ai_relevance_score or 0, reverse=True)
            
            # Log score distribution
            if filtered_leads:
                scores = [lead.ai_relevance_score for lead in filtered_leads if lead.ai_relevance_score]
                logger.info(f"Simple filtering: {len(posts)} posts down to {len(filtered_leads)} high-relevance leads")
                logger.info(f"Score distribution: min={min(scores)}, max={max(scores)}, avg={sum(scores)/len(scores):.1f}")
            
            return filtered_leads
            
        except Exception as e:
            logger.error(f"Simple filtering failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
