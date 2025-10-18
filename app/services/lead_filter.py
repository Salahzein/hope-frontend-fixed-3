import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.models.lead import Lead
from app.services.ai_enhancer import AIEnhancer, EnhancedQuery
from app.services.openai_service import OpenAIService, AIAnalysisResult
from app.services.simple_lead_filter import SimpleLeadFilter
from app.core.ai_config import get_ai_config
from app.services.business_mapping import BUSINESS_MAPPINGS, INDUSTRY_MAPPINGS

logger = logging.getLogger(__name__)

# THRESHOLD CONFIGURATION
# Current: 25+ (captures more posts, may be less specific)
# Previous: 35+ (more specific, fewer posts)
# To revert: Change line 75 from ">= 25" to ">= 35"

class LeadFilter:
    def __init__(self):
        # Get AI configuration
        ai_config = get_ai_config()
        self.use_openai = ai_config["use_openai"]
        self.use_improved_ai = ai_config["use_improved_scoring"]
        # Use the configured threshold
        self.ai_threshold = ai_config["threshold"]
        
        # Initialize AI services
        self.ai_enhancer = AIEnhancer(use_improved_scoring=self.use_improved_ai)
        self.openai_service = OpenAIService() if self.use_openai else None
        self.simple_filter = SimpleLeadFilter()  # Original simple system
        
        # Store metrics from last filtering operation
        self._last_metrics = None
        
        # Keep original struggle indicators as fallback
        self.struggle_indicators = [
            "struggling", "struggle", "help", "advice", "can't", "cannot", "can not",
            "trouble", "problem", "issue", "stuck", "frustrated", "overwhelmed",
            "desperate", "urgent", "failing", "lost", "losing", "declining",
            "first client", "first customer", "no customers", "no clients",
            "getting clients", "customer acquisition", "lead generation",
            "need help", "looking for", "how to", "what should", "any advice"
        ]
    
    def filter_posts_by_time_range(self, posts: List[Dict[str, Any]], time_range: str) -> List[Dict[str, Any]]:
        """Filter posts by their actual creation date based on time range (backup filtering)"""
        if not posts:
            return posts
            
        now = datetime.now()
        filtered_posts = []
        
        for post in posts:
            try:
                post_date = datetime.fromtimestamp(post["created_utc"])
                
                if time_range == "today":
                    # Same day (within 24 hours) - more lenient
                    if (now - post_date).days <= 1:  # Allow up to 1 day
                        filtered_posts.append(post)
                elif time_range == "last_week":
                    # Last 7 days - more lenient
                    if (now - post_date).days <= 10:  # Allow up to 10 days
                        filtered_posts.append(post)
                elif time_range == "last_month":
                    # Last 30 days - more lenient
                    if (now - post_date).days <= 45:  # Allow up to 45 days
                        filtered_posts.append(post)
                elif time_range == "all_time":
                    # Include all posts
                    filtered_posts.append(post)
                else:
                    # Default to all posts if unknown time range
                    filtered_posts.append(post)
                    
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Error processing post date: {e}")
                # Include post if we can't parse the date
                filtered_posts.append(post)
        
        logger.info(f"Time filtering (backup): {len(posts)} posts -> {len(filtered_posts)} posts (time_range: {time_range})")
        return filtered_posts
    
    def extract_keywords(self, user_input: str) -> List[str]:
        """Extract main keywords from user input"""
        # Simple keyword extraction - split by spaces and filter out common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "cannot", "i", "me", "my", "we", "our", "you", "your", "they", "their", "it", "its", "this", "that", "these", "those"}
        
        words = re.findall(r'\b\w+\b', user_input.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        logger.info(f"Extracted keywords from '{user_input}': {keywords}")
        return keywords
    
    def contains_struggle_indicators(self, text: str) -> bool:
        """Check if text contains struggle indicators"""
        text_lower = text.lower()
        struggle_count = sum(1 for indicator in self.struggle_indicators if indicator in text_lower)
        
        # Must have at least 2 struggle indicators
        has_struggle = struggle_count >= 2
        logger.info(f"Struggle check for text (first 100 chars): {text[:100]}... - Found {struggle_count} indicators, Result: {has_struggle}")
        return has_struggle
    
    def matches_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text matches any of the keywords"""
        if not keywords:
            return True  # If no keywords, match all
        
        text_lower = text.lower()
        matched_keywords = [keyword for keyword in keywords if keyword in text_lower]
        
        has_match = len(matched_keywords) > 0
        logger.info(f"Keyword match for text (first 100 chars): {text[:100]}... - Keywords: {keywords}, Matched: {matched_keywords}, Result: {has_match}")
        return has_match
    
    def filter_posts(self, posts: List[Dict[str, Any]], user_input: str, business_type: Optional[str] = None, time_range: str = "all_time") -> List[Lead]:
        """Filter posts using AI-enhanced analysis for better relevance with time-based filtering"""
        try:
            # DEBUG: Log current configuration
            logger.info(f"🔧 FILTER DEBUG: use_openai={self.use_openai}, use_improved_ai={self.use_improved_ai}, threshold={self.ai_threshold}")
            logger.info(f"🔧 FILTER DEBUG: openai_service available: {self.openai_service is not None}")
            logger.info(f"🔧 FILTER DEBUG: ai_enhancer available: {self.ai_enhancer is not None}")
            logger.info(f"🔧 FILTER DEBUG: simple_filter available: {self.simple_filter is not None}")
            
            logger.info(f"Starting AI-enhanced filtering for {len(posts)} posts")
            
            # First, filter posts by time range
            time_filtered_posts = self.filter_posts_by_time_range(posts, time_range)
            
            # Choose AI service based on configuration
            if self.use_openai and self.openai_service:
                logger.info("🚀 USING: OpenAI service for intelligent analysis")
                logger.info(f"🔍 DEBUG: About to call OpenAI with {len(time_filtered_posts)} posts")
                result, metrics = self._filter_posts_with_openai(time_filtered_posts, user_input, business_type)
                logger.info(f"🔍 DEBUG: OpenAI returned {len(result)} leads")
                logger.info(f"💰 OPENAI METRICS: {metrics}")
                # Store metrics for later retrieval
                self._last_metrics = metrics
                return result
            elif self.use_improved_ai:
                logger.info("🚀 USING: Rule-based AI enhancer (IMPROVED mode)")
                result = self._filter_posts_with_rule_based_ai(time_filtered_posts, user_input, business_type)
                logger.info(f"🔍 DEBUG: Rule-based AI returned {len(result)} leads")
                # Store metrics for rule-based system
                self._last_metrics = {
                    "tokens_used": 0,
                    "cost": 0.0,
                    "model_used": "rule_based",
                    "posts_analyzed": len(time_filtered_posts),
                    "results_returned": len(result)
                }
                return result
            else:
                logger.info("🚀 USING: Original simple filtering system (HIGH QUALITY)")
                result = self.simple_filter.filter_posts(time_filtered_posts, user_input, business_type, time_range)
                logger.info(f"🔍 DEBUG: Simple filter returned {len(result)} leads")
                # Store metrics for simple system
                self._last_metrics = {
                    "tokens_used": 0,
                    "cost": 0.0,
                    "model_used": "simple",
                    "posts_analyzed": len(time_filtered_posts),
                    "results_returned": len(result)
                }
                return result
            
        except Exception as e:
            logger.error(f"AI filtering failed, falling back to basic filtering: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fallback to original filtering method
            fallback_result = self._basic_filter_posts(posts, user_input)
            self._last_metrics = {
                "tokens_used": 0,
                "cost": 0.0,
                "model_used": "basic_fallback",
                "posts_analyzed": len(posts),
                "results_returned": len(fallback_result)
            }
            return fallback_result
    
    def get_last_metrics(self) -> Optional[Dict[str, Any]]:
        """Get metrics from the last filtering operation"""
        return self._last_metrics
    
    def _filter_posts_with_openai(self, posts: List[Dict[str, Any]], user_input: str, business_type: Optional[str] = None) -> tuple[List[Lead], Dict[str, Any]]:
        """Filter posts using OpenAI service and return leads with metrics"""
        try:
            # Reset metrics for this operation
            self.openai_service.reset_metrics()
            
            # Enhance query with OpenAI
            enhanced_query = self.openai_service.enhance_query(user_input, business_type or "General Business")
            
            # Analyze posts with OpenAI (batch processing for efficiency)
            analysis_results = self.openai_service.batch_analyze_posts(posts, user_input, business_type or "General Business")
            
            filtered_leads = []
            total_tokens = 0
            total_cost = 0.0
            
            for i, post in enumerate(posts):
                if i >= len(analysis_results):
                    break
                    
                analysis = analysis_results[i]
                
                logger.info(f"OpenAI Analysis - Post: {post['title'][:50]}... Score: {analysis.relevance_score}")
                
                # Only include posts with high relevance and struggle indicators
                if analysis.relevance_score >= self.ai_threshold and analysis.is_struggle_post:
                    # Generate AI summary
                    ai_summary = self.openai_service.generate_lead_summary(post, analysis)
                    
                    # Create enhanced snippet
                    snippet = self._create_enhanced_snippet(post["text"], enhanced_query.search_keywords)
                    
                    # Create enhanced lead with OpenAI insights
                    lead = Lead(
                        title=post["title"],
                        subreddit=post["subreddit"],
                        snippet=snippet,
                        permalink=post["permalink"],
                        author=post["author"],
                        created_utc=post["created_utc"],
                        score=post["score"],
                        matched_keywords=enhanced_query.search_keywords,
                        # OpenAI-enhanced fields
                        ai_relevance_score=analysis.relevance_score,
                        urgency_level=analysis.urgency_level,
                        business_context=analysis.business_type,
                        problem_category=analysis.problem_category,
                        ai_summary=ai_summary
                    )
                    
                    filtered_leads.append(lead)
            
            # Sort by AI relevance score
            filtered_leads.sort(key=lambda x: x.ai_relevance_score or 0, reverse=True)
            
            # Debug: Log score distribution
            scores = [lead.ai_relevance_score for lead in filtered_leads if lead.ai_relevance_score]
            if scores:
                logger.info(f"OpenAI Score distribution: min={min(scores)}, max={max(scores)}, avg={sum(scores)/len(scores):.1f}")
                logger.info(f"Score ranges: 25-34: {len([s for s in scores if 25 <= s < 35])}, 35-49: {len([s for s in scores if 35 <= s < 50])}, 50+: {len([s for s in scores if s >= 50])}")
            
            # Get metrics from OpenAI service
            openai_metrics = self.openai_service.get_metrics()
            metrics = {
                "tokens_used": openai_metrics["tokens_used"],
                "cost": openai_metrics["cost"],
                "model_used": openai_metrics["model_used"],
                "posts_analyzed": len(posts),
                "results_returned": len(filtered_leads)
            }
            
            logger.info(f"OpenAI filtering: {len(posts)} posts down to {len(filtered_leads)} high-relevance leads ({self.ai_threshold}+ threshold)")
            return filtered_leads, metrics
            
        except Exception as e:
            logger.error(f"OpenAI filtering failed: {e}")
            # Fallback to rule-based AI
            fallback_result = self._filter_posts_with_rule_based_ai(posts, user_input, business_type)
            fallback_metrics = {
                "tokens_used": 0,
                "cost": 0.0,
                "model_used": "rule_based_fallback",
                "posts_analyzed": len(posts),
                "results_returned": len(fallback_result)
            }
            self._last_metrics = fallback_metrics
            return fallback_result, fallback_metrics
    
    def _filter_posts_with_rule_based_ai(self, posts: List[Dict[str, Any]], user_input: str, business_type: Optional[str] = None) -> List[Lead]:
        """Filter posts using rule-based AI enhancer (fallback)"""
        # Use AI to enhance the query
        enhanced_query = self.ai_enhancer.enhance_query(user_input, business_type or "General Business")
        
        filtered_leads = []
        logger.info(f"Rule-based AI filtering ({'IMPROVED' if self.use_improved_ai else 'ORIGINAL'}): {len(posts)} posts with enhanced query: {enhanced_query.enhanced_problem}")
        
        for post in posts:
                # Use AI to analyze post relevance with business/industry context
                is_business = business_type in BUSINESS_MAPPINGS
                is_industry = business_type in INDUSTRY_MAPPINGS
                
                relevance_score = self.ai_enhancer.analyze_post_relevance(
                    post, 
                    enhanced_query.keywords, 
                    business_type=business_type if is_business else None,
                    industry_type=business_type if is_industry else None
                )
                
            logger.info(f"Rule-based AI Analysis - Post: {post['title'][:50]}... Score: {relevance_score.overall_score}")
                
                # Only include posts with high relevance (configurable threshold)
                if relevance_score.overall_score >= self.ai_threshold:
                    # Extract business context
                    business_context = self.ai_enhancer.extract_business_context(post["text"])
                    
                    # Create enhanced snippet
                    snippet = self._create_enhanced_snippet(post["text"], enhanced_query.keywords)
                    
                    # Find matched keywords
                    text_lower = post["text"].lower()
                    matched_keywords = [keyword for keyword in enhanced_query.keywords if keyword in text_lower]
                    
                    # Create enhanced lead with AI insights
                    lead = Lead(
                        title=post["title"],
                        subreddit=post["subreddit"],
                        snippet=snippet,
                        permalink=post["permalink"],
                        author=post["author"],
                        created_utc=post["created_utc"],
                        score=post["score"],
                        matched_keywords=matched_keywords,
                        # AI-enhanced fields
                        ai_relevance_score=relevance_score.overall_score,
                        urgency_level=relevance_score.urgency_level,
                        business_context=business_context.business_type,
                        problem_category=business_context.problem_category
                    )
                    
                    filtered_leads.append(lead)
            
            # Sort by AI relevance score
            filtered_leads.sort(key=lambda x: x.ai_relevance_score or 0, reverse=True)
            
            # Debug: Log score distribution
            scores = [lead.ai_relevance_score for lead in filtered_leads if lead.ai_relevance_score]
            if scores:
                logger.info(f"Rule-based Score distribution: min={min(scores)}, max={max(scores)}, avg={sum(scores)/len(scores):.1f}")
                logger.info(f"Score ranges: 25-34: {len([s for s in scores if 25 <= s < 35])}, 35-49: {len([s for s in scores if 35 <= s < 50])}, 50+: {len([s for s in scores if s >= 50])}")
            
            logger.info(f"Rule-based AI filtering: {len(posts)} posts down to {len(filtered_leads)} high-relevance leads ({self.ai_threshold}+ threshold, {'IMPROVED' if self.use_improved_ai else 'ORIGINAL'} mode)")
            return filtered_leads
    
    def _basic_filter_posts(self, posts: List[Dict[str, Any]], user_input: str) -> List[Lead]:
        """Original filtering method as fallback"""
        keywords = self.extract_keywords(user_input)
        filtered_leads = []
        
        logger.info(f"Basic filtering: {len(posts)} posts with keywords: {keywords}")
        
        for post in posts:
            # Check if post matches keywords AND contains struggle indicators
            if (self.matches_keywords(post["text"], keywords) and 
                self.contains_struggle_indicators(post["text"])):
                
                # Create snippet (first 200 characters)
                snippet = post["text"][:200] + "..." if len(post["text"]) > 200 else post["text"]
                
                # Find matched keywords for this post
                text_lower = post["text"].lower()
                matched_keywords = [keyword for keyword in keywords if keyword in text_lower]
                
                lead = Lead(
                    title=post["title"],
                    subreddit=post["subreddit"],
                    snippet=snippet,
                    permalink=post["permalink"],
                    author=post["author"],
                    created_utc=post["created_utc"],
                    score=post["score"],
                    matched_keywords=matched_keywords
                )
                filtered_leads.append(lead)
        
        logger.info(f"Basic filtering: {len(posts)} posts down to {len(filtered_leads)} relevant leads")
        return filtered_leads
    
    def _create_enhanced_snippet(self, text: str, keywords: List[str]) -> str:
        """Create a snippet that highlights relevant keywords"""
        if not keywords:
            return text[:200] + "..." if len(text) > 200 else text
        
        # Find the first occurrence of any keyword
        text_lower = text.lower()
        first_keyword_pos = len(text)
        
        for keyword in keywords:
            pos = text_lower.find(keyword.lower())
            if pos != -1 and pos < first_keyword_pos:
                first_keyword_pos = pos
        
        # Create snippet around the first keyword
        start = max(0, first_keyword_pos - 50)
        end = min(len(text), first_keyword_pos + 150)
        
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
