package batch

import (
	"context"
	"database/sql"
	"time"

	"github.com/rs/zerolog"

	pb "github.com/unoc/engine-go/proto/batch"
)

// Service implements the batch operations gRPC service
type Service struct {
	pb.UnimplementedBatchServiceServer
	db            *sql.DB
	logger        zerolog.Logger
	opticalClient *OpticalClient // Week 3 Day 13: Single optical recompute coordination

	// Metrics
	startTime     time.Time
	totalBatchOps int64
	lastBatchTime time.Time
}

// NewService creates a new batch service instance
func NewService(db *sql.DB, logger zerolog.Logger) *Service {
	svcLogger := logger.With().Str("service", "batch").Logger()

	// Initialize optical client (Week 3 Day 13: Single recompute coordination)
	// If optical service is unavailable, log warning but continue (non-blocking)
	opticalClient, err := NewOpticalClient("localhost:50051", svcLogger)
	if err != nil {
		svcLogger.Warn().
			Err(err).
			Msg("Optical client initialization failed - batch operations will skip optical recompute")
	}

	return &Service{
		db:            db,
		logger:        svcLogger,
		opticalClient: opticalClient,
		startTime:     time.Now(),
	}
}

// NOTE: BatchCreateLinks is implemented in create.go (Week 3 Day 13)

// BatchDeleteLinks deletes multiple links in a single transaction
// TODO: Week 3 Day 14 implementation (currently stub)
func (s *Service) BatchDeleteLinks(ctx context.Context, req *pb.BatchDeleteLinksRequest) (*pb.BatchDeleteLinksResponse, error) {
	startTime := time.Now()

	s.logger.Info().
		Int("links_count", len(req.LinkIds)).
		Bool("force", req.Force).
		Str("request_id", req.RequestId).
		Msg("BatchDeleteLinks called (stub - Week 3 Day 14)")

	// TODO Day 14: Implement batch deletion logic
	return &pb.BatchDeleteLinksResponse{
		DeletedLinkIds: []string{},
		FailedDeletes:  []*pb.LinkDeletionFailure{},
		TotalRequested: int32(len(req.LinkIds)),
		TotalDeleted:   0,
		DurationMs:     time.Since(startTime).Milliseconds(),
		RequestId:      req.RequestId,
	}, nil
}

// HealthCheck returns service health status
func (s *Service) HealthCheck(ctx context.Context, req *pb.HealthCheckRequest) (*pb.HealthCheckResponse, error) {
	resp := &pb.HealthCheckResponse{
		Status:    "OK",
		Message:   "Batch service operational",
		Timestamp: time.Now().Unix(),
		Version:   "v1.0.0-week3-day13",
	}

	// Check DB connectivity
	if err := s.db.PingContext(ctx); err != nil {
		s.logger.Error().Err(err).Msg("DB ping failed")
		resp.Status = "DEGRADED"
		resp.Message = "Database connection failed"
		return resp, nil
	}

	s.logger.Debug().
		Str("status", resp.Status).
		Int64("timestamp", resp.Timestamp).
		Msg("Health check")

	return resp, nil
}
