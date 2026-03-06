// Package optical provides optical path computation for ONT signal budget analysis.
// This file implements parallel path resolution using goroutine worker pools.
//
// Week 2 Day 8: Parallel Processing
// Target: 5-10× additional speedup from concurrent path resolution
package optical

import (
	"context"
	"fmt"
	"sync"
)

// PathResolutionResult represents the result of resolving a single ONT's path.
type PathResolutionResult struct {
	ONTID  string
	Result *OpticalPathResult
	Error  error
}

// ResolveOpticalPathsParallel resolves optical paths for multiple ONTs concurrently.
// Uses a bounded worker pool to control concurrency and avoid resource exhaustion.
//
// Parameters:
//   - ctx: Context for cancellation and timeout
//   - g: Optical graph (shared read-only, safe for concurrent access)
//   - ontIDs: List of ONT IDs to resolve paths for
//   - fiberTypes: Fiber type catalog (shared read-only)
//   - workers: Number of concurrent workers (recommended: 10-20)
//
// Returns:
//   - map[string]*OpticalPathResult: Resolved paths keyed by ONT ID
//   - error: Non-nil if context cancelled or critical error
//
// Algorithm:
//  1. Create buffered channels for work distribution and results
//  2. Start N worker goroutines (bounded concurrency)
//  3. Fan-out: Send ONT IDs to workers via channel
//  4. Workers: Process ONT IDs, send results back
//  5. Fan-in: Collect all results into map
//  6. Return aggregated results
//
// Performance:
//   - Sequential: 50 ONTs × 50ms = 2500ms
//   - Parallel (10 workers): 50 ONTs / 10 × 50ms = 250ms (10× speedup)
//   - Parallel (20 workers): 50 ONTs / 20 × 50ms = 125ms (20× speedup)
//
// Example:
//
//	results, err := ResolveOpticalPathsParallel(ctx, graph, ontIDs, fiberTypes, 10)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	for ontID, result := range results {
//	    fmt.Printf("ONT %s: %.2f dB\n", ontID, result.TotalAttenuationDB)
//	}
func ResolveOpticalPathsParallel(
	ctx context.Context,
	g *Graph,
	ontIDs []string,
	fiberTypes map[string]FiberType,
	workers int,
) (map[string]*OpticalPathResult, error) {
	if g == nil {
		return nil, fmt.Errorf("graph is nil")
	}

	if len(ontIDs) == 0 {
		return make(map[string]*OpticalPathResult), nil
	}

	// Bound workers to reasonable range
	if workers <= 0 {
		workers = 10 // Default
	}
	if workers > len(ontIDs) {
		workers = len(ontIDs) // No point having more workers than ONTs
	}

	// Channels for work distribution and results
	ontChan := make(chan string, len(ontIDs))
	resultChan := make(chan PathResolutionResult, len(ontIDs))

	// WaitGroup to track worker completion
	var wg sync.WaitGroup

	// Start worker goroutines
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()

			for ontID := range ontChan {
				// Check context cancellation
				select {
				case <-ctx.Done():
					resultChan <- PathResolutionResult{
						ONTID: ontID,
						Error: ctx.Err(),
					}
					return
				default:
				}

				// Resolve optical path for this ONT
				result, err := ResolveOpticalPath(g, ontID, fiberTypes)
				resultChan <- PathResolutionResult{
					ONTID:  ontID,
					Result: result,
					Error:  err,
				}
			}
		}(i)
	}

	// Fan-out: Send ONT IDs to workers
	go func() {
		for _, ontID := range ontIDs {
			select {
			case <-ctx.Done():
				close(ontChan)
				return
			case ontChan <- ontID:
			}
		}
		close(ontChan)
	}()

	// Fan-in: Collect results
	go func() {
		wg.Wait()
		close(resultChan)
	}()

	// Aggregate results into map
	results := make(map[string]*OpticalPathResult)
	errors := make(map[string]error)

	for res := range resultChan {
		if res.Error != nil {
			errors[res.ONTID] = res.Error
		} else if res.Result != nil {
			// Only add non-nil results (isolated ONTs may have nil result with nil error)
			results[res.ONTID] = res.Result
		}
	}

	// If context was cancelled, return error
	if ctx.Err() != nil {
		return nil, ctx.Err()
	}

	// If all ONTs failed, return error
	if len(errors) == len(ontIDs) && len(errors) > 0 {
		return nil, fmt.Errorf("all %d ONT path resolutions failed", len(errors))
	}

	// Return results (partial results are OK - some ONTs may not have paths)
	return results, nil
}

// ResolveOpticalPathsSequential resolves optical paths for multiple ONTs sequentially.
// This is a fallback implementation when parallel processing is not desired.
// Used for testing and debugging.
func ResolveOpticalPathsSequential(
	ctx context.Context,
	g *Graph,
	ontIDs []string,
	fiberTypes map[string]FiberType,
) (map[string]*OpticalPathResult, error) {
	if g == nil {
		return nil, fmt.Errorf("graph is nil")
	}

	results := make(map[string]*OpticalPathResult)

	for _, ontID := range ontIDs {
		// Check context cancellation
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		result, err := ResolveOpticalPath(g, ontID, fiberTypes)
		if err != nil {
			// Log error but continue (some ONTs may not have paths)
			continue
		}
		if result != nil {
			results[ontID] = result
		}
	}

	return results, nil
}

// ParallelConfig holds configuration for parallel path resolution.
type ParallelConfig struct {
	// MaxWorkers is the maximum number of concurrent workers
	MaxWorkers int

	// BatchSize is the number of ONTs to process in a single batch
	// Used for very large ONT counts (1000+) to avoid memory pressure
	BatchSize int
}

// DefaultParallelConfig returns a sensible default configuration.
func DefaultParallelConfig() ParallelConfig {
	return ParallelConfig{
		MaxWorkers: 10,
		BatchSize:  1000, // Process up to 1000 ONTs at once
	}
}

// ResolveOpticalPathsBatched resolves paths for a large number of ONTs in batches.
// This prevents memory exhaustion when processing thousands of ONTs.
//
// Example: 10,000 ONTs with batchSize=1000
//   - Process 10 batches of 1000 ONTs each
//   - Each batch uses parallel workers
//   - Total time: ~10 seconds (vs ~5 minutes sequential)
func ResolveOpticalPathsBatched(
	ctx context.Context,
	g *Graph,
	ontIDs []string,
	fiberTypes map[string]FiberType,
	config ParallelConfig,
) (map[string]*OpticalPathResult, error) {
	if g == nil {
		return nil, fmt.Errorf("graph is nil")
	}

	if len(ontIDs) == 0 {
		return make(map[string]*OpticalPathResult), nil
	}

	allResults := make(map[string]*OpticalPathResult)
	var mu sync.Mutex // Protect allResults from concurrent writes

	// Process ONTs in batches
	for i := 0; i < len(ontIDs); i += config.BatchSize {
		// Check context cancellation
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		// Determine batch bounds
		end := i + config.BatchSize
		if end > len(ontIDs) {
			end = len(ontIDs)
		}
		batch := ontIDs[i:end]

		// Process batch in parallel
		batchResults, err := ResolveOpticalPathsParallel(ctx, g, batch, fiberTypes, config.MaxWorkers)
		if err != nil {
			return nil, fmt.Errorf("batch %d-%d failed: %w", i, end, err)
		}

		// Merge batch results into allResults
		mu.Lock()
		for ontID, result := range batchResults {
			allResults[ontID] = result
		}
		mu.Unlock()
	}

	return allResults, nil
}
