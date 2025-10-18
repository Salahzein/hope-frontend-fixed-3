"""
OpenAI Service for intelligent lead analysis and filtering
Replaces rule-based AI with actual OpenAI API integration
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class AIAnalysisResult:
    """Result of OpenAI analysis of a Reddit post"""
    relevance_score: int  # 0-100
    is_struggle_post: bool
    urgency_level: str  # "High", "Medium", "Low"
    business_type: str
    problem_category: str
    key_insights: List[str]
    confidence: float  # 0.0-1.0
    reasoning: str

@dataclass
class EnhancedQuery:
    """Enhanced query with AI-generated insights"""
    original_problem: str
    enhanced_problem: str
    search_keywords: List[str]
    business_context: str
    target_audience: str

class OpenAIService:
    """
    OpenAI-powered service for intelligent lead finding and analysis.
    Provides semantic understanding, context awareness, and business relevance scoring.
    """
    
    def __init__(self):
        # Initialize OpenAI client with explicit httpx configuration
        try:
            import httpx
            # Create a custom httpx client without proxy settings
            http_client = httpx.Client(
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            
            # Initialize OpenAI with custom http client
            self.client = OpenAI(
                api_key=settings.openai_api_key,
                http_client=http_client
            )
            logger.info("✅ OpenAI client initialized with custom httpx client")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client with custom httpx: {e}")
            # Final fallback: try without any custom client
            try:
                self.client = OpenAI(api_key=settings.openai_api_key)
                logger.info("✅ OpenAI client initialized with default settings")
            except Exception as e2:
                logger.error(f"Complete OpenAI initialization failure: {e2}")
                raise e2
        self.model = settings.openai_model
        self.temperature = settings.openai_temperature
        self.max_tokens = settings.openai_max_tokens
        
        logger.info(f"OpenAI Service initialized with model: {self.model}")
        
        # Initialize metrics tracking
        self._total_tokens = 0
        self._total_cost = 0.0
    
    def reset_metrics(self):
        """Reset token and cost tracking"""
        self._total_tokens = 0
        self._total_cost = 0.0
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current token and cost metrics"""
        return {
            "tokens_used": self._total_tokens,
            "cost": self._total_cost,
            "model_used": self.model
        }
    
    def _calculate_cost(self, tokens_used: int) -> float:
        """Calculate cost based on model and token usage"""
        # gpt-3.5-turbo pricing: $0.0015 per 1K input tokens, $0.002 per 1K output tokens
        # For simplicity, using average of $0.00175 per 1K tokens
        cost_per_1k_tokens = 0.00175
        return (tokens_used / 1000) * cost_per_1k_tokens
    
    def enhance_query(self, problem: str, business_type: str) -> EnhancedQuery:
        """
        Enhance the user's problem description using OpenAI to extract better keywords
        and understand the business context.
        """
        try:
            logger.info(f"🔍 OPENAI DEBUG: Starting query enhancement for problem: '{problem}', business: '{business_type}'")
            prompt = f"""
You are an expert business consultant helping to find leads for a service provider.

USER'S PROBLEM: "{problem}"
TARGET BUSINESS TYPE: "{business_type}"

Your task:
1. Enhance the problem description to be more searchable
2. Extract key search terms and keywords
3. Identify the target audience
4. Provide business context

Respond in JSON format:
{{
    "enhanced_problem": "Enhanced problem description with related terms",
    "search_keywords": ["keyword1", "keyword2", "keyword3"],
    "business_context": "Brief business context description",
    "target_audience": "Who specifically needs this solution"
}}
"""

            logger.info(f"🚀 OPENAI DEBUG: Making API call to OpenAI with model: {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert business consultant specializing in lead generation and market analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Track token usage and cost
            tokens_used = response.usage.total_tokens
            cost = self._calculate_cost(tokens_used)
            
            logger.info(f"✅ OPENAI DEBUG: Received response from OpenAI")
            logger.info(f"💰 TOKEN USAGE: {tokens_used} tokens, ${cost:.4f} cost (query enhancement)")
            
            # Parse JSON response with error handling
            try:
                content = response.choices[0].message.content
                logger.info(f"🔍 OPENAI DEBUG: Raw response content: {content[:200]}...")
                result = json.loads(content)
                logger.info(f"📊 OPENAI DEBUG: Parsed result: {result}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Raw content: {content}")
                # Return a fallback result
                result = {
                    "enhanced_problem": problem,
                    "search_keywords": problem.split(),
                    "business_context": f"Business in {business_type} sector",
                    "target_audience": "Business owners and entrepreneurs"
                }
                logger.info(f"📊 OPENAI DEBUG: Using fallback result: {result}")
            
            # Store metrics for later retrieval
            result["_metrics"] = {
                "tokens_used": tokens_used,
                "cost": cost,
                "operation": "query_enhancement"
            }
            
            # Also store metrics in the service for batch retrieval
            if not hasattr(self, '_total_tokens'):
                self._total_tokens = 0
                self._total_cost = 0.0
            self._total_tokens += tokens_used
            self._total_cost += cost
            
            return EnhancedQuery(
                original_problem=problem,
                enhanced_problem=result.get("enhanced_problem", problem),
                search_keywords=result.get("search_keywords", []),
                business_context=result.get("business_context", business_type),
                target_audience=result.get("target_audience", "Business owners")
            )
            
        except Exception as e:
            logger.error(f"Error enhancing query with OpenAI: {e}")
            # Fallback to basic enhancement
            return EnhancedQuery(
                original_problem=problem,
                enhanced_problem=problem,
                search_keywords=problem.lower().split(),
                business_context=business_type,
                target_audience="Business owners"
            )
    
    def analyze_post_relevance(self, post: Dict[str, Any], user_problem: str, business_type: str) -> AIAnalysisResult:
        """
        Analyze a Reddit post using OpenAI to determine its relevance and extract insights.
        """
        try:
            logger.info(f"🔍 OPENAI DEBUG: Analyzing post: '{post.get('title', '')[:50]}...' for problem: '{user_problem}'")
            post_text = f"Title: {post.get('title', '')}\n\nContent: {post.get('text', '')}"
            
            prompt = f"""
You are analyzing Reddit posts to find businesses that need help with specific problems.

USER'S PROBLEM: "{user_problem}"
TARGET BUSINESS TYPE: "{business_type}"

REDDIT POST TO ANALYZE:
{post_text}

Analyze this post and determine:
1. How relevant is this post to someone who solves "{user_problem}" for "{business_type}"?
2. Is this person actively struggling with a problem (not sharing success stories)?
3. What's the urgency level of their need?
4. What type of business is this?
5. What category of problem are they facing?
6. What are the key insights about their situation?

Respond in JSON format:
{{
    "relevance_score": 85,
    "is_struggle_post": true,
    "urgency_level": "High",
    "business_type": "SaaS Company",
    "problem_category": "Client Acquisition",
    "key_insights": ["Struggling to get first clients", "Tried cold emailing without success", "6 months in business"],
    "confidence": 0.9,
    "reasoning": "Post shows clear struggle with client acquisition, matches target problem area"
}}

Scoring Guidelines:
- 90-100: Perfect match, actively struggling with exact problem
- 70-89: Good match, struggling with related problem
- 50-69: Moderate match, some relevance
- 30-49: Weak match, minimal relevance
- 0-29: No relevance or success story

Focus on finding people who are ACTIVELY STRUGGLING, not those sharing success stories.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing business posts to find genuine struggles and needs. You excel at distinguishing between people asking for help vs. those sharing success stories."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Track token usage and cost
            tokens_used = response.usage.total_tokens
            cost = self._calculate_cost(tokens_used)
            logger.info(f"💰 TOKEN USAGE: {tokens_used} tokens, ${cost:.4f} cost (single post analysis)")
            
            # Parse JSON response with error handling
            try:
                content = response.choices[0].message.content
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error in post analysis: {e}")
                logger.error(f"Raw content: {content}")
                # Return fallback result
                result = {
                    "relevance_score": 50,  # Medium relevance as fallback
                    "is_struggle_post": True,
                    "urgency_level": "Medium",
                    "business_type": business_type or "Unknown",
                    "problem_category": "General",
                    "key_insights": ["Post analysis failed - using fallback"],
                    "confidence": 0.3,
                    "reasoning": "JSON parsing failed - fallback analysis"
                }
            
            return AIAnalysisResult(
                relevance_score=result.get("relevance_score", 0),
                is_struggle_post=result.get("is_struggle_post", False),
                urgency_level=result.get("urgency_level", "Low"),
                business_type=result.get("business_type", "Unknown"),
                problem_category=result.get("problem_category", "General"),
                key_insights=result.get("key_insights", []),
                confidence=result.get("confidence", 0.0),
                reasoning=result.get("reasoning", "No reasoning provided")
            )
            
        except Exception as e:
            logger.error(f"Error analyzing post with OpenAI: {e}")
            # Fallback analysis
            return AIAnalysisResult(
                relevance_score=0,
                is_struggle_post=False,
                urgency_level="Low",
                business_type="Unknown",
                problem_category="General",
                key_insights=[],
                confidence=0.0,
                reasoning=f"Error in analysis: {str(e)}"
            )
    
    def batch_analyze_posts(self, posts: List[Dict[str, Any]], user_problem: str, business_type: str) -> List[AIAnalysisResult]:
        """
        Analyze multiple posts efficiently using multiple batches for large datasets.
        """
        try:
            logger.info(f"🔍 OPENAI DEBUG: Starting batch analysis of {len(posts)} posts for problem: '{user_problem}'")
            if not posts:
                return []
            
            all_results = []
            batch_size = 20  # Process 20 posts per batch for better efficiency
            total_batches = (len(posts) + batch_size - 1) // batch_size
            
            logger.info(f"📊 Processing {len(posts)} posts in {total_batches} batches of {batch_size}")
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(posts))
                batch_posts = posts[start_idx:end_idx]
                
                logger.info(f"🔄 Processing batch {batch_num + 1}/{total_batches} (posts {start_idx + 1}-{end_idx})")
                
                # Prepare batch analysis prompt
                posts_text = ""
                for i, post in enumerate(batch_posts):
                    posts_text += f"\n--- POST {start_idx + i + 1} ---\n"
                    posts_text += f"Title: {post.get('title', '')}\n"
                    posts_text += f"Content: {post.get('text', '')}\n"
                
                prompt = f"""
You are analyzing multiple Reddit posts to find businesses that need help with specific problems.

USER'S PROBLEM: "{user_problem}"
TARGET BUSINESS TYPE: "{business_type}"

REDDIT POSTS TO ANALYZE:
{posts_text}

For EACH post, analyze and determine:
1. Relevance score (0-100)
2. Is this a struggle post (true/false)
3. Urgency level (High/Medium/Low)
4. Business type
5. Problem category
6. Key insights (list of 2-3 items)

Respond in JSON format with an array of results:
[
    {{
        "post_index": 0,
        "relevance_score": 85,
        "is_struggle_post": true,
        "urgency_level": "High",
        "business_type": "SaaS Company",
        "problem_category": "Client Acquisition",
        "key_insights": ["Struggling to get first clients", "Tried cold emailing without success"],
        "confidence": 0.9,
        "reasoning": "Clear struggle with client acquisition"
    }},
    ...
]

Focus on finding people who are ACTIVELY STRUGGLING, not those sharing success stories.
"""

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert at analyzing business posts to find genuine struggles and needs. You excel at batch analysis and distinguishing between people asking for help vs. those sharing success stories."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens * 2  # More tokens for batch analysis
                )
                
                # Track token usage and cost for this batch
                tokens_used = response.usage.total_tokens
                cost = self._calculate_cost(tokens_used)
                logger.info(f"💰 TOKEN USAGE: {tokens_used} tokens, ${cost:.4f} cost (batch {batch_num + 1} of {len(batch_posts)} posts)")
                
                # Add to total metrics
                if not hasattr(self, '_total_tokens'):
                    self._total_tokens = 0
                    self._total_cost = 0.0
                self._total_tokens += tokens_used
                self._total_cost += cost
                
                # Parse JSON response with error handling
                try:
                    content = response.choices[0].message.content
                    results = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error in batch analysis: {e}")
                    logger.error(f"Raw content: {content}")
                    # Return fallback results for this batch
                    results = []
                    for i in range(len(batch_posts)):
                        results.append({
                            "post_index": i,
                            "relevance_score": 50,  # Medium relevance as fallback
                            "is_struggle_post": True,
                            "urgency_level": "Medium",
                            "business_type": business_type or "Unknown",
                            "problem_category": "General",
                            "key_insights": ["Batch analysis failed - using fallback"],
                            "confidence": 0.3,
                            "reasoning": "JSON parsing failed - fallback analysis"
                        })
                
                # Convert to AIAnalysisResult objects and add to all_results
                for result in results:
                    # Map the post_index back to the actual post index
                    actual_post_index = start_idx + result.get("post_index", 0)
                    all_results.append(AIAnalysisResult(
                        relevance_score=result.get("relevance_score", 0),
                        is_struggle_post=result.get("is_struggle_post", False),
                        urgency_level=result.get("urgency_level", "Low"),
                        business_type=result.get("business_type", "Unknown"),
                        problem_category=result.get("problem_category", "General"),
                        key_insights=result.get("key_insights", []),
                        confidence=result.get("confidence", 0.0),
                        reasoning=result.get("reasoning", "No reasoning provided")
                    ))
            
            logger.info(f"✅ Completed batch analysis: {len(all_results)} total results for {len(posts)} posts")
            return all_results
            
        except Exception as e:
            logger.error(f"Error in batch analysis with OpenAI: {e}")
            # Fallback: analyze posts individually
            return [self.analyze_post_relevance(post, user_problem, business_type) for post in posts]
    
    def generate_lead_summary(self, lead: Dict[str, Any], analysis: AIAnalysisResult) -> str:
        """
        Generate a concise summary of the lead and their situation.
        """
        try:
            prompt = f"""
Generate a concise, professional summary of this business lead for a service provider.

LEAD INFORMATION:
Title: {lead.get('title', '')}
Content: {lead.get('text', '')}
Business Type: {analysis.business_type}
Problem Category: {analysis.problem_category}
Urgency: {analysis.urgency_level}
Key Insights: {', '.join(analysis.key_insights)}

Create a 2-3 sentence summary that highlights:
1. What type of business they have
2. What specific problem they're facing
3. Why they're a good lead

Keep it professional and focused on the business opportunity.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional business consultant creating lead summaries for service providers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating lead summary: {e}")
            return f"Business owner in {analysis.business_type} struggling with {analysis.problem_category}."
    
    def is_service_available(self) -> bool:
        """
        Check if OpenAI service is available and properly configured.
        """
        try:
            # Simple test call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI service not available: {e}")
            return False
