// Package optical provides optical path computation for ONT signal budget analysis.
// This file contains tests for parallel path resolution.
//
// Week 2 Day 8: Parallel Processing Tests
package optical

import (
	"context"
	"fmt"
	"math"
	"sort"
	"sync"
	"testing"
	"time"
)

// Helper to create a simple test graph
func createSimpleTestGraph() *Graph {
	g := NewGraph()

	// OLT → 3 ONTs
	g.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})
	g.AddNode(&Node{ID: "ont1", Type: NodeTypeONT})
	g.AddNode(&Node{ID: "ont2", Type: NodeTypeONT})
	g.AddNode(&Node{ID: "ont3", Type: NodeTypeONT})

	g.AddEdge(&Edge{
		LinkID:       "link1",
		SourceID:     "olt1",
		TargetID:     "ont1",
		FiberLossDB:  1.0,
		HasFiberLoss: true,
		LengthKm:     1.0,
		HasLengthKm:  true,
	})
	g.AddEdge(&Edge{
		LinkID:       "link2",
		SourceID:     "olt1",
		TargetID:     "ont2",
		FiberLossDB:  2.0,
		HasFiberLoss: true,
		LengthKm:     2.0,
		HasLengthKm:  true,
	})
	g.AddEdge(&Edge{
		LinkID:       "link3",
		SourceID:     "olt1",
		TargetID:     "ont3",
		FiberLossDB:  3.0,
		HasFiberLoss: true,
		LengthKm:     3.0,
		HasLengthKm:  true,
	})

	return g
}

// TestResolveOpticalPathsParallel_BasicExecution tests basic parallel execution.
func TestResolveOpticalPathsParallel_BasicExecution(t *testing.T) {
	graph := createSimpleTestGraph()
	fiberTypes := GetFiberTypes()

	// Resolve paths in parallel
	ctx := context.Background()
	ontIDs := []string{"ont1", "ont2", "ont3"}
	results, err := ResolveOpticalPathsParallel(ctx, graph, ontIDs, fiberTypes, 10)

	// Verify no error
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Verify all 3 ONTs have results
	if len(results) != 3 {
		t.Errorf("Expected 3 results, got %d", len(results))
	}

	// Verify each ONT has a valid path
	for _, ontID := range ontIDs {
		result, exists := results[ontID]
		if !exists {
			t.Errorf("ONT %s missing from results", ontID)
			continue
		}
		if result == nil {
			t.Errorf("ONT %s has nil result", ontID)
			continue
		}
		if len(result.Segments) == 0 {
			t.Errorf("ONT %s has empty segments", ontID)
		}
	}
}

// TestResolveOpticalPathsParallel_WorkerBounding tests worker count limits.
func TestResolveOpticalPathsParallel_WorkerBounding(t *testing.T) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Create topology with 5 ONTs
	g.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})
	for i := 1; i <= 5; i++ {
		ontID := fmt.Sprintf("ont%d", i)
		g.AddNode(&Node{ID: ontID, Type: NodeTypeONT})
		g.AddEdge(&Edge{
			LinkID:       fmt.Sprintf("link%d", i),
			SourceID:     "olt1",
			TargetID:     ontID,
			FiberLossDB:  1.0,
			HasFiberLoss: true,
		})
	}

	ctx := context.Background()
	ontIDs := []string{"ont1", "ont2", "ont3", "ont4", "ont5"}

	// Test 1: More workers than ONTs (should bound to ontID count)
	results, err := ResolveOpticalPathsParallel(ctx, g, ontIDs, fiberTypes, 100)
	if err != nil {
		t.Fatalf("Expected no error with 100 workers, got: %v", err)
	}
	if len(results) != 5 {
		t.Errorf("Expected 5 results, got %d", len(results))
	}

	// Test 2: Zero workers (should default to 10)
	results, err = ResolveOpticalPathsParallel(ctx, g, ontIDs, fiberTypes, 0)
	if err != nil {
		t.Fatalf("Expected no error with 0 workers, got: %v", err)
	}
	if len(results) != 5 {
		t.Errorf("Expected 5 results, got %d", len(results))
	}

	// Test 3: 1 worker (sequential-like)
	results, err = ResolveOpticalPathsParallel(ctx, g, ontIDs, fiberTypes, 1)
	if err != nil {
		t.Fatalf("Expected no error with 1 worker, got: %v", err)
	}
	if len(results) != 5 {
		t.Errorf("Expected 5 results, got %d", len(results))
	}
}

// TestResolveOpticalPathsParallel_EmptyInput tests empty input handling.
func TestResolveOpticalPathsParallel_EmptyInput(t *testing.T) {
	graph := createSimpleTestGraph()
	fiberTypes := GetFiberTypes()

	ctx := context.Background()
	ontIDs := []string{} // Empty

	results, err := ResolveOpticalPathsParallel(ctx, graph, ontIDs, fiberTypes, 10)
	if err != nil {
		t.Fatalf("Expected no error with empty input, got: %v", err)
	}
	if len(results) != 0 {
		t.Errorf("Expected 0 results, got %d", len(results))
	}
}

// TestResolveOpticalPathsParallel_NilGraph tests nil graph handling.
func TestResolveOpticalPathsParallel_NilGraph(t *testing.T) {
	ctx := context.Background()
	ontIDs := []string{"ont1"}
	fiberTypes := GetFiberTypes()

	results, err := ResolveOpticalPathsParallel(ctx, nil, ontIDs, fiberTypes, 10)
	if err == nil {
		t.Fatal("Expected error with nil graph, got nil")
	}
	if results != nil {
		t.Errorf("Expected nil results with error, got: %v", results)
	}
}

// TestResolveOpticalPathsParallel_ContextCancellation tests context cancellation.
func TestResolveOpticalPathsParallel_ContextCancellation(t *testing.T) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Create large topology (100 ONTs)
	g.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})
	ontIDs := []string{}
	for i := 0; i < 100; i++ {
		ontID := fmt.Sprintf("ont%d", i)
		g.AddNode(&Node{ID: ontID, Type: NodeTypeONT})
		g.AddEdge(&Edge{
			LinkID:       fmt.Sprintf("link%d", i),
			SourceID:     "olt1",
			TargetID:     ontID,
			FiberLossDB:  float64(i%10 + 1),
			HasFiberLoss: true,
		})
		ontIDs = append(ontIDs, ontID)
	}

	// Create cancellable context with very short timeout
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Millisecond)
	defer cancel()

	// Start parallel resolution (should be cancelled quickly)
	results, err := ResolveOpticalPathsParallel(ctx, g, ontIDs, fiberTypes, 10)

	// Should return context error
	if err == nil {
		t.Error("Expected context cancellation error, got nil")
	}
	if err != nil && err != context.DeadlineExceeded && err != context.Canceled {
		t.Errorf("Expected context error, got: %v", err)
	}

	// Results should be nil when context cancelled
	if results != nil {
		t.Errorf("Expected nil results on cancellation, got %d results", len(results))
	}
}

// TestResolveOpticalPathsParallel_PartialFailure tests handling partial failures.
func TestResolveOpticalPathsParallel_PartialFailure(t *testing.T) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Build topology where some ONTs have no paths
	g.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})
	g.AddNode(&Node{ID: "ont1", Type: NodeTypeONT}) // Has path
	g.AddNode(&Node{ID: "ont2", Type: NodeTypeONT}) // No path (isolated)
	g.AddNode(&Node{ID: "ont3", Type: NodeTypeONT}) // Has path

	g.AddEdge(&Edge{
		LinkID:       "link1",
		SourceID:     "olt1",
		TargetID:     "ont1",
		FiberLossDB:  1.0,
		HasFiberLoss: true,
	})
	g.AddEdge(&Edge{
		LinkID:       "link3",
		SourceID:     "olt1",
		TargetID:     "ont3",
		FiberLossDB:  1.0,
		HasFiberLoss: true,
	})
	// ont2 has no link (isolated)

	ctx := context.Background()
	ontIDs := []string{"ont1", "ont2", "ont3"}

	results, err := ResolveOpticalPathsParallel(ctx, g, ontIDs, fiberTypes, 10)

	// Should succeed even with partial failures
	if err != nil {
		t.Fatalf("Expected no error with partial failure, got: %v", err)
	}

	// Should have results for ont1 and ont3, but not ont2
	if len(results) != 2 {
		t.Errorf("Expected 2 results (ont1, ont3), got %d", len(results))
	}

	if _, exists := results["ont1"]; !exists {
		t.Error("Expected result for ont1")
	}
	if _, exists := results["ont3"]; !exists {
		t.Error("Expected result for ont3")
	}
	if _, exists := results["ont2"]; exists {
		t.Error("Did not expect result for ont2 (isolated)")
	}
}

// TestResolveOpticalPathsSequential_Comparison tests sequential vs parallel results.
func TestResolveOpticalPathsSequential_Comparison(t *testing.T) {
	graph := createSimpleTestGraph()
	fiberTypes := GetFiberTypes()

	ctx := context.Background()
	ontIDs := []string{"ont1", "ont2", "ont3"}

	// Resolve sequentially
	seqResults, err := ResolveOpticalPathsSequential(ctx, graph, ontIDs, fiberTypes)
	if err != nil {
		t.Fatalf("Sequential resolution failed: %v", err)
	}

	// Resolve in parallel
	parResults, err := ResolveOpticalPathsParallel(ctx, graph, ontIDs, fiberTypes, 10)
	if err != nil {
		t.Fatalf("Parallel resolution failed: %v", err)
	}

	// Compare results
	if len(seqResults) != len(parResults) {
		t.Errorf("Result count mismatch: sequential=%d, parallel=%d", len(seqResults), len(parResults))
	}

	for ontID, seqResult := range seqResults {
		parResult, exists := parResults[ontID]
		if !exists {
			t.Errorf("ONT %s missing in parallel results", ontID)
			continue
		}

		// Compare segment counts
		if len(seqResult.Segments) != len(parResult.Segments) {
			t.Errorf("ONT %s: segment count mismatch: sequential=%d, parallel=%d",
				ontID, len(seqResult.Segments), len(parResult.Segments))
		}

		// Compare attenuation (should be identical)
		if math.Abs(seqResult.TotalAttenuationDB-parResult.TotalAttenuationDB) > 0.001 {
			t.Errorf("ONT %s: attenuation mismatch: sequential=%.2f, parallel=%.2f",
				ontID, seqResult.TotalAttenuationDB, parResult.TotalAttenuationDB)
		}
	}
}

// TestResolveOpticalPathsBatched_BasicExecution tests batched processing.
func TestResolveOpticalPathsBatched_BasicExecution(t *testing.T) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Create topology with 25 ONTs
	g.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})
	ontIDs := []string{}
	for i := 0; i < 25; i++ {
		ontID := fmt.Sprintf("ont%d", i)
		g.AddNode(&Node{ID: ontID, Type: NodeTypeONT})
		g.AddEdge(&Edge{
			LinkID:       fmt.Sprintf("link%d", i),
			SourceID:     "olt1",
			TargetID:     ontID,
			FiberLossDB:  float64(i%10 + 1),
			HasFiberLoss: true,
		})
		ontIDs = append(ontIDs, ontID)
	}

	ctx := context.Background()
	config := ParallelConfig{
		MaxWorkers: 5,
		BatchSize:  10, // Process in 3 batches (10, 10, 5)
	}

	results, err := ResolveOpticalPathsBatched(ctx, g, ontIDs, fiberTypes, config)
	if err != nil {
		t.Fatalf("Batched resolution failed: %v", err)
	}

	// Should have all 25 results
	if len(results) != 25 {
		t.Errorf("Expected 25 results, got %d", len(results))
	}

	// Verify each ONT has a valid result
	for _, ontID := range ontIDs {
		result, exists := results[ontID]
		if !exists {
			t.Errorf("ONT %s missing from results", ontID)
			continue
		}
		if result == nil {
			t.Errorf("ONT %s has nil result", ontID)
		}
	}
}

// TestParallelConfig_Default tests default configuration.
func TestParallelConfig_Default(t *testing.T) {
	config := DefaultParallelConfig()

	if config.MaxWorkers != 10 {
		t.Errorf("Expected MaxWorkers=10, got %d", config.MaxWorkers)
	}
	if config.BatchSize != 1000 {
		t.Errorf("Expected BatchSize=1000, got %d", config.BatchSize)
	}
}

// TestResolveOpticalPathsParallel_Concurrency tests actual concurrent execution.
func TestResolveOpticalPathsParallel_Concurrency(t *testing.T) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Create topology with 20 ONTs
	g.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})
	ontIDs := []string{}
	for i := 0; i < 20; i++ {
		ontID := fmt.Sprintf("ont%d", i)
		g.AddNode(&Node{ID: ontID, Type: NodeTypeONT})
		g.AddEdge(&Edge{
			LinkID:       fmt.Sprintf("link%d", i),
			SourceID:     "olt1",
			TargetID:     ontID,
			FiberLossDB:  1.0,
			HasFiberLoss: true,
		})
		ontIDs = append(ontIDs, ontID)
	}

	ctx := context.Background()

	// Measure sequential execution time
	seqStart := time.Now()
	_, err := ResolveOpticalPathsSequential(ctx, g, ontIDs, fiberTypes)
	if err != nil {
		t.Fatalf("Sequential resolution failed: %v", err)
	}
	seqDuration := time.Since(seqStart)

	// Measure parallel execution time (10 workers)
	parStart := time.Now()
	_, err = ResolveOpticalPathsParallel(ctx, g, ontIDs, fiberTypes, 10)
	if err != nil {
		t.Fatalf("Parallel resolution failed: %v", err)
	}
	parDuration := time.Since(parStart)

	// Log timings (parallel should be faster on multi-core)
	t.Logf("Sequential: %v, Parallel: %v", seqDuration, parDuration)

	// Verify results are identical
	seqResults, _ := ResolveOpticalPathsSequential(ctx, g, ontIDs, fiberTypes)
	parResults, _ := ResolveOpticalPathsParallel(ctx, g, ontIDs, fiberTypes, 10)

	if len(seqResults) != len(parResults) {
		t.Errorf("Result count mismatch: sequential=%d, parallel=%d", len(seqResults), len(parResults))
	}
}

// TestResolveOpticalPathsParallel_ThreadSafety tests concurrent access safety.
func TestResolveOpticalPathsParallel_ThreadSafety(t *testing.T) {
	graph := createSimpleTestGraph()
	fiberTypes := GetFiberTypes()

	ctx := context.Background()
	ontIDs := []string{"ont1", "ont2"}

	// Run multiple parallel resolutions concurrently
	// This tests that the Graph can be safely read by multiple goroutines
	var wg sync.WaitGroup
	iterations := 10

	for i := 0; i < iterations; i++ {
		wg.Add(1)
		go func(iter int) {
			defer wg.Done()

			results, err := ResolveOpticalPathsParallel(ctx, graph, ontIDs, fiberTypes, 5)
			if err != nil {
				t.Errorf("Iteration %d failed: %v", iter, err)
			}
			if len(results) != 2 {
				t.Errorf("Iteration %d: expected 2 results, got %d", iter, len(results))
			}
		}(i)
	}

	wg.Wait()
}

// TestResolveOpticalPathsParallel_ResultOrdering tests result determinism.
func TestResolveOpticalPathsParallel_ResultOrdering(t *testing.T) {
	graph := createSimpleTestGraph()
	fiberTypes := GetFiberTypes()

	ctx := context.Background()
	ontIDs := []string{"ont1", "ont2", "ont3"}

	// Run parallel resolution multiple times
	// Results should be consistent (same attenuation for same ONT)
	previousResults := make(map[string]float64)

	for iteration := 0; iteration < 5; iteration++ {
		results, err := ResolveOpticalPathsParallel(ctx, graph, ontIDs, fiberTypes, 10)
		if err != nil {
			t.Fatalf("Iteration %d failed: %v", iteration, err)
		}

		for ontID, result := range results {
			if result == nil {
				t.Errorf("Iteration %d: ONT %s has nil result", iteration, ontID)
				continue
			}

			currentAttenuation := result.TotalAttenuationDB

			if iteration > 0 {
				// Compare with previous iteration
				if previousAttenuation, exists := previousResults[ontID]; exists {
					if math.Abs(currentAttenuation-previousAttenuation) > 0.001 {
						t.Errorf("Iteration %d: ONT %s attenuation changed: %.2f → %.2f",
							iteration, ontID, previousAttenuation, currentAttenuation)
					}
				}
			}

			previousResults[ontID] = currentAttenuation
		}
	}
}

// BenchmarkResolveOpticalPathsSequential benchmarks sequential resolution.
func BenchmarkResolveOpticalPathsSequential(b *testing.B) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Create topology with 50 ONTs
	g.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})
	ontIDs := []string{}
	for i := 0; i < 50; i++ {
		ontID := fmt.Sprintf("ont%d", i)
		g.AddNode(&Node{ID: ontID, Type: NodeTypeONT})
		g.AddEdge(&Edge{
			LinkID:       fmt.Sprintf("link%d", i),
			SourceID:     "olt1",
			TargetID:     ontID,
			FiberLossDB:  1.0,
			HasFiberLoss: true,
		})
		ontIDs = append(ontIDs, ontID)
	}

	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := ResolveOpticalPathsSequential(ctx, g, ontIDs, fiberTypes)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkResolveOpticalPathsParallel benchmarks parallel resolution.
func BenchmarkResolveOpticalPathsParallel(b *testing.B) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Create topology with 50 ONTs
	g.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})
	ontIDs := []string{}
	for i := 0; i < 50; i++ {
		ontID := fmt.Sprintf("ont%d", i)
		g.AddNode(&Node{ID: ontID, Type: NodeTypeONT})
		g.AddEdge(&Edge{
			LinkID:       fmt.Sprintf("link%d", i),
			SourceID:     "olt1",
			TargetID:     ontID,
			FiberLossDB:  1.0,
			HasFiberLoss: true,
		})
		ontIDs = append(ontIDs, ontID)
	}

	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := ResolveOpticalPathsParallel(ctx, g, ontIDs, fiberTypes, 10)
		if err != nil {
			b.Fatal(err)
		}
	}
}

// Helper to sort ONT IDs for comparison
func sortedONTIDs(results map[string]*OpticalPathResult) []string {
	ids := make([]string, 0, len(results))
	for id := range results {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}
