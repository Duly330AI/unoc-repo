// Package optical tests for path resolver implementation.
// Week 2 Day 6: Unit tests for resolver.go
package optical

import (
	"math"
	"testing"
)

// TestResolveOpticalPathSimple tests basic ONT to OLT path resolution.
func TestResolveOpticalPathSimple(t *testing.T) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Create simple topology: ONT -> SPLITTER -> OLT
	g.AddNode(&Node{ID: "ont1", Type: NodeTypeONT})
	g.AddNode(&Node{ID: "splitter1", Type: NodeTypeSplitter, InsertionLossDB: 3.5, HasInsertionLoss: true})
	g.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})

	g.AddEdge(&Edge{
		LinkID:       "link1",
		SourceID:     "ont1",
		TargetID:     "splitter1",
		FiberLossDB:  2.0,
		HasFiberLoss: true,
		LengthKm:     8.0,
		HasLengthKm:  true,
	})
	g.AddEdge(&Edge{
		LinkID:       "link2",
		SourceID:     "splitter1",
		TargetID:     "olt1",
		FiberLossDB:  1.5,
		HasFiberLoss: true,
		LengthKm:     6.0,
		HasLengthKm:  true,
	})

	result, err := ResolveOpticalPath(g, "ont1", fiberTypes)
	if err != nil {
		t.Fatalf("ResolveOpticalPath failed: %v", err)
	}
	if result == nil {
		t.Fatal("Expected path result, got nil")
	}

	// Check OLT ID
	if result.OLTID != "olt1" {
		t.Errorf("OLTID: got %s, want olt1", result.OLTID)
	}

	// Check total attenuation: 2.0 + 3.5 + 1.5 = 7.0
	expectedAtten := 7.0
	if math.Abs(result.TotalAttenuationDB-expectedAtten) > 0.001 {
		t.Errorf("TotalAttenuationDB: got %v, want %v", result.TotalAttenuationDB, expectedAtten)
	}

	// Check total length: 8.0 + 6.0 = 14.0
	expectedLength := 14.0
	if math.Abs(result.TotalLengthKm-expectedLength) > 0.001 {
		t.Errorf("TotalLengthKm: got %v, want %v", result.TotalLengthKm, expectedLength)
	}

	// Check hop count: 2 hops
	if result.HopCount != 2 {
		t.Errorf("HopCount: got %d, want 2", result.HopCount)
	}

	// Check segments
	if len(result.Segments) != 2 {
		t.Fatalf("Expected 2 segments, got %d", len(result.Segments))
	}
	seg0 := result.Segments[0]
	if seg0.Src != "ont1" || seg0.Dst != "splitter1" {
		t.Errorf("Segment 0: got %s->%s, want ont1->splitter1", seg0.Src, seg0.Dst)
	}
	if seg0.LinkID == nil || *seg0.LinkID != "link1" {
		t.Errorf("Segment 0 LinkID: got %v, want link1", seg0.LinkID)
	}

	seg1 := result.Segments[1]
	if seg1.Src != "splitter1" || seg1.Dst != "olt1" {
		t.Errorf("Segment 1: got %s->%s, want splitter1->olt1", seg1.Src, seg1.Dst)
	}
}

// TestResolveOpticalPathMultipleOLTs tests deterministic OLT selection.
func TestResolveOpticalPathMultipleOLTs(t *testing.T) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Topology: ONT can reach two OLTs with different costs
	//     OLT1 (expensive: 10.0 dB)
	//    /
	// ONT
	//    \
	//     OLT2 (cheap: 5.0 dB) <- Should be selected

	g.AddNode(&Node{ID: "ont1", Type: NodeTypeONT})
	g.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})
	g.AddNode(&Node{ID: "olt2", Type: NodeTypeOLT})

	// Expensive path to OLT1
	g.AddEdge(&Edge{
		LinkID:       "link1",
		SourceID:     "ont1",
		TargetID:     "olt1",
		FiberLossDB:  10.0,
		HasFiberLoss: true,
		LengthKm:     40.0,
		HasLengthKm:  true,
	})

	// Cheap path to OLT2
	g.AddEdge(&Edge{
		LinkID:       "link2",
		SourceID:     "ont1",
		TargetID:     "olt2",
		FiberLossDB:  5.0,
		HasFiberLoss: true,
		LengthKm:     20.0,
		HasLengthKm:  true,
	})

	result, err := ResolveOpticalPath(g, "ont1", fiberTypes)
	if err != nil {
		t.Fatalf("ResolveOpticalPath failed: %v", err)
	}
	if result == nil {
		t.Fatal("Expected path result, got nil")
	}

	// Should select OLT2 (cheaper path)
	if result.OLTID != "olt2" {
		t.Errorf("OLTID: got %s, want olt2 (cheaper path)", result.OLTID)
	}
	if math.Abs(result.TotalAttenuationDB-5.0) > 0.001 {
		t.Errorf("TotalAttenuationDB: got %v, want 5.0", result.TotalAttenuationDB)
	}
}

// TestResolveOpticalPathNoOLT tests that nil is returned when no OLT is reachable.
func TestResolveOpticalPathNoOLT(t *testing.T) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Create ONT with no path to OLT (only connected to another ONT)
	g.AddNode(&Node{ID: "ont1", Type: NodeTypeONT})
	g.AddNode(&Node{ID: "ont2", Type: NodeTypeONT})

	g.AddEdge(&Edge{
		LinkID:       "link1",
		SourceID:     "ont1",
		TargetID:     "ont2",
		FiberLossDB:  1.0,
		HasFiberLoss: true,
	})

	result, err := ResolveOpticalPath(g, "ont1", fiberTypes)
	if err != nil {
		t.Fatalf("ResolveOpticalPath failed: %v", err)
	}
	if result != nil {
		t.Errorf("Expected nil result (no OLT reachable), got %v", result)
	}
}

// TestResolveOpticalPathDeterministicOrdering tests tie-breaking logic.
func TestResolveOpticalPathDeterministicOrdering(t *testing.T) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Create two OLTs with IDENTICAL attenuation (5.0 dB each)
	// But different lengths and IDs for deterministic ordering
	g.AddNode(&Node{ID: "ont1", Type: NodeTypeONT})
	g.AddNode(&Node{ID: "olt_alpha", Type: NodeTypeOLT})
	g.AddNode(&Node{ID: "olt_beta", Type: NodeTypeOLT})

	// Path to olt_alpha: 5.0 dB, 30 km
	g.AddEdge(&Edge{
		LinkID:       "link1",
		SourceID:     "ont1",
		TargetID:     "olt_alpha",
		FiberLossDB:  5.0,
		HasFiberLoss: true,
		LengthKm:     30.0,
		HasLengthKm:  true,
	})

	// Path to olt_beta: 5.0 dB, 20 km (shorter - should win)
	g.AddEdge(&Edge{
		LinkID:       "link2",
		SourceID:     "ont1",
		TargetID:     "olt_beta",
		FiberLossDB:  5.0,
		HasFiberLoss: true,
		LengthKm:     20.0,
		HasLengthKm:  true,
	})

	result, err := ResolveOpticalPath(g, "ont1", fiberTypes)
	if err != nil {
		t.Fatalf("ResolveOpticalPath failed: %v", err)
	}
	if result == nil {
		t.Fatal("Expected path result, got nil")
	}

	// Should select olt_beta (shorter length, same attenuation)
	if result.OLTID != "olt_beta" {
		t.Errorf("OLTID: got %s, want olt_beta (shorter length)", result.OLTID)
	}
}

// TestResolveOpticalPathComplexTopology tests multi-hop path with passive devices.
func TestResolveOpticalPathComplexTopology(t *testing.T) {
	g := NewGraph()
	fiberTypes := GetFiberTypes()

	// Complex topology: ONT -> ODF -> SPLITTER -> NVT -> OLT
	g.AddNode(&Node{ID: "ont1", Type: NodeTypeONT})
	g.AddNode(&Node{ID: "odf1", Type: NodeTypeODF, InsertionLossDB: 0.5, HasInsertionLoss: true})
	g.AddNode(&Node{ID: "splitter1", Type: NodeTypeSplitter, InsertionLossDB: 3.5, HasInsertionLoss: true})
	g.AddNode(&Node{ID: "nvt1", Type: NodeTypeNVT, InsertionLossDB: 1.0, HasInsertionLoss: true})
	g.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})

	g.AddEdge(&Edge{LinkID: "link1", SourceID: "ont1", TargetID: "odf1", FiberLossDB: 1.0, HasFiberLoss: true, LengthKm: 4.0, HasLengthKm: true})
	g.AddEdge(&Edge{LinkID: "link2", SourceID: "odf1", TargetID: "splitter1", FiberLossDB: 2.0, HasFiberLoss: true, LengthKm: 8.0, HasLengthKm: true})
	g.AddEdge(&Edge{LinkID: "link3", SourceID: "splitter1", TargetID: "nvt1", FiberLossDB: 1.5, HasFiberLoss: true, LengthKm: 6.0, HasLengthKm: true})
	g.AddEdge(&Edge{LinkID: "link4", SourceID: "nvt1", TargetID: "olt1", FiberLossDB: 1.0, HasFiberLoss: true, LengthKm: 4.0, HasLengthKm: true})

	result, err := ResolveOpticalPath(g, "ont1", fiberTypes)
	if err != nil {
		t.Fatalf("ResolveOpticalPath failed: %v", err)
	}
	if result == nil {
		t.Fatal("Expected path result, got nil")
	}

	// Calculate expected attenuation:
	// ont1 -> odf1: 1.0 + 0.5 = 1.5
	// odf1 -> splitter1: 2.0 + 3.5 = 5.5
	// splitter1 -> nvt1: 1.5 + 1.0 = 2.5
	// nvt1 -> olt1: 1.0 + 0.0 = 1.0 (OLT not passive)
	// Total: 1.5 + 5.5 + 2.5 + 1.0 = 10.5
	expectedAtten := 10.5
	if math.Abs(result.TotalAttenuationDB-expectedAtten) > 0.001 {
		t.Errorf("TotalAttenuationDB: got %v, want %v", result.TotalAttenuationDB, expectedAtten)
	}

	// Check total length: 4 + 8 + 6 + 4 = 22 km
	expectedLength := 22.0
	if math.Abs(result.TotalLengthKm-expectedLength) > 0.001 {
		t.Errorf("TotalLengthKm: got %v, want %v", result.TotalLengthKm, expectedLength)
	}

	// Check hop count: 4 hops
	if result.HopCount != 4 {
		t.Errorf("HopCount: got %d, want 4", result.HopCount)
	}

	// Check that all segments are present
	if len(result.Segments) != 4 {
		t.Fatalf("Expected 4 segments, got %d", len(result.Segments))
	}
}

// TestBuildGraphBuilder tests graph construction from records.
func TestBuildGraphBuilder(t *testing.T) {
	fiberTypes := GetFiberTypes()

	devices := []DeviceRecord{
		{ID: "ont1", Type: "ONT", InsertionLossDB: nil},
		{ID: "splitter1", Type: "SPLITTER", InsertionLossDB: floatPtr(3.5)},
		{ID: "olt1", Type: "OLT", InsertionLossDB: nil},
		{ID: "router1", Type: "EDGE_ROUTER", InsertionLossDB: nil}, // Non-optical, should be filtered
	}

	links := []LinkRecord{
		{
			ID:             "link1",
			ADeviceID:      "ont1",
			BDeviceID:      "splitter1",
			Kind:           "FIBER",
			LengthKm:       floatPtr(8.0),
			PhysicalMedium: stringPtr("SM_G652D"),
		},
		{
			ID:             "link2",
			ADeviceID:      "splitter1",
			BDeviceID:      "olt1",
			Kind:           "FIBER",
			LengthKm:       floatPtr(6.0),
			PhysicalMedium: stringPtr("SM_G652D"),
		},
		{
			ID:        "link3",
			ADeviceID: "router1",
			BDeviceID: "olt1",
			Kind:      "P2P", // Non-optical link, should be filtered
		},
	}

	g, err := BuildOpticalGraph(devices, links, fiberTypes)
	if err != nil {
		t.Fatalf("BuildOpticalGraph failed: %v", err)
	}

	// Check nodes (should have 3 optical nodes, not the router)
	if len(g.Nodes) != 3 {
		t.Errorf("Expected 3 nodes, got %d", len(g.Nodes))
	}
	if _, ok := g.Nodes["ont1"]; !ok {
		t.Error("ont1 should be in graph")
	}
	if _, ok := g.Nodes["splitter1"]; !ok {
		t.Error("splitter1 should be in graph")
	}
	if _, ok := g.Nodes["olt1"]; !ok {
		t.Error("olt1 should be in graph")
	}
	if _, ok := g.Nodes["router1"]; ok {
		t.Error("router1 (non-optical) should NOT be in graph")
	}

	// Check edges (should have 2 fiber links)
	edgeCount := 0
	for _, targets := range g.Edges {
		edgeCount += len(targets)
	}
	// Each edge is stored bidirectionally, so 2 links = 4 directed edges
	if edgeCount != 4 {
		t.Errorf("Expected 4 directed edges (2 bidirectional), got %d", edgeCount)
	}

	// Check that fiber loss was calculated
	edge, ok := g.GetEdge("ont1", "splitter1")
	if !ok {
		t.Fatal("Edge ont1->splitter1 should exist")
	}
	if !edge.HasFiberLoss {
		t.Error("Edge should have fiber loss")
	}
	// 8.0 km * 0.25 dB/km = 2.0 dB
	expectedLoss := 2.0
	if math.Abs(edge.FiberLossDB-expectedLoss) > 0.001 {
		t.Errorf("Fiber loss: got %v, want %v", edge.FiberLossDB, expectedLoss)
	}
}

// TestValidateGraph tests graph validation.
func TestValidateGraph(t *testing.T) {
	// Test 1: Valid graph with OLT
	g1 := NewGraph()
	g1.AddNode(&Node{ID: "olt1", Type: NodeTypeOLT})
	g1.AddNode(&Node{ID: "ont1", Type: NodeTypeONT})
	g1.AddEdge(&Edge{LinkID: "link1", SourceID: "olt1", TargetID: "ont1", FiberLossDB: 1.0, HasFiberLoss: true})

	if err := ValidateGraph(g1); err != nil {
		t.Errorf("Valid graph failed validation: %v", err)
	}

	// Test 2: Invalid graph (no OLT)
	g2 := NewGraph()
	g2.AddNode(&Node{ID: "ont1", Type: NodeTypeONT})
	g2.AddNode(&Node{ID: "ont2", Type: NodeTypeONT})

	if err := ValidateGraph(g2); err == nil {
		t.Error("Graph without OLT should fail validation")
	}
}

// Helper functions
func floatPtr(f float64) *float64 {
	return &f
}

func stringPtr(s string) *string {
	return &s
}
