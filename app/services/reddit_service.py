import praw
import time
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from app.core.config import settings
from app.services.business_mapping import get_subreddits_for_business, get_subreddits_for_industry

logger = logging.getLogger(__name__)

class RedditService:
    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )
        self.last_request_time = 0
        self.rate_limit_delay = 0.2  # 0.2 seconds between requests (5x faster)
    
    def _rate_limit(self):
        """Ensure we don't exceed Reddit's rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def get_business_subreddits(self) -> List[str]:
        """Return predefined list of business-related subreddits"""
        return [
            "SaaS", "entrepreneur", "startups", "smallbusiness", "business",
            "marketing", "sales", "freelance", "consulting", "agency",
            "sideproject", "indiehackers", "microsaas", "startup_ideas",
            "business_ideas", "entrepreneurship", "cofounderhunt"
        ]
    
    def get_subreddits_for_selection(self, business: Optional[str] = None, industry: Optional[str] = None) -> List[str]:
        """Get subreddits based on business or industry selection"""
        if business:
            return get_subreddits_for_business(business)
        elif industry:
            return get_subreddits_for_industry(industry)
        else:
            return ["SaaS", "entrepreneur", "startups"]  # Fallback
    
    def fetch_posts_from_subreddit(self, subreddit_name: str, limit: int = 50, time_range: str = "today") -> List[Dict[str, Any]]:
        """Fetch posts from a specific subreddit using multiple sorting methods for better diversity"""
        logger.info(f"Fetching {limit} posts from r/{subreddit_name} (time_range: {time_range})")
        
        try:
            self._rate_limit()
            subreddit = self.reddit.subreddit(subreddit_name)
            all_posts = []
            
            # Use multiple sorting methods to get diverse posts
            if time_range == "today":
                # For today: mix of new and hot posts
                posts_per_method = limit // 2
                try:
                    new_posts = list(subreddit.new(limit=posts_per_method))
                    all_posts.extend(new_posts)
                except:
                    pass
                try:
                    hot_posts = list(subreddit.hot(limit=posts_per_method))
                    all_posts.extend(hot_posts)
                except:
                    pass
                    
            elif time_range == "last_week":
                # For last week: mix of hot and top weekly
                posts_per_method = limit // 2
                try:
                    hot_posts = list(subreddit.hot(limit=posts_per_method))
                    all_posts.extend(hot_posts)
                except:
                    pass
                try:
                    top_posts = list(subreddit.top(time_filter="week", limit=posts_per_method))
                    all_posts.extend(top_posts)
                except:
                    pass
                    
            elif time_range == "last_month":
                # For last month: mix of top monthly and hot
                posts_per_method = limit // 2
                try:
                    top_posts = list(subreddit.top(time_filter="month", limit=posts_per_method))
                    all_posts.extend(top_posts)
                except:
                    pass
                try:
                    hot_posts = list(subreddit.hot(limit=posts_per_method))
                    all_posts.extend(hot_posts)
                except:
                    pass
                    
            elif time_range == "all_time":
                # For all time: mix of top all-time and hot
                posts_per_method = limit // 2
                try:
                    top_posts = list(subreddit.top(time_filter="all", limit=posts_per_method))
                    all_posts.extend(top_posts)
                except:
                    pass
                try:
                    hot_posts = list(subreddit.hot(limit=posts_per_method))
                    all_posts.extend(hot_posts)
                except:
                    pass
            else:
                # Default: just new posts
                all_posts = list(subreddit.new(limit=limit))
            
            # Remove duplicates based on post ID
            seen_ids = set()
            unique_posts = []
            for submission in all_posts:
                if submission.id not in seen_ids:
                    seen_ids.add(submission.id)
                    unique_posts.append(submission)
            
            # Convert to our format
            posts = []
            for submission in unique_posts[:limit]:  # Limit to requested amount
                post_data = {
                    "title": submission.title,
                    "text": f"{submission.title} {submission.selftext}".strip(),
                    "subreddit": subreddit_name,
                    "permalink": f"https://reddit.com{submission.permalink}",
                    "author": str(submission.author) if submission.author else "[deleted]",
                    "created_utc": submission.created_utc,
                    "score": submission.score,
                    "num_comments": submission.num_comments
                }
                posts.append(post_data)
            
            logger.info(f"Successfully fetched {len(posts)} unique posts from r/{subreddit_name}")
            return posts
            
        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit_name}: {e}")
            return []
    
    def fetch_posts_from_multiple_subreddits(self, subreddit_names: List[str], query: str = "", limit_per_sub: int = 50, time_range: str = "today") -> List[Dict[str, Any]]:
        """Fetch posts from multiple subreddits in parallel for much faster performance"""
        logger.info(f"🚀 PARALLEL SCRAPING: Starting parallel fetch from {len(subreddit_names)} subreddits")
        all_posts = []
        
        # Use ThreadPoolExecutor to run subreddits in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all subreddit scraping tasks
            futures = []
            for subreddit_name in subreddit_names:
                future = executor.submit(
                    self.fetch_posts_with_multiple_methods, 
                    subreddit_name, query, limit_per_sub, time_range
                )
                futures.append((subreddit_name, future))
            
            # Collect results as they complete
            for subreddit_name, future in futures:
                try:
                    posts = future.result()
                    all_posts.extend(posts)
                    logger.info(f"✅ PARALLEL: Fetched {len(posts)} posts from r/{subreddit_name}")
                except Exception as e:
                    logger.error(f"❌ PARALLEL: Error fetching from r/{subreddit_name}: {e}")
        
        logger.info(f"🎯 PARALLEL COMPLETE: Total {len(all_posts)} posts from {len(subreddit_names)} subreddits")
        return all_posts
    
    def fetch_posts_with_multiple_methods(self, subreddit_name: str, query: str, limit: int = 50, time_range: str = "today") -> List[Dict[str, Any]]:
        """Fetch posts using multiple sorting methods and search variations for maximum diversity"""
        logger.info(f"🔍 MULTIPLE METHODS: Fetching from r/{subreddit_name} with query '{query}' (time_range: {time_range})")
        
        all_posts = []
        posts_per_method = max(1, limit // 2)  # Split limit between methods
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # TIME RANGE LOGIC: Use different methods based on time_range
            if time_range == "today":
                # For today: Use 'new' and 'hot' for recent posts - GET MORE POSTS
                # Increase limit to get more posts and handle duplicates better
                today_posts_per_method = limit * 2  # Get 2x limit from each method (100+100 instead of 50+50)
                
                try:
                    self._rate_limit()
                    new_posts = list(subreddit.new(limit=today_posts_per_method))
                    # Add all posts without filtering - let AND-logic handle filtering later
                    for post in new_posts:
                        all_posts.append(self._format_post(post))
                    logger.info(f"✅ NEW method (today): Found {len(new_posts)} posts (increased limit)")
                except Exception as e:
                    logger.warning(f"❌ NEW method failed: {e}")
                
                try:
                    self._rate_limit()
                    hot_posts = list(subreddit.hot(limit=today_posts_per_method))
                    # Add all posts without filtering - only check for duplicates
                    for post in hot_posts:
                        if not any(p['id'] == post.id for p in all_posts):
                            all_posts.append(self._format_post(post))
                    logger.info(f"✅ HOT method (today): Found {len(hot_posts)} posts (increased limit)")
                except Exception as e:
                    logger.warning(f"❌ HOT method failed: {e}")
                    
            elif time_range == "last_week":
                # For last week: Use 'top' with week filter
                try:
                    self._rate_limit()
                    top_posts = list(subreddit.top(time_filter="week", limit=posts_per_method))
                    for post in top_posts:
                        if self._post_matches_query(post, query):
                            all_posts.append(self._format_post(post))
                    logger.info(f"✅ TOP method (week): Found {len([p for p in top_posts if self._post_matches_query(p, query)])} matching posts")
                except Exception as e:
                    logger.warning(f"❌ TOP method (week) failed: {e}")
                    
            elif time_range == "last_month":
                # For last month: Use 'top' with month filter
                try:
                    self._rate_limit()
                    top_posts = list(subreddit.top(time_filter="month", limit=posts_per_method))
                    for post in top_posts:
                        if self._post_matches_query(post, query):
                            all_posts.append(self._format_post(post))
                    logger.info(f"✅ TOP method (month): Found {len([p for p in top_posts if self._post_matches_query(p, query)])} matching posts")
                except Exception as e:
                    logger.warning(f"❌ TOP method (month) failed: {e}")
                    
            elif time_range == "all_time":
                # For all time: Use 'top' with all filter
                try:
                    self._rate_limit()
                    top_posts = list(subreddit.top(time_filter="all", limit=posts_per_method))
                    for post in top_posts:
                        if self._post_matches_query(post, query):
                            all_posts.append(self._format_post(post))
                    logger.info(f"✅ TOP method (all): Found {len([p for p in top_posts if self._post_matches_query(p, query)])} matching posts")
                except Exception as e:
                    logger.warning(f"❌ TOP method (all) failed: {e}")
            
            # If we don't have enough posts, try search API variations
            if len(all_posts) < limit and query.strip():
                search_variations = self._generate_search_variations(query)
                for variation in search_variations[:2]:  # Try top 2 variations
                    if len(all_posts) >= limit:
                        break
                    try:
                        self._rate_limit()
                        # Set current time range for search API to use
                        self._current_time_range = time_range
                        search_posts = self.fetch_posts_search_api(subreddit_name, variation, min(10, limit - len(all_posts)))
                        for post in search_posts:
                            if not any(p['id'] == post['id'] for p in all_posts):
                                all_posts.append(post)
                        logger.info(f"✅ SEARCH variation '{variation}': Found {len(search_posts)} new posts")
                    except Exception as e:
                        logger.warning(f"❌ SEARCH variation '{variation}' failed: {e}")
            
            logger.info(f"🎯 MULTIPLE METHODS RESULT: {len(all_posts)} total unique posts from r/{subreddit_name} (time_range: {time_range})")
            return all_posts[:limit]
            
        except Exception as e:
            logger.error(f"❌ MULTIPLE METHODS failed for r/{subreddit_name}: {e}")
            return []
    
    def _generate_search_variations(self, query: str) -> List[str]:
        """Generate search query variations for better coverage"""
        variations = [query]  # Original query first
        
        # Add variations with different keywords
        words = query.lower().split()
        if len(words) > 1:
            # Try with "help" added
            variations.append(f"{query} help")
            # Try with "struggling" added
            variations.append(f"{query} struggling")
            # Try with "problem" added
            variations.append(f"{query} problem")
        
        return variations[:5]  # Limit to 5 variations
    
    def _post_matches_query(self, post, query: str) -> bool:
        """Check if a post matches the search query"""
        if not query.strip():
            return True
        
        query_lower = query.lower()
        title_lower = post.title.lower()
        selftext_lower = (post.selftext or "").lower()
        
        # Check if any query words appear in title or content
        query_words = query_lower.split()
        return any(word in title_lower or word in selftext_lower for word in query_words)
    
    def fetch_posts_search_api(self, subreddit_name: str, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch posts using Reddit's search API for better relevance"""
        try:
            import requests
            
            # Use Reddit's search API
            url = f"https://www.reddit.com/r/{subreddit_name}/search.json"
            params = {
                'q': query,
                'sort': 'relevance',
                'limit': min(limit, 100),  # Reddit API limit
                'restrict_sr': '1'  # Restrict to subreddit
            }
            
            headers = {
                'User-Agent': settings.reddit_user_agent
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            posts = []
            
            if 'data' in data and 'children' in data['data']:
                for child in data['data']['children']:
                    post_data = child['data']
                    posts.append({
                        'id': post_data['id'],
                        'title': post_data['title'],
                        'text': post_data.get('selftext', ''),  # Changed from 'selftext' to 'text'
                        'selftext': post_data.get('selftext', ''),
                        'author': post_data.get('author', '[deleted]'),
                        'score': post_data.get('score', 0),
                        'created_utc': post_data.get('created_utc', 0),
                        'subreddit': post_data.get('subreddit', subreddit_name),
                        'url': f"https://www.reddit.com{post_data.get('permalink', '')}",
                        'permalink': f"https://www.reddit.com{post_data.get('permalink', '')}",
                        'num_comments': post_data.get('num_comments', 0)
                    })
            
            logger.info(f"🔍 SEARCH API: Found {len(posts)} posts for query '{query}' in r/{subreddit_name}")
            
            # Apply time filtering if time_range is specified
            if hasattr(self, '_current_time_range') and self._current_time_range != "all_time":
                posts = self._filter_posts_by_time(posts, self._current_time_range)
                logger.info(f"🕒 TIME FILTERING: Filtered to {len(posts)} posts for time_range: {self._current_time_range}")
            
            return posts
            
        except Exception as e:
            logger.error(f"❌ SEARCH API failed for r/{subreddit_name} with query '{query}': {e}")
            return []
    
    def _format_post(self, post) -> Dict[str, Any]:
        """Format a PRAW submission object into our standard post format"""
        return {
            'id': post.id,
            'title': post.title,
            'text': post.selftext or "",  # This is the missing 'text' field!
            'author': str(post.author) if post.author else '[deleted]',
            'score': post.score,
            'created_utc': post.created_utc,
            'subreddit': post.subreddit.display_name,
            'permalink': f"https://www.reddit.com{post.permalink}",
            'num_comments': post.num_comments
        }
    
    def _filter_posts_by_time(self, posts: List[Dict[str, Any]], time_range: str) -> List[Dict[str, Any]]:
        """Filter posts by time range"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        filtered_posts = []
        
        for post in posts:
            try:
                post_date = datetime.fromtimestamp(post["created_utc"])
                time_diff = now - post_date
                
                if time_range == "today":
                    # Only posts from today (within 24 hours)
                    if time_diff.days == 0:
                        filtered_posts.append(post)
                elif time_range == "last_week":
                    # Posts from last 7 days
                    if time_diff.days <= 7:
                        filtered_posts.append(post)
                elif time_range == "last_month":
                    # Posts from last 30 days
                    if time_diff.days <= 30:
                        filtered_posts.append(post)
                else:
                    # For all_time or unknown ranges, include all posts
                    filtered_posts.append(post)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Error processing post date for time filtering: {e}")
                # Include post if we can't parse the date
                filtered_posts.append(post)
        
        logger.info(f"🕒 TIME FILTER: {len(posts)} posts -> {len(filtered_posts)} posts (time_range: {time_range})")
        return filtered_posts
