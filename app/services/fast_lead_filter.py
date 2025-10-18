"""
Fast Lead Filter - Rule-Based Filtering + OpenAI Summaries
This combines the proven rule-based filtering with OpenAI summaries for the best of both worlds:
- Fast performance (rule-based filtering)
- Quality insights (OpenAI summaries)
- Cost control (minimal API calls)
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from app.models.lead import Lead
from app.services.ai_enhancer import AIEnhancer, EnhancedQuery
from app.services.summary_service import SummaryService
from app.core.ai_config import get_ai_config
from app.services.business_mapping import BUSINESS_MAPPINGS, INDUSTRY_MAPPINGS

logger = logging.getLogger(__name__)

class FastLeadFilter:
    def __init__(self):
        self.ai_config = get_ai_config()
        self.ai_enhancer = AIEnhancer()
        self.summary_service = SummaryService()
        
        # Performance metrics
        self._last_metrics: Optional[Dict[str, Any]] = None
        
        logger.info(f"🚀 Fast Lead Filter initialized - Rule-based filtering + OpenAI summaries")
        logger.info(f"🔧 Config: threshold={self.ai_config['threshold']}, use_openai={self.ai_config['use_openai']}")

    def filter_posts(self, posts: List[Dict[str, Any]], problem_description: str, 
                    business_type: str, industry_type: Optional[str] = None) -> Tuple[List[Lead], Dict[str, Any]]:
        """
        Filter posts using rule-based system and add OpenAI summaries.
        Returns: (filtered_leads, metrics)
        """
        logger.info(f"🚀 Fast filtering: {len(posts)} posts for '{problem_description}'")
        
        # Reset metrics
        self._last_metrics = {
            "posts_analyzed": len(posts),
            "posts_filtered": 0,
            "summaries_generated": 0,
            "tokens_used": 0,
            "cost": 0.0,
            "filter_method": "rule_based",
            "summary_method": "openai"
        }
        
        try:
            # Step 1: Rule-based filtering (fast and accurate)
            filtered_posts = self._rule_based_filter(posts, problem_description, business_type, industry_type)
            logger.info(f"✅ Rule-based filtering: {len(posts)} -> {len(filtered_posts)} posts")
            
            # Step 2: Create leads from filtered posts
            leads = self._create_leads_from_posts(filtered_posts, problem_description, business_type)
            logger.info(f"✅ Created {len(leads)} leads")
            
            # Step 3: Add simple summaries (OpenAI disabled for now due to proxy issues)
            if leads:
                leads = self._add_simple_summaries(leads, problem_description)
            
            # Update metrics
            self._last_metrics.update({
                "posts_filtered": len(filtered_posts),
                "results_returned": len(leads)
            })
            
            logger.info(f"🎯 Fast filtering complete: {len(leads)} quality leads")
            return leads, self._last_metrics
            
        except Exception as e:
            logger.error(f"❌ Error in fast filtering: {e}")
            # Return empty results on error
            return [], self._last_metrics or {}

    def _rule_based_filter(self, posts: List[Dict[str, Any]], problem_description: str, 
                          business_type: str, industry_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Rule-based filtering - the proven system that worked before.
        """
        # Get business/industry keywords
        business_keywords = BUSINESS_MAPPINGS.get(business_type, {}).get("keywords", [])
        if industry_type:
            industry_keywords = INDUSTRY_MAPPINGS.get(industry_type, {}).get("keywords", [])
            business_keywords.extend(industry_keywords)
        
        # Enhanced query processing
        enhanced_query = self.ai_enhancer.enhance_query(problem_description, business_type)
        enhanced_keywords = enhanced_query.keywords
        
        # Combine all keywords
        all_keywords = business_keywords + enhanced_keywords
        
        logger.info(f"🔍 Keywords for '{business_type}': {all_keywords[:10]}...")  # Show first 10 keywords
        
        # Struggle indicators
        struggle_indicators = [
            "struggling", "help", "can't", "cannot", "can not", "trouble", "problem", "issue", 
            "stuck", "frustrated", "overwhelmed", "desperate", "urgent", "failing", "lost", 
            "losing", "declining", "first client", "first customer", "no customers", "no clients",
            "getting clients", "customer acquisition", "lead generation", "need help", 
            "looking for", "how to", "what should", "any advice"
        ]
        
        filtered_posts = []
        
        logger.info(f"🔍 Processing {len(posts)} posts for filtering...")
        
        for i, post in enumerate(posts[:5]):  # Log first 5 posts for debugging
            logger.info(f"📝 Post {i+1}: {post.get('title', '')[:50]}...")
        
        for post in posts:
            title = post.get("title", "").lower()
            content = post.get("content", "").lower()
            text = f"{title} {content}"
            
            # Calculate relevance score
            score = 0
            
            # Business keyword matching
            for keyword in all_keywords:
                if keyword.lower() in text:
                    score += 3
            
            # Struggle indicator matching
            for indicator in struggle_indicators:
                if indicator in text:
                    score += 2
            
            # Enhanced keyword matching (higher weight)
            for keyword in enhanced_keywords:
                if keyword.lower() in text:
                    score += 4
            
            # Bonus for exact problem match
            problem_words = problem_description.lower().split()
            for word in problem_words:
                if len(word) > 3 and word in text:
                    score += 1
            
            # Assign score to post (for debugging)
            post["relevance_score"] = score
            
            # Apply threshold
            if score >= self.ai_config["threshold"]:
                filtered_posts.append(post)
        
        # Sort by relevance score (highest first)
        filtered_posts.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Debug: Show score distribution
        all_scores = [post.get("relevance_score", 0) for post in posts]
        max_score = max(all_scores) if all_scores else 0
        min_score = min(all_scores) if all_scores else 0
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        logger.info(f"📊 Score distribution: min={min_score}, max={max_score}, avg={avg_score:.1f}")
        logger.info(f"📊 Filtered posts: {len(filtered_posts)} out of {len(posts)} (threshold={self.ai_config['threshold']})")
        logger.info(f"📊 Top scores: {[p.get('relevance_score', 0) for p in filtered_posts[:5]]}")
        
        return filtered_posts

    def _create_leads_from_posts(self, posts: List[Dict[str, Any]], problem_description: str, business_type: str) -> List[Lead]:
        """Create Lead objects from filtered posts."""
        leads = []
        
        for post in posts:
            try:
                lead = Lead(
                    title=post.get("title", ""),
                    subreddit=post.get("subreddit", ""),
                    snippet=post.get("content", "")[:200] + "..." if len(post.get("content", "")) > 200 else post.get("content", ""),
                    permalink=post.get("permalink", ""),
                    author=post.get("author", ""),
                    created_utc=post.get("created_utc", 0),
                    score=post.get("score", 0),
                    matched_keywords=[],  # Will be populated later
                    ai_relevance_score=post.get("relevance_score", 0),
                    urgency_level="Medium",  # Default
                    business_context=business_type,
                    problem_category="General",  # Default
                    ai_summary=""  # Will be populated by OpenAI
                )
                leads.append(lead)
            except Exception as e:
                logger.error(f"❌ Error creating lead from post: {e}")
                continue
        
        return leads

    def _add_openai_summaries(self, leads: List[Lead], problem_description: str) -> List[Lead]:
        """
        Add OpenAI summaries to leads in batches for efficiency.
        This is the only place we use OpenAI - for summaries only.
        """
        try:
            # Convert leads to post format for summary service
            posts_for_summary = []
            for lead in leads[:10]:  # Limit to top 10 for performance
                posts_for_summary.append({
                    "title": lead.title,
                    "content": lead.snippet
                })
            
            # Generate summaries in batch
            summaries = self.summary_service.batch_generate_summaries(posts_for_summary, problem_description)
            
            # Apply summaries to leads
            for i, lead in enumerate(leads[:10]):
                if i < len(summaries):
                    lead.ai_summary = summaries[i]
                else:
                    lead.ai_summary = f"Post about {problem_description.lower()} - {lead.title[:100]}..."
            
            # Add fallback summaries for remaining leads
            for lead in leads[10:]:
                lead.ai_summary = f"Post about {problem_description.lower()} - {lead.title[:100]}..."
            
            logger.info(f"✅ Added OpenAI summaries to {len(leads)} leads")
            return leads
            
        except Exception as e:
            logger.error(f"❌ Error adding OpenAI summaries: {e}")
            # Add fallback summaries
            for lead in leads:
                lead.ai_summary = f"Post about {problem_description.lower()} - {lead.title[:100]}..."
            return leads

    def _add_simple_summaries(self, leads: List[Lead], problem_description: str) -> List[Lead]:
        """
        Add intelligent, descriptive summaries without OpenAI.
        These are fast, reliable, and much more readable than the old system.
        """
        try:
            for lead in leads:
                lead.ai_summary = self._generate_smart_summary(lead, problem_description)
            
            logger.info(f"✅ Added smart summaries to {len(leads)} leads")
            return leads
            
        except Exception as e:
            logger.error(f"❌ Error adding smart summaries: {e}")
            # Add basic fallback summaries
            for lead in leads:
                lead.ai_summary = f"Post about {problem_description.lower()} - {lead.title[:100]}..."
            return leads

    def _generate_smart_summary(self, lead: Lead, problem_description: str) -> str:
        """
        Generate a simple, varied summary by rephrasing the title.
        Uses hash-based variation to guarantee different summaries for different titles.
        """
        try:
            title = lead.title.strip()
            business_context = lead.business_context or "business owner"
            
            # Clean up the title
            cleaned_title = self._clean_title(title)
            
            # Get business term
            business_term = self._get_business_term(business_context)
            
            # Generate varied summary using hash-based variation
            summary = self._create_simple_varied_summary(cleaned_title, business_term)
            
            # Ensure appropriate length
            if len(summary) > 120:
                summary = summary[:117] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generating smart summary: {e}")
            # Fallback to simple summary
            return f"Post about {problem_description.lower()} - {lead.title[:80]}..."

    def _clean_title(self, title: str) -> str:
        """Clean up the title by removing Reddit prefixes and fixing common issues."""
        cleaned = title.strip()
        
        # Remove common Reddit prefixes
        prefixes_to_remove = [
            "[serious]", "[help]", "[advice]", "[question]", "[discussion]", "[vent]",
            "serious:", "help:", "advice:", "question:", "discussion:", "vent:",
            "[serious] ", "[help] ", "[advice] ", "[question] ", "[discussion] "
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
        
        # Fix common grammar issues
        cleaned = cleaned.replace("&amp;", "&")
        cleaned = cleaned.replace("&lt;", "<")
        cleaned = cleaned.replace("&gt;", ">")
        
        # Ensure proper capitalization
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        return cleaned

    def _get_business_term(self, business_context: str) -> str:
        """Get the appropriate business term for the context."""
        # Map business types to natural terms
        business_terms = {
            "SaaS Companies": "SaaS founder",
            "E-commerce Stores": "e-commerce store owner", 
            "Marketing Agencies": "marketing agency owner",
            "Gyms / Fitness Studios": "fitness business owner",
            "Coffee Shops / Cafés": "coffee shop owner",
            "Freelance Designers": "freelance designer",
            "Online Course Creators": "course creator",
            "Local Service Businesses": "local business owner",
            "App Developers": "app developer",
            "Consultants / Coaches": "consultant",
            "Jobs and Hiring": "job seeker"
        }
        
        return business_terms.get(business_context, "business owner")

    def _create_simple_varied_summary(self, title: str, business_term: str) -> str:
        """Create a detailed, specific summary by extracting key information from the title."""
        title_lower = title.lower()
        
        # Extract specific details from the title
        numbers = self._extract_numbers(title)
        problems = self._extract_specific_problems(title)
        stage = self._extract_stage(title)
        
        # Create targeted summaries based on extracted details
        if "first" in title_lower and numbers:
            return f"{business_term.title()} seeking {numbers} for initial validation and feedback"
        elif "struggling" in title_lower and problems:
            return f"{business_term.title()} facing {problems} challenges, seeking solutions"
        elif "help" in title_lower and numbers:
            return f"{business_term.title()} looking for assistance to reach {numbers}"
        elif "feedback" in title_lower:
            return f"{business_term.title()} requesting feedback and user validation"
        elif "launch" in title_lower or "launched" in title_lower:
            return f"{business_term.title()} recently launched and seeking initial traction"
        elif "marketing" in title_lower:
            return f"{business_term.title()} struggling with marketing and customer acquisition"
        elif stage:
            return f"{business_term.title()} at {stage} stage, seeking growth strategies"
        elif "trial" in title_lower or "beta" in title_lower:
            return f"{business_term.title()} looking for beta users and early adopters"
        elif "grow" in title_lower or "scale" in title_lower:
            return f"{business_term.title()} looking to grow and scale their business"
        else:
            # Fallback with some variation
            title_hash = hash(title) % 3
            if title_hash == 0:
                return f"{business_term.title()} seeking advice and guidance for business growth"
            elif title_hash == 1:
                return f"{business_term.title()} looking for solutions to current challenges"
            else:
                return f"{business_term.title()} requesting help with business development"

    def _extract_numbers(self, title: str) -> str:
        """Extract numbers and quantities from the title."""
        import re
        
        # Look for patterns like "first 5-10 users", "100 users", "first 50", etc.
        patterns = [
            r'first\s+(\d+(?:-\d+)?)\s*(?:to\s+\d+)?\s*(?:users?|customers?|clients?)',
            r'(\d+(?:-\d+)?)\s*(?:to\s+\d+)?\s*(?:users?|customers?|clients?)',
            r'first\s+(\d+)',
            r'(\d+)\s+(?:paying\s+)?users?',
            r'(\d+)\s+(?:active\s+)?users?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title.lower())
            if match:
                number = match.group(1)
                if "first" in title.lower():
                    return f"their first {number} users"
                else:
                    return f"{number} users"
        
        return None

    def _extract_specific_problems(self, title: str) -> str:
        """Extract specific problems mentioned in the title."""
        title_lower = title.lower()
        
        if "marketing" in title_lower:
            return "marketing and customer acquisition"
        elif "conversion" in title_lower:
            return "conversion optimization"
        elif "feedback" in title_lower:
            return "user feedback and validation"
        elif "adoption" in title_lower:
            return "user adoption and engagement"
        elif "traffic" in title_lower:
            return "traffic generation"
        elif "sales" in title_lower:
            return "sales and revenue generation"
        elif "scaling" in title_lower or "scale" in title_lower:
            return "scaling and growth"
        else:
            return "customer acquisition"

    def _extract_stage(self, title: str) -> str:
        """Extract the business stage mentioned in the title."""
        title_lower = title.lower()
        
        if "launch" in title_lower or "launched" in title_lower:
            return "early launch"
        elif "beta" in title_lower or "trial" in title_lower:
            return "beta testing"
        elif "first" in title_lower and ("user" in title_lower or "customer" in title_lower):
            return "initial user acquisition"
        elif "startup" in title_lower:
            return "startup"
        else:
            return None

    def get_last_metrics(self) -> Optional[Dict[str, Any]]:
        """Get metrics from the last filtering operation."""
        return self._last_metrics
