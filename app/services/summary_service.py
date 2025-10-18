"""
Simple OpenAI Service for Post Summaries Only
This service only generates summaries for posts that have already been filtered
by the rule-based system, avoiding the performance and quality issues.
"""

import os
import json
import logging
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class SummaryService:
    def __init__(self):
        self.client = None
        self.model = "gpt-3.5-turbo"
        self.max_tokens = 150
        self.temperature = 0.3
        
        # Initialize OpenAI client with proxy handling
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                # Clear any proxy environment variables that might cause issues
                for key in list(os.environ.keys()):
                    if key.lower().startswith('http_proxy') or key.lower().startswith('https_proxy'):
                        del os.environ[key]
                
                # Initialize with minimal parameters
                self.client = OpenAI(api_key=api_key)
                logger.info("✅ Summary Service: OpenAI client initialized")
            except Exception as e:
                logger.error(f"❌ Summary Service: Failed to initialize OpenAI client: {e}")
                try:
                    # Fallback: try with explicit httpx client
                    import httpx
                    client = httpx.Client(proxies=None)
                    self.client = OpenAI(api_key=api_key, http_client=client)
                    logger.info("✅ Summary Service: OpenAI client initialized with httpx")
                except Exception as e2:
                    logger.error(f"❌ Summary Service: Fallback also failed: {e2}")
                    self.client = None
        else:
            logger.warning("⚠️ Summary Service: No OpenAI API key found")

    def generate_summary(self, post_title: str, post_content: str, problem_description: str) -> str:
        """
        Generate a concise summary for a post that's already been filtered as relevant.
        This is much faster and more accurate than trying to filter and summarize at once.
        """
        if not self.client:
            return f"Post about {problem_description.lower()} - {post_title[:100]}..."
        
        try:
            prompt = f"""
You are analyzing a Reddit post that has already been identified as relevant to someone looking for help with: "{problem_description}"

Post Title: {post_title}
Post Content: {post_content[:500]}...

Generate a concise 2-3 sentence summary that explains:
1. What specific problem the person is facing
2. Why this would be a good lead for someone who solves "{problem_description}"

Keep it under 150 words and focus on the business opportunity.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"✅ Generated summary for: {post_title[:50]}...")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generating summary: {e}")
            return f"Post about {problem_description.lower()} - {post_title[:100]}..."

    def batch_generate_summaries(self, posts: List[Dict[str, Any]], problem_description: str) -> List[str]:
        """
        Generate summaries for a batch of posts.
        This is much more efficient than individual API calls.
        """
        if not self.client or not posts:
            return [f"Post about {problem_description.lower()}" for _ in posts]
        
        try:
            # Create a single prompt for all posts
            posts_text = ""
            for i, post in enumerate(posts[:10]):  # Limit to 10 posts per batch
                posts_text += f"\nPost {i+1}:\n"
                posts_text += f"Title: {post.get('title', '')}\n"
                posts_text += f"Content: {post.get('content', '')[:300]}...\n"
                posts_text += "---\n"
            
            prompt = f"""
You are analyzing Reddit posts that have already been identified as relevant to someone looking for help with: "{problem_description}"

{posts_text}

For each post, generate a concise 2-3 sentence summary that explains:
1. What specific problem the person is facing
2. Why this would be a good lead for someone who solves "{problem_description}"

Return your response as a JSON array of summaries, one for each post.
Format: ["summary1", "summary2", "summary3", ...]

Keep each summary under 100 words and focus on the business opportunity.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,  # More tokens for batch processing
                temperature=self.temperature
            )
            
            result = response.choices[0].message.content.strip()
            
            try:
                summaries = json.loads(result)
                if isinstance(summaries, list) and len(summaries) == len(posts[:10]):
                    logger.info(f"✅ Generated {len(summaries)} summaries in batch")
                    return summaries
                else:
                    raise ValueError("Invalid response format")
            except (json.JSONDecodeError, ValueError):
                logger.warning("⚠️ Batch summary failed, falling back to individual summaries")
                return [self.generate_summary(post.get('title', ''), post.get('content', ''), problem_description) for post in posts[:10]]
                
        except Exception as e:
            logger.error(f"❌ Error in batch summary generation: {e}")
            return [f"Post about {problem_description.lower()}" for _ in posts]
