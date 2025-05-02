"""Rate limiting utilities for API calls."""

import time
import random
import logging
import threading
import queue
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)

# Type for callbacks
T = TypeVar('T')

class TokenBucket:
    """Token bucket rate limiter."""
    
    def __init__(self, tokens_per_minute: float, max_tokens: float):
        """Initialize the token bucket.
        
        Args:
            tokens_per_minute: Number of tokens to add per minute
            max_tokens: Maximum tokens the bucket can hold
        """
        self.tokens_per_second = tokens_per_minute / 60.0
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.last_refill_time = time.time()
        self.lock = threading.Lock()
        
    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            bool: True if tokens were consumed, False otherwise
        """
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
            
    def wait_for_tokens(self, tokens: float = 1.0, max_wait: float = 60.0) -> bool:
        """Wait until tokens are available.
        
        Args:
            tokens: Number of tokens to consume
            max_wait: Maximum time to wait in seconds
            
        Returns:
            bool: True if tokens were consumed, False if timeout
        """
        start_time = time.time()
        while (time.time() - start_time) < max_wait:
            if self.consume(tokens):
                return True
            # Sleep for a short time to avoid busy waiting
            time.sleep(0.1)
        return False
    
    def _refill(self):
        """Refill the token bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill_time
        if elapsed > 0:
            self.tokens = min(self.max_tokens, self.tokens + (elapsed * self.tokens_per_second))
            self.last_refill_time = now

class RateLimitedAPIClient:
    """Rate-limited API client wrapper."""
    
    def __init__(
        self, 
        name: str,
        min_request_interval: float = 1.0,
        tokens_per_minute: float = 20.0,
        max_tokens: float = 20.0
    ):
        """Initialize the rate limited API client.
        
        Args:
            name: Name of the API for logging
            min_request_interval: Minimum interval between requests in seconds
            tokens_per_minute: Number of tokens to add per minute
            max_tokens: Maximum tokens the bucket can hold
        """
        self.name = name
        self.min_request_interval = min_request_interval
        self.token_bucket = TokenBucket(tokens_per_minute, max_tokens)
        self.last_request_time = 0
        self.request_lock = threading.Lock()
    
    def execute(
        self, 
        func: Callable[..., T], 
        *args: Any, 
        max_retries: int = 3, 
        initial_backoff: float = 1.0,
        **kwargs: Any
    ) -> Optional[T]:
        """Execute a function with rate limiting.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            max_retries: Maximum number of retries
            initial_backoff: Initial backoff time in seconds
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Optional[T]: Result of the function call or None if it failed
        """
        retry_count = 0
        backoff = initial_backoff
        
        # Wait for tokens
        if not self.token_bucket.wait_for_tokens():
            logger.warning(f"{self.name} API: Could not get token, giving up")
            return None
            
        # Ensure minimum interval between requests
        with self.request_lock:
            now = time.time()
            since_last = now - self.last_request_time
            if since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - since_last
                logger.info(f"{self.name} API: Enforcing minimum interval, waiting {sleep_time:.2f}s")
                time.sleep(sleep_time)
            self.last_request_time = time.time()
        
        # Execute with retries
        while retry_count <= max_retries:
            try:
                logger.info(f"{self.name} API: Executing request (attempt {retry_count+1}/{max_retries+1})")
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.warning(f"{self.name} API: Failed after {max_retries} retries: {str(e)}")
                    return None
                
                jitter = random.uniform(0, 0.1 * backoff)
                sleep_time = backoff + jitter
                logger.warning(f"{self.name} API: Request failed. Retrying in {sleep_time:.2f}s. Retry {retry_count}/{max_retries}")
                time.sleep(sleep_time)
                backoff *= 2  # Exponential backoff
                
        return None


class QueuedWorker:
    """Worker that processes tasks from a queue."""
    
    def __init__(
        self, 
        name: str,
        thread_count: int = 1,
        rate_limiter: Optional[RateLimitedAPIClient] = None
    ):
        """Initialize the queued worker.
        
        Args:
            name: Name of the worker for logging
            thread_count: Number of worker threads
            rate_limiter: Optional rate limiter
        """
        self.name = name
        self.task_queue = queue.Queue()
        self.threads = []
        self.rate_limiter = rate_limiter
        self.running = True
        
        # Start worker threads
        for i in range(thread_count):
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"{name}-worker-{i}",
                daemon=True
            )
            self.threads.append(thread)
            thread.start()
    
    def _worker_loop(self):
        """Worker thread that processes tasks from the queue."""
        while self.running:
            try:
                # Get a task from the queue
                task = self.task_queue.get(timeout=1.0)
                if task is None:
                    # None is a signal to stop the worker
                    self.task_queue.task_done()
                    break
                    
                func, args, kwargs, callback = task
                
                # Execute the task with rate limiting if available
                if self.rate_limiter:
                    result = self.rate_limiter.execute(func, *args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                    
                # Call the callback with the result
                if callback:
                    callback(result)
                    
                # Mark the task as done
                self.task_queue.task_done()
            except queue.Empty:
                # No tasks in the queue, just continue
                continue
            except Exception as e:
                logger.error(f"{self.name} worker: Error processing task: {str(e)}")
                # Keep the worker running despite errors
    
    def enqueue(
        self, 
        func: Callable[..., T], 
        *args: Any, 
        callback: Optional[Callable[[T], None]] = None,
        **kwargs: Any
    ) -> None:
        """Enqueue a task for processing.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            callback: Optional callback to call with the result
            **kwargs: Keyword arguments to pass to the function
        """
        self.task_queue.put((func, args, kwargs, callback))
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all tasks in the queue to complete.
        
        Args:
            timeout: Timeout in seconds, or None for no timeout
            
        Returns:
            bool: True if all tasks completed, False if timeout
        """
        try:
            self.task_queue.join(timeout=timeout)
            return True
        except queue.Empty:
            return False
    
    def shutdown(self, wait: bool = True):
        """Shutdown the worker.
        
        Args:
            wait: Whether to wait for all tasks to complete
        """
        self.running = False
        
        # Signal all worker threads to stop
        for _ in self.threads:
            self.task_queue.put(None)
            
        # Wait for worker threads to complete
        if wait:
            for thread in self.threads:
                thread.join()
                
        self.threads = [] 