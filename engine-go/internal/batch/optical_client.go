package batch

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	pb "github.com/unoc/engine-go/proto/optical"
)

// OpticalClient wraps gRPC connection to optical service
type OpticalClient struct {
	conn   *grpc.ClientConn
	client pb.OpticalServiceClient
	logger zerolog.Logger
}

// NewOpticalClient creates a new optical service client
// Default address: localhost:50051 (optical service port from Day 17)
func NewOpticalClient(address string, logger zerolog.Logger) (*OpticalClient, error) {
	if address == "" {
		address = "localhost:50051"
	}

	// Create gRPC connection (insecure for local services)
	conn, err := grpc.NewClient(
		address,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to optical service: %w", err)
	}

	client := pb.NewOpticalServiceClient(conn)

	// Test connection with health check
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	healthReq := &pb.HealthRequest{}
	_, err = client.Health(ctx, healthReq)
	if err != nil {
		conn.Close()
		logger.Warn().
			Str("address", address).
			Err(err).
			Msg("Optical service unavailable - will skip optical recompute")
		return nil, fmt.Errorf("optical service health check failed: %w", err)
	}

	logger.Info().
		Str("address", address).
		Msg("Connected to optical service")

	return &OpticalClient{
		conn:   conn,
		client: client,
		logger: logger,
	}, nil
}

// RecomputeForLinks triggers optical path recompute for given link IDs
// This is the critical optimization: call once with all link IDs instead of 64 separate calls
func (oc *OpticalClient) RecomputeForLinks(ctx context.Context, linkIDs []string) error {
	if len(linkIDs) == 0 {
		return nil
	}

	start := time.Now()

	req := &pb.RecomputeRequest{
		LinkIds:   linkIDs,
		RequestId: nil, // Optional: could add batch correlation ID here
	}

	resp, err := oc.client.RecomputePaths(ctx, req)
	if err != nil {
		oc.logger.Error().
			Err(err).
			Int("link_count", len(linkIDs)).
			Msg("Optical recompute failed")
		return fmt.Errorf("optical recompute failed: %w", err)
	}

	duration := time.Since(start)

	oc.logger.Info().
		Int("link_count", len(linkIDs)).
		Int32("affected_onts", resp.AffectedOnts).
		Int64("duration_ms", resp.DurationMs).
		Dur("client_duration", duration).
		Str("status", resp.Status).
		Msg("Optical recompute completed")

	if resp.Status != "success" {
		return fmt.Errorf("optical recompute status: %s, errors: %v", resp.Status, resp.Errors)
	}

	return nil
}

// Close closes the gRPC connection
func (oc *OpticalClient) Close() error {
	if oc.conn != nil {
		return oc.conn.Close()
	}
	return nil
}
