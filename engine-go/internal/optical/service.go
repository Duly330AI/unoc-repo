package optical

import (
	"context"
	"database/sql"
	"time"

	"github.com/rs/zerolog"

	pb "github.com/unoc/engine-go/proto/optical"
)

// Service implements the optical computation gRPC service
type Service struct {
	pb.UnimplementedOpticalServiceServer
	db         *sql.DB
	logger     zerolog.Logger
	pathfinder *PathFinder

	// Metrics
	startTime         time.Time
	totalRecomputes   int64
	lastRecomputeTime time.Time
}

// NewService creates a new optical service instance
func NewService(db *sql.DB, logger zerolog.Logger) *Service {
	return &Service{
		db:         db,
		logger:     logger.With().Str("service", "optical").Logger(),
		pathfinder: NewPathFinder(db),
		startTime:  time.Now(),
	}
}

// RecomputePaths recomputes optical paths for affected ONTs
// TODO: Week 2 implementation (currently stub for Week 1 scaffolding)
func (s *Service) RecomputePaths(ctx context.Context, req *pb.RecomputeRequest) (*pb.RecomputeResponse, error) {
	s.logger.Info().
		Int("link_ids_count", len(req.GetLinkIds())).
		Int("device_ids_count", len(req.GetDeviceIds())).
		Bool("force_full_recompute", req.GetForceFullRecompute()).
		Str("request_id", req.GetRequestId()).
		Msg("RecomputePaths called (stub)")

	// TODO Week 2:
	// 1. Fetch affected ONTs from DB
	// 2. Compute Dijkstra for each ONT
	// 3. Calculate signal budgets
	// 4. Update DB with new paths
	// 5. Return affected ONT IDs

	// Stub response
	return &pb.RecomputeResponse{
		Status:       "not_implemented",
		AffectedOnts: 0,
		OntIds:       []string{},
		DurationMs:   0,
		Errors:       []string{"Week 2: Full implementation pending"},
	}, nil
}

// GetPath retrieves the optical path for a single ONT
func (s *Service) GetPath(ctx context.Context, req *pb.GetPathRequest) (*pb.OpticalPath, error) {
	s.logger.Info().
		Str("ont_id", req.GetOntId()).
		Str("request_id", req.GetRequestId()).
		Msg("GetPath called")

	// Call PathFinder to resolve the optical path
	result, err := s.pathfinder.ResolveOpticalPath(ctx, req.GetOntId())
	if err != nil {
		s.logger.Error().
			Err(err).
			Str("ont_id", req.GetOntId()).
			Msg("PathFinder error")
		return nil, err
	}

	// If no path found (ONT doesn't exist or no route to OLT)
	if result == nil {
		s.logger.Warn().
			Str("ont_id", req.GetOntId()).
			Msg("No path found for ONT")
		return &pb.OpticalPath{
			OntId:  req.GetOntId(),
			Status: "no_path",
		}, nil
	}

	// Map PathSegment → pb.PathSegment
	segments := make([]*pb.PathSegment, len(result.Segments))
	for i, seg := range result.Segments {
		linkID := ""
		if seg.LinkID != nil {
			linkID = *seg.LinkID
		}
		segments[i] = &pb.PathSegment{
			FromDeviceId:  seg.Src,
			ToDeviceId:    seg.Dst,
			LinkId:        linkID,
			AttenuationDb: seg.AttenuationDB,
		}
	}

	s.logger.Info().
		Str("ont_id", req.GetOntId()).
		Str("olt_id", result.OLTID).
		Int("segments", len(segments)).
		Float64("total_attenuation_db", result.TotalAttenuationDB).
		Msg("Path resolved successfully")

	return &pb.OpticalPath{
		OntId:              req.GetOntId(),
		OltId:              result.OLTID,
		Segments:           segments,
		TotalAttenuationDb: result.TotalAttenuationDB,
		Status:             "ok",
	}, nil
}

// Health returns service health status
// IMPLEMENTED: DB connectivity check + optional stats
func (s *Service) Health(ctx context.Context, req *pb.HealthRequest) (*pb.HealthResponse, error) {
	resp := &pb.HealthResponse{
		Status:        "healthy",
		Version:       "1.0.0",
		UptimeSeconds: int64(time.Since(s.startTime).Seconds()),
	}

	// Check DB connectivity
	if err := s.db.PingContext(ctx); err != nil {
		s.logger.Error().Err(err).Msg("DB ping failed")
		resp.Status = "unhealthy"
		resp.DbStatus = "disconnected"
		return resp, nil
	}
	resp.DbStatus = "connected"

	// Always try to fetch ONT count (no conditional flag in proto)
	var totalOnts int32
	err := s.db.QueryRowContext(ctx, `
		SELECT COUNT(*) 
		FROM device 
		WHERE type = 'ONT'
	`).Scan(&totalOnts)

	if err != nil {
		s.logger.Warn().Err(err).Msg("Failed to query ONT count")
	} else {
		resp.TotalOnts = &totalOnts
	}

	// Add last recompute timestamp if available
	if !s.lastRecomputeTime.IsZero() {
		ts := s.lastRecomputeTime.Unix()
		resp.LastRecomputeTimestamp = &ts
	}

	s.logger.Debug().
		Str("status", resp.Status).
		Str("db_status", resp.DbStatus).
		Int64("uptime_seconds", resp.UptimeSeconds).
		Msg("Health check")

	return resp, nil
}
