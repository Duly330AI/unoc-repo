package api

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
	"github.com/unoc/engine-go/internal/db"
)

// Server represents the HTTP server
type Server struct {
	router *gin.Engine
}

// NewServer creates a new HTTP server
func NewServer() *Server {
	// Set Gin mode based on environment
	gin.SetMode(gin.ReleaseMode)

	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(requestLogger())

	server := &Server{router: router}
	server.setupRoutes()

	return server
}

// setupRoutes configures the API routes
func (s *Server) setupRoutes() {
	// Health check endpoint
	s.router.GET("/health", s.healthHandler)

	// API v1 group
	v1 := s.router.Group("/api/v1")
	{
		v1.GET("/health", s.healthHandler)
		v1.POST("/tick", s.tickHandler)
		v1.GET("/snapshot", s.snapshotHandler)
	}
}

// healthHandler handles health check requests
func (s *Server) healthHandler(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 2*time.Second)
	defer cancel()

	// Check database health
	dbStatus := "healthy"
	if err := db.HealthCheck(ctx); err != nil {
		log.Error().Err(err).Msg("Database health check failed")
		dbStatus = "unhealthy"
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"status":   "unhealthy",
			"database": dbStatus,
			"error":    err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":   "healthy",
		"database": dbStatus,
		"version":  "0.1.0",
	})
}

// Run starts the HTTP server
func (s *Server) Run(port string) error {
	log.Info().Str("port", port).Msg("Starting HTTP server")
	return s.router.Run(":" + port)
}

// requestLogger is a custom middleware for logging HTTP requests
func requestLogger() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		method := c.Request.Method

		c.Next()

		duration := time.Since(start)
		statusCode := c.Writer.Status()

		log.Info().
			Str("method", method).
			Str("path", path).
			Int("status", statusCode).
			Dur("duration_ms", duration).
			Msg("HTTP request")
	}
}
