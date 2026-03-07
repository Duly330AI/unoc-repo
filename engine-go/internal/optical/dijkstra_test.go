// Package optical tests for Dijkstra's algorithm implementation.
// Week 2 Day 6: Unit tests for dijkstra.go
package optical

import (
	"math"
	"testing"
)

// TestDijkstraSimplePath tests Dijkstra on a simple linear path.
func TestDijkstraSimplePath(t *testing.T) {
	g := NewGraph()

	// Create nodes: A -> B -> C
	g.AddNode(&Node{ID: "A", Type: NodeTypeOLT})
	g.AddNode(&Node{ID: "B", Type: NodeTypeSplitter, InsertionLossDB: 1.0, HasInsertionLoss: true})
	g.AddNode(&Node{ID: "C", Type: NodeTypeONT})

	// Create edges
	g.AddEdge(&Edge{
		LinkID:       "link1",
		SourceID:     "A",
		TargetID:     "B",
		FiberLossDB:  2.0,
		HasFiberLoss: true,
	})
	g.AddEdge(&Edge{
		LinkID:       "link2",
		SourceID:     "B",
		TargetID:     "C",
		FiberLossDB:  3.0,
		HasFiberLoss: true,
	})

	// Run Dijkstra from A
	fiberTypes := GetFiberTypes()
	weightFn := func(g *Graph, src, tgt string) float64 {
		return computeEdgeWeight(g, src, tgt, fiberTypes)
	}

	result, err := dijkstra(g, "A", weightFn)
	if err != nil {
		t.Fatalf("dijkstra failed: %v", err)
	}

	// Check distances
	// A -> B: 2.0 (fiber) + 1.0 (insertion) = 3.0
	// A -> C: 3.0 + 3.0 (fiber) = 6.0
	if dist, ok := result.Distances["A"]; !ok || dist != 0.0 {
		t.Errorf("Distance to A: got %v, want 0.0", dist)
	}
	if dist, ok := result.Distances["B"]; !ok || math.Abs(dist-3.0) > 0.001 {
		t.Errorf("Distance to B: got %v, want 3.0", dist)
	}
	if dist, ok := result.Distances["C"]; !ok || math.Abs(dist-6.0) > 0.001 {
		t.Errorf("Distance to C: got %v, want 6.0", dist)
	}

	// Check paths
	if len(result.Paths["A"]) != 1 || result.Paths["A"][0] != "A" {
		t.Errorf("Path to A: got %v, want [A]", result.Paths["A"])
	}
	if len(result.Paths["B"]) != 2 || result.Paths["B"][0] != "A" || result.Paths["B"][1] != "B" {
		t.Errorf("Path to B: got %v, want [A B]", result.Paths["B"])
	}
	if len(result.Paths["C"]) != 3 || result.Paths["C"][0] != "A" || result.Paths["C"][1] != "B" || result.Paths["C"][2] != "C" {
		t.Errorf("Path to C: got %v, want [A B C]", result.Paths["C"])
	}
}

// TestDijkstraMultiplePaths tests that Dijkstra chooses the lowest-cost path.
func TestDijkstraMultiplePaths(t *testing.T) {
	g := NewGraph()

	// Create diamond topology:
	//     A
	//    / \
	//   B   C
	//    \ /
	//     D
	// Path A->B->D: 1.0 + 1.0 = 2.0 (cheaper)
	// Path A->C->D: 5.0 + 5.0 = 10.0 (expensive)

	g.AddNode(&Node{ID: "A", Type: NodeTypeOLT})
	g.AddNode(&Node{ID: "B", Type: NodeTypeSplitter, InsertionLossDB: 0.5, HasInsertionLoss: true})
	g.AddNode(&Node{ID: "C", Type: NodeTypeSplitter, InsertionLossDB: 0.5, HasInsertionLoss: true})
	g.AddNode(&Node{ID: "D", Type: NodeTypeONT})

	// Cheap path: A -> B -> D
	g.AddEdge(&Edge{LinkID: "link1", SourceID: "A", TargetID: "B", FiberLossDB: 1.0, HasFiberLoss: true})
	g.AddEdge(&Edge{LinkID: "link2", SourceID: "B", TargetID: "D", FiberLossDB: 1.0, HasFiberLoss: true})

	// Expensive path: A -> C -> D
	g.AddEdge(&Edge{LinkID: "link3", SourceID: "A", TargetID: "C", FiberLossDB: 5.0, HasFiberLoss: true})
	g.AddEdge(&Edge{LinkID: "link4", SourceID: "C", TargetID: "D", FiberLossDB: 5.0, HasFiberLoss: true})

	fiberTypes := GetFiberTypes()
	weightFn := func(g *Graph, src, tgt string) float64 {
		return computeEdgeWeight(g, src, tgt, fiberTypes)
	}

	result, err := dijkstra(g, "A", weightFn)
	if err != nil {
		t.Fatalf("dijkstra failed: %v", err)
	}

	// Distance to D should use cheap path: 1.0 + 0.5 (insertion at B) + 1.0 = 2.5
	expectedDist := 2.5
	if dist, ok := result.Distances["D"]; !ok || math.Abs(dist-expectedDist) > 0.001 {
		t.Errorf("Distance to D: got %v, want %v", dist, expectedDist)
	}

	// Path should be A -> B -> D
	path := result.Paths["D"]
	if len(path) != 3 || path[0] != "A" || path[1] != "B" || path[2] != "D" {
		t.Errorf("Path to D: got %v, want [A B D]", path)
	}
}

// TestDijkstraNoPath tests that Dijkstra handles unreachable nodes correctly.
func TestDijkstraNoPath(t *testing.T) {
	g := NewGraph()

	// Create two disconnected components: A-B and C-D
	g.AddNode(&Node{ID: "A", Type: NodeTypeOLT})
	g.AddNode(&Node{ID: "B", Type: NodeTypeONT})
	g.AddNode(&Node{ID: "C", Type: NodeTypeOLT})
	g.AddNode(&Node{ID: "D", Type: NodeTypeONT})

	g.AddEdge(&Edge{LinkID: "link1", SourceID: "A", TargetID: "B", FiberLossDB: 1.0, HasFiberLoss: true})
	g.AddEdge(&Edge{LinkID: "link2", SourceID: "C", TargetID: "D", FiberLossDB: 1.0, HasFiberLoss: true})

	fiberTypes := GetFiberTypes()
	weightFn := func(g *Graph, src, tgt string) float64 {
		return computeEdgeWeight(g, src, tgt, fiberTypes)
	}

	result, err := dijkstra(g, "A", weightFn)
	if err != nil {
		t.Fatalf("dijkstra failed: %v", err)
	}

	// A and B should be reachable
	if _, ok := result.Distances["A"]; !ok {
		t.Errorf("A should be reachable")
	}
	if _, ok := result.Distances["B"]; !ok {
		t.Errorf("B should be reachable")
	}

	// C and D should NOT be reachable (different component)
	if _, ok := result.Distances["C"]; ok {
		t.Errorf("C should NOT be reachable from A")
	}
	if _, ok := result.Distances["D"]; ok {
		t.Errorf("D should NOT be reachable from A")
	}
}

// TestDijkstraIsolatedNode tests that Dijkstra handles an isolated source node.
func TestDijkstraIsolatedNode(t *testing.T) {
	g := NewGraph()

	// Create isolated node with no edges
	g.AddNode(&Node{ID: "ISOLATED", Type: NodeTypeONT})
	g.AddNode(&Node{ID: "OTHER", Type: NodeTypeOLT})

	fiberTypes := GetFiberTypes()
	weightFn := func(g *Graph, src, tgt string) float64 {
		return computeEdgeWeight(g, src, tgt, fiberTypes)
	}

	result, err := dijkstra(g, "ISOLATED", weightFn)
	if err != nil {
		t.Fatalf("dijkstra failed: %v", err)
	}

	// Only ISOLATED should be reachable (itself)
	if len(result.Distances) != 1 {
		t.Errorf("Expected 1 reachable node, got %d", len(result.Distances))
	}
	if dist, ok := result.Distances["ISOLATED"]; !ok || dist != 0.0 {
		t.Errorf("Distance to ISOLATED: got %v, want 0.0", dist)
	}
	if _, ok := result.Distances["OTHER"]; ok {
		t.Errorf("OTHER should NOT be reachable from ISOLATED")
	}
}

// TestDijkstraPassiveInsertionLoss tests that passive insertion loss is correctly added.
func TestDijkstraPassiveInsertionLoss(t *testing.T) {
	g := NewGraph()

	// Path: ONT -> Splitter1 -> Splitter2 -> OLT
	// Each splitter has insertion loss
	g.AddNode(&Node{ID: "ONT", Type: NodeTypeONT})
	g.AddNode(&Node{ID: "SPLITTER1", Type: NodeTypeSplitter, InsertionLossDB: 3.5, HasInsertionLoss: true})
	g.AddNode(&Node{ID: "SPLITTER2", Type: NodeTypeSplitter, InsertionLossDB: 2.0, HasInsertionLoss: true})
	g.AddNode(&Node{ID: "OLT", Type: NodeTypeOLT})

	g.AddEdge(&Edge{LinkID: "link1", SourceID: "ONT", TargetID: "SPLITTER1", FiberLossDB: 1.0, HasFiberLoss: true})
	g.AddEdge(&Edge{LinkID: "link2", SourceID: "SPLITTER1", TargetID: "SPLITTER2", FiberLossDB: 2.0, HasFiberLoss: true})
	g.AddEdge(&Edge{LinkID: "link3", SourceID: "SPLITTER2", TargetID: "OLT", FiberLossDB: 1.5, HasFiberLoss: true})

	fiberTypes := GetFiberTypes()
	weightFn := func(g *Graph, src, tgt string) float64 {
		return computeEdgeWeight(g, src, tgt, fiberTypes)
	}

	result, err := dijkstra(g, "ONT", weightFn)
	if err != nil {
		t.Fatalf("dijkstra failed: %v", err)
	}

	// Distance to OLT:
	// ONT -> SPLITTER1: 1.0 (fiber) + 3.5 (insertion) = 4.5
	// SPLITTER1 -> SPLITTER2: 2.0 (fiber) + 2.0 (insertion) = 4.0
	// SPLITTER2 -> OLT: 1.5 (fiber) + 0.0 (OLT not passive) = 1.5
	// Total: 4.5 + 4.0 + 1.5 = 10.0
	expectedDist := 10.0
	if dist, ok := result.Distances["OLT"]; !ok || math.Abs(dist-expectedDist) > 0.001 {
		t.Errorf("Distance to OLT: got %v, want %v", dist, expectedDist)
	}
}

// TestComputeEdgeWeight tests the edge weight computation function directly.
func TestComputeEdgeWeight(t *testing.T) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Test 1: Fiber loss only (no passive insertion)
	g.AddNode(&Node{ID: "A", Type: NodeTypeOLT})
	g.AddNode(&Node{ID: "B", Type: NodeTypeONT})
	g.AddEdge(&Edge{
		LinkID:       "link1",
		SourceID:     "A",
		TargetID:     "B",
		FiberLossDB:  5.5,
		HasFiberLoss: true,
	})

	weight := computeEdgeWeight(g, "A", "B", fiberTypes)
	if math.Abs(weight-5.5) > 0.001 {
		t.Errorf("Weight A->B: got %v, want 5.5", weight)
	}

	// Test 2: Fiber loss + passive insertion
	g.AddNode(&Node{ID: "C", Type: NodeTypeSplitter, InsertionLossDB: 2.5, HasInsertionLoss: true})
	g.AddEdge(&Edge{
		LinkID:       "link2",
		SourceID:     "B",
		TargetID:     "C",
		FiberLossDB:  3.0,
		HasFiberLoss: true,
	})

	weight = computeEdgeWeight(g, "B", "C", fiberTypes)
	expectedWeight := 5.5 // 3.0 (fiber) + 2.5 (insertion)
	if math.Abs(weight-expectedWeight) > 0.001 {
		t.Errorf("Weight B->C: got %v, want %v", weight, expectedWeight)
	}

	// Test 3: No fiber loss (missing edge data)
	g.AddNode(&Node{ID: "D", Type: NodeTypeODF, InsertionLossDB: 1.0, HasInsertionLoss: true})
	g.AddEdge(&Edge{
		LinkID:       "link3",
		SourceID:     "C",
		TargetID:     "D",
		HasFiberLoss: false, // No fiber loss data
	})

	weight = computeEdgeWeight(g, "C", "D", fiberTypes)
	expectedWeight = 1.0 // 0.0 (fiber) + 1.0 (insertion)
	if math.Abs(weight-expectedWeight) > 0.001 {
		t.Errorf("Weight C->D: got %v, want %v", weight, expectedWeight)
	}
}
