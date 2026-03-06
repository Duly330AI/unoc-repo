package main

import (
	"database/sql"
	"fmt"
	"net"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/rs/zerolog"
	"google.golang.org/grpc"
	"google.golang.org/grpc/health"
	"google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"

	_ "github.com/lib/pq"

	"github.com/unoc/engine-go/internal/optical"
	pb "github.com/unoc/engine-go/proto/optical"
)

func main() {
	// Setup logger
	logger := zerolog.New(os.Stdout).With().
		Timestamp().
		Str("service", "optical-service").
		Logger()

	// Get configuration from environment
	port := getEnv("OPTICAL_SERVICE_PORT", "50051")
	dbURL := getEnv("DATABASE_URL", "postgresql://unoc:unocpw@localhost:5432/unocdb")

	// Add sslmode=disable if not already present (local dev PostgreSQL)
	if len(dbURL) > 0 && !containsSSLMode(dbURL) {
		if containsQueryParams(dbURL) {
			dbURL += "&sslmode=disable"
		} else {
			dbURL += "?sslmode=disable"
		}
	}

	logger.Info().
		Str("port", port).
		Str("db_url_masked", maskDBPassword(dbURL)).
		Msg("Starting Optical Compute Service")

	// Connect to database
	db, err := sql.Open("postgres", dbURL)
	if err != nil {
		logger.Fatal().Err(err).Msg("Failed to connect to database")
	}
	defer db.Close()

	// Verify DB connection
	if err := db.Ping(); err != nil {
		logger.Fatal().Err(err).Msg("Failed to ping database")
	}
	logger.Info().Msg("Database connection established")

	// Create gRPC server
	grpcServer := grpc.NewServer()

	// Register optical service
	opticalSvc := optical.NewService(db, logger)
	pb.RegisterOpticalServiceServer(grpcServer, opticalSvc)

	// Register health check service
	healthSvc := health.NewServer()
	healthSvc.SetServingStatus("optical.OpticalService", grpc_health_v1.HealthCheckResponse_SERVING)
	grpc_health_v1.RegisterHealthServer(grpcServer, healthSvc)

	// Enable reflection (for grpcurl/debugging)
	reflection.Register(grpcServer)

	// Start listening
	lis, err := net.Listen("tcp", fmt.Sprintf(":%s", port))
	if err != nil {
		logger.Fatal().Err(err).Msg("Failed to listen")
	}

	// Graceful shutdown handler
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
		<-sigChan

		logger.Info().Msg("Received shutdown signal, stopping gracefully...")
		healthSvc.SetServingStatus("optical.OpticalService", grpc_health_v1.HealthCheckResponse_NOT_SERVING)
		grpcServer.GracefulStop()
		logger.Info().Msg("Server stopped")
	}()

	logger.Info().
		Str("address", lis.Addr().String()).
		Msg("Optical Compute Service listening")

	// Start serving (blocks until shutdown)
	if err := grpcServer.Serve(lis); err != nil {
		logger.Fatal().Err(err).Msg("Failed to serve")
	}
}

// getEnv retrieves environment variable or returns default value
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// maskDBPassword masks password in database URL for logging
func maskDBPassword(dbURL string) string {
	// Simple masking for postgres://user:password@host:port/db
	// Replace password with ****
	if len(dbURL) < 15 {
		return "****"
	}
	// Basic masking (production code should use proper URL parsing)
	return dbURL[:12] + "****" + dbURL[len(dbURL)-20:]
}

// containsSSLMode checks if URL already has sslmode parameter
func containsSSLMode(dbURL string) bool {
	return strings.Contains(dbURL, "sslmode=")
}

// containsQueryParams checks if URL already has query parameters
func containsQueryParams(dbURL string) bool {
	return strings.Contains(dbURL, "?")
}
