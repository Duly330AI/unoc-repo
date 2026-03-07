// Package optical implements optical path resolution.
// This is the Go port of resolve_optical_path from Python optical_path_resolver.py
//
// Week 2 Day 6: Path resolver with deterministic ordering
package optical

import (
	"fmt"
	"sort"
	"strings"
)

// ResolveOpticalPath finds the minimal-attenuation path from ONT to any reachable OLT.
// Returns nil if no path exists.
//
// Matches Python resolve_optical_path logic:
// - Uses Dijkstra with custom weights (fiber + passive insertion)
// - Deterministic ordering of candidates: attenuation → length → hops → OLT ID → path signature
// - Returns path segments with attenuation details
func ResolveOpticalPath(g *Graph, ontID string, fiberTypes map[string]FiberType) (*OpticalPathResult, error) {
	// Check if ONT exists in graph
	if _, ok := g.Nodes[ontID]; !ok {
		return nil, fmt.Errorf("ONT node %s not found in graph", ontID)
	}

	// Run Dijkstra from ONT with custom weight function
	weightFn := func(g *Graph, src, tgt string) float64 {
		return computeEdgeWeight(g, src, tgt, fiberTypes)
	}

	result, err := dijkstra(g, ontID, weightFn)
	if err != nil {
		return nil, fmt.Errorf("dijkstra failed: %w", err)
	}

	// Collect candidate OLTs that were reached
	type candidate struct {
		oltID         string
		attenuation   float64
		lengthKm      float64
		hopCount      int
		pathSignature string
		path          []string
	}

	var candidates []candidate
	for nodeID, distance := range result.Distances {
		node, ok := g.Nodes[nodeID]
		if !ok || !node.Type.IsOLT() {
			continue
		}

		path, ok := result.Paths[nodeID]
		if !ok || len(path) == 0 {
			continue
		}

		// Compute total physical path length (for tie-breaking)
		lengthKm := computePathLengthKm(g, path)
		hopCount := len(path) - 1
		pathSignature := strings.Join(path, ",")

		candidates = append(candidates, candidate{
			oltID:         nodeID,
			attenuation:   distance,
			lengthKm:      lengthKm,
			hopCount:      hopCount,
			pathSignature: pathSignature,
			path:          path,
		})
	}

	if len(candidates) == 0 {
		return nil, nil // No path to any OLT
	}

	// Deterministic ordering (matches Python):
	// 1. Attenuation (primary)
	// 2. Physical path length (secondary)
	// 3. Hop count (tertiary)
	// 4. OLT ID (quaternary)
	// 5. Path signature (quinary - for absolute determinism)
	sort.Slice(candidates, func(i, j int) bool {
		a, b := candidates[i], candidates[j]

		// 1. Compare attenuation
		if a.attenuation != b.attenuation {
			return a.attenuation < b.attenuation
		}

		// 2. Compare length
		if a.lengthKm != b.lengthKm {
			return a.lengthKm < b.lengthKm
		}

		// 3. Compare hop count
		if a.hopCount != b.hopCount {
			return a.hopCount < b.hopCount
		}

		// 4. Compare OLT ID
		if a.oltID != b.oltID {
			return a.oltID < b.oltID
		}

		// 5. Compare path signature (stable tie-break)
		return a.pathSignature < b.pathSignature
	})

	// Select best candidate (first after sorting)
	best := candidates[0]

	// Build path segments
	segments := buildPathSegments(g, best.path, fiberTypes)

	return &OpticalPathResult{
		OLTID:              best.oltID,
		TotalAttenuationDB: best.attenuation,
		Segments:           segments,
		TotalLengthKm:      best.lengthKm,
		HopCount:           best.hopCount,
	}, nil
}

// computePathLengthKm calculates total physical path length (km).
// Only sums known Link.length_km values (missing values contribute 0).
func computePathLengthKm(g *Graph, path []string) float64 {
	totalKm := 0.0
	for i := 0; i < len(path)-1; i++ {
		edge, ok := g.GetEdge(path[i], path[i+1])
		if ok && edge.HasLengthKm {
			totalKm += edge.LengthKm
		}
	}
	return totalKm
}

// buildPathSegments constructs path segments from a node path.
// Each segment includes source, destination, link ID, and attenuation.
func buildPathSegments(g *Graph, path []string, fiberTypes map[string]FiberType) []PathSegment {
	segments := make([]PathSegment, 0, len(path)-1)

	for i := 0; i < len(path)-1; i++ {
		srcID := path[i]
		dstID := path[i+1]

		// Get edge data
		edge, ok := g.GetEdge(srcID, dstID)

		// Compute attenuation for this segment
		attenuation := computeEdgeWeight(g, srcID, dstID, fiberTypes)

		var linkID *string
		if ok && edge.LinkID != "" {
			linkID = &edge.LinkID
		}

		segments = append(segments, PathSegment{
			Src:           srcID,
			Dst:           dstID,
			LinkID:        linkID,
			AttenuationDB: attenuation,
		})
	}

	return segments
}

// ResolveMultipleOpticalPaths resolves paths for multiple ONTs in parallel.
// This is a helper for batch operations (Week 2 Day 8: parallelism).
//
// For now, this is a simple sequential implementation.
// TODO Week 2 Day 8: Add goroutine worker pool for parallel processing.
func ResolveMultipleOpticalPaths(g *Graph, ontIDs []string, fiberTypes map[string]FiberType) (map[string]*OpticalPathResult, error) {
	results := make(map[string]*OpticalPathResult)

	for _, ontID := range ontIDs {
		result, err := ResolveOpticalPath(g, ontID, fiberTypes)
		if err != nil {
			return nil, fmt.Errorf("failed to resolve path for ONT %s: %w", ontID, err)
		}
		if result != nil {
			results[ontID] = result
		}
	}

	return results, nil
}
