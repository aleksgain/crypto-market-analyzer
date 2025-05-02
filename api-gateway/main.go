package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
)

var (
	backendURL = getEnv("BACKEND_URL", "http://backend:5000")
	redisURL   = getEnv("REDIS_URL", "redis://redis:6379/0")
	logLevel   = getEnv("LOG_LEVEL", "INFO")
	ctx        = context.Background()
	rdb        *redis.Client
)

func init() {
	// Configure logging based on LOG_LEVEL
	configureLogging()

	// Parse Redis URL and create client
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatalf("Error parsing Redis URL: %v", err)
	}
	rdb = redis.NewClient(opt)

	// Test Redis connection
	_, err = rdb.Ping(ctx).Result()
	if err != nil {
		log.Fatalf("Error connecting to Redis: %v", err)
	}
	log.Println("Connected to Redis successfully")
}

// configureLogging sets up logging based on LOG_LEVEL
func configureLogging() {
	// Set Gin mode based on GIN_MODE env var
	ginMode := getEnv("GIN_MODE", "debug")
	if ginMode == "release" {
		gin.SetMode(gin.ReleaseMode)
	}

	// Default to minimal logging for production
	if strings.ToUpper(logLevel) == "ERROR" || strings.ToUpper(logLevel) == "WARN" ||
		strings.ToUpper(logLevel) == "WARNING" || strings.ToUpper(logLevel) == "CRITICAL" {
		// Disable debug logging for production
		gin.DefaultWriter = io.Discard
		log.Printf("Log level set to %s - detailed logs disabled", logLevel)
	} else {
		log.Printf("Log level set to %s - detailed logs enabled", logLevel)
	}
}

func main() {
	r := gin.Default()

	// Configure CORS for both development and production
	corsConfig := cors.DefaultConfig()
	corsConfig.AllowAllOrigins = false

	// In production, you'd replace these with your actual domains
	corsConfig.AllowOrigins = []string{
		"http://localhost:3000",
		"http://localhost:8080",
		"https://your-production-domain.com", // Replace with your actual domain
	}

	corsConfig.AllowMethods = []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
	corsConfig.AllowHeaders = []string{"Origin", "Content-Type", "Accept", "Authorization"}
	corsConfig.ExposeHeaders = []string{"Content-Length"}
	corsConfig.AllowCredentials = true
	corsConfig.MaxAge = 12 * time.Hour

	r.Use(cors.New(corsConfig))

	// Set up routes
	r.GET("/api/prices", cachedProxy("prices", 5*time.Minute))
	r.GET("/api/news", cachedProxy("news", 30*time.Minute))
	r.GET("/api/predictions", cachedProxy("predictions", 15*time.Minute))
	r.GET("/api/accuracy", cachedProxy("accuracy", 1*time.Hour))
	r.GET("/api/advanced-insights", cachedProxy("advanced-insights", 10*time.Minute))
	r.GET("/api/test-connectivity", directProxy) // Don't cache test endpoints
	r.GET("/api/test-eventregistry", directProxy)
	r.GET("/api/test-openai", directProxy)

	// Health check endpoint
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "ok",
			"time":   time.Now().Format(time.RFC3339),
		})
	})

	// Start server
	port := getEnv("PORT", "8080")
	log.Printf("Starting API gateway on port %s", port)
	if err := r.Run(fmt.Sprintf(":%s", port)); err != nil {
		log.Fatalf("Error starting server: %v", err)
	}
}

// cachedProxy creates a gin handler that caches responses in Redis
func cachedProxy(endpoint string, ttl time.Duration) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Build cache key from endpoint and query parameters
		cacheKey := fmt.Sprintf("cache:%s:%s", endpoint, c.Request.URL.RawQuery)

		// Try to get from cache
		cachedData, err := rdb.Get(ctx, cacheKey).Result()
		if err == nil {
			// Cache hit
			log.Printf("Cache hit for %s", cacheKey)
			c.Header("X-Cache", "HIT")
			c.Data(http.StatusOK, "application/json", []byte(cachedData))
			return
		}

		// Cache miss, proxy the request to the backend
		targetURL := fmt.Sprintf("%s/api/%s?%s", backendURL, endpoint, c.Request.URL.RawQuery)
		resp, err := http.Get(targetURL)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Error proxying request: %v", err)})
			return
		}
		defer resp.Body.Close()

		// Read the response body
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Error reading response: %v", err)})
			return
		}

		// Cache the response if it was successful
		if resp.StatusCode == http.StatusOK {
			if err := rdb.Set(ctx, cacheKey, body, ttl).Err(); err != nil {
				log.Printf("Error caching response: %v", err)
			} else {
				log.Printf("Cached response for %s with TTL %v", cacheKey, ttl)
			}
		}

		// Set original status code and headers
		c.Status(resp.StatusCode)
		for k, v := range resp.Header {
			for _, vv := range v {
				c.Header(k, vv)
			}
		}
		c.Header("X-Cache", "MISS")
		c.Data(resp.StatusCode, resp.Header.Get("Content-Type"), body)
	}
}

// directProxy creates a gin handler that directly proxies requests without caching
func directProxy(c *gin.Context) {
	targetURL := fmt.Sprintf("%s%s?%s", backendURL, c.Request.URL.Path, c.Request.URL.RawQuery)
	resp, err := http.Get(targetURL)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Error proxying request: %v", err)})
		return
	}
	defer resp.Body.Close()

	// Read the response body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Error reading response: %v", err)})
		return
	}

	// Set original status code and headers
	c.Status(resp.StatusCode)
	for k, v := range resp.Header {
		for _, vv := range v {
			c.Header(k, vv)
		}
	}
	c.Data(resp.StatusCode, resp.Header.Get("Content-Type"), body)
}

// getEnv gets an environment variable or returns a default value
func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}
