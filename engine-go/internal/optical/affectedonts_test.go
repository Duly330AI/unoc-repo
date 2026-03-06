// Package optical provides optical path computation for ONT signal budget analysis.
// This file contains tests for affected ONT detection (affectedonts.go).
//
// Week 2 Day 7: Smart ONT Detection Tests
package optical

import (
	"testing"
)

// TestFindAffectedONTs_SingleLink tests finding affected ONTs from a single changed link.
// Topology: OLT → SPLITTER → 3 ONTs
// Changed Link: OLT-SPLITTER link
// Expected: All 3 ONTs affected
func TestFindAffectedONTs_SingleLink(t *testing.T) {
	// Build test graph
	g := &Graph{
		Nodes: map[string]*Node{
			"olt1": {ID: "olt1", Type: NodeTypeOLT},
			"sp1":  {ID: "sp1", Type: NodeTypeSplitter, InsertionLossDB: 3.5, HasInsertionLoss: true},
			"ont1": {ID: "ont1", Type: NodeTypeONT},
			"ont2": {ID: "ont2", Type: NodeTypeONT},
			"ont3": {ID: "ont3", Type: NodeTypeONT},
		},
		Edges: map[string]map[string]*Edge{
			"olt1": {
				"sp1": {LinkID: "link1", SourceID: "olt1", TargetID: "sp1", FiberLossDB: 5.0},
			},
			"sp1": {
				"olt1": {LinkID: "link1", SourceID: "sp1", TargetID: "olt1", FiberLossDB: 5.0},
				"ont1": {LinkID: "link2", SourceID: "sp1", TargetID: "ont1", FiberLossDB: 2.0},
				"ont2": {LinkID: "link3", SourceID: "sp1", TargetID: "ont2", FiberLossDB: 2.5},
				"ont3": {LinkID: "link4", SourceID: "sp1", TargetID: "ont3", FiberLossDB: 3.0},
			},
			"ont1": {
				"sp1": {LinkID: "link2", SourceID: "ont1", TargetID: "sp1", FiberLossDB: 2.0},
			},
			"ont2": {
				"sp1": {LinkID: "link3", SourceID: "ont2", TargetID: "sp1", FiberLossDB: 2.5},
			},
			"ont3": {
				"sp1": {LinkID: "link4", SourceID: "ont3", TargetID: "sp1", FiberLossDB: 3.0},
			},
		},
	}

	// Changed link: OLT-SPLITTER (link1)
	affectedONTs, err := FindAffectedONTs(g, []string{"link1"})
	if err != nil {
		t.Fatalf("FindAffectedONTs failed: %v", err)
	}

	// Should find all 3 ONTs
	if len(affectedONTs) != 3 {
		t.Errorf("Expected 3 affected ONTs, got %d: %v", len(affectedONTs), affectedONTs)
	}

	// Check ONT IDs (sorted)
	expected := []string{"ont1", "ont2", "ont3"}
	for i, ontID := range expected {
		if i >= len(affectedONTs) || affectedONTs[i] != ontID {
			t.Errorf("Expected ONT[%d]=%s, got %v", i, ontID, affectedONTs)
		}
	}
}

// TestFindAffectedONTs_EdgeLink tests a change to an edge link (close to ONT).
// Topology: OLT → SPLITTER → ONT1, ONT2, ONT3
// Changed Link: SPLITTER-ONT1 link (edge link)
// Expected: All 3 ONTs affected (BFS traverses bidirectionally through splitter to other ONTs)
// Note: In optical networks, fiber is bidirectional, so changing any link in a splitter
// potentially affects all ONTs connected to that splitter.
func TestFindAffectedONTs_EdgeLink(t *testing.T) {
	// Build test graph (same as above)
	g := &Graph{
		Nodes: map[string]*Node{
			"olt1": {ID: "olt1", Type: NodeTypeOLT},
			"sp1":  {ID: "sp1", Type: NodeTypeSplitter, InsertionLossDB: 3.5, HasInsertionLoss: true},
			"ont1": {ID: "ont1", Type: NodeTypeONT},
			"ont2": {ID: "ont2", Type: NodeTypeONT},
			"ont3": {ID: "ont3", Type: NodeTypeONT},
		},
		Edges: map[string]map[string]*Edge{
			"olt1": {
				"sp1": {LinkID: "link1", SourceID: "olt1", TargetID: "sp1", FiberLossDB: 5.0},
			},
			"sp1": {
				"olt1": {LinkID: "link1", SourceID: "sp1", TargetID: "olt1", FiberLossDB: 5.0},
				"ont1": {LinkID: "link2", SourceID: "sp1", TargetID: "ont1", FiberLossDB: 2.0},
				"ont2": {LinkID: "link3", SourceID: "sp1", TargetID: "ont2", FiberLossDB: 2.5},
				"ont3": {LinkID: "link4", SourceID: "sp1", TargetID: "ont3", FiberLossDB: 3.0},
			},
			"ont1": {
				"sp1": {LinkID: "link2", SourceID: "ont1", TargetID: "sp1", FiberLossDB: 2.0},
			},
			"ont2": {
				"sp1": {LinkID: "link3", SourceID: "ont2", TargetID: "sp1", FiberLossDB: 2.5},
			},
			"ont3": {
				"sp1": {LinkID: "link4", SourceID: "ont3", TargetID: "sp1", FiberLossDB: 3.0},
			},
		},
	}

	// Changed link: SPLITTER-ONT1 (link2) - edge link
	// BFS from link2 endpoints (sp1, ont1) will traverse through sp1 to reach all other ONTs
	affectedONTs, err := FindAffectedONTs(g, []string{"link2"})
	if err != nil {
		t.Fatalf("FindAffectedONTs failed: %v", err)
	}

	// Should find all 3 ONTs (bidirectional traversal through splitter)
	if len(affectedONTs) != 3 {
		t.Errorf("Expected 3 affected ONTs, got %d: %v", len(affectedONTs), affectedONTs)
	}

	// Check ONT IDs (sorted)
	expected := []string{"ont1", "ont2", "ont3"}
	for i, ontID := range expected {
		if i >= len(affectedONTs) || affectedONTs[i] != ontID {
			t.Errorf("Expected ONT[%d]=%s, got %v", i, ontID, affectedONTs)
		}
	}
}

// TestFindAffectedONTs_IsolatedChange tests a change to a link not in the optical graph.
// Changed Link: Non-existent link ID
// Expected: No ONTs affected (empty result, not error)
func TestFindAffectedONTs_IsolatedChange(t *testing.T) {
	// Build simple graph
	g := &Graph{
		Nodes: map[string]*Node{
			"olt1": {ID: "olt1", Type: NodeTypeOLT},
			"ont1": {ID: "ont1", Type: NodeTypeONT},
		},
		Edges: map[string]map[string]*Edge{
			"olt1": {
				"ont1": {LinkID: "link1", SourceID: "olt1", TargetID: "ont1", FiberLossDB: 5.0},
			},
			"ont1": {
				"olt1": {LinkID: "link1", SourceID: "ont1", TargetID: "olt1", FiberLossDB: 5.0},
			},
		},
	}

	// Changed link: Non-existent link (e.g., P2P management link not in optical graph)
	affectedONTs, err := FindAffectedONTs(g, []string{"nonexistent_link"})
	if err != nil {
		t.Fatalf("FindAffectedONTs should not error on non-existent link: %v", err)
	}

	// Should return empty list (not an error)
	if len(affectedONTs) != 0 {
		t.Errorf("Expected 0 affected ONTs for isolated change, got %d: %v", len(affectedONTs), affectedONTs)
	}
}

// TestFindAffectedONTs_ComplexTopology tests a complex topology with multiple OLTs and splitters.
// Topology: OLT1 → SP1 → 2 ONTs, OLT2 → SP2 → 3 ONTs (separate networks)
// Changed Link: OLT1-SP1 link
// Expected: Only 2 ONTs connected to OLT1 (not all 5 ONTs)
func TestFindAffectedONTs_ComplexTopology(t *testing.T) {
	// Build complex graph with 2 separate OLT networks
	g := &Graph{
		Nodes: map[string]*Node{
			"olt1": {ID: "olt1", Type: NodeTypeOLT},
			"olt2": {ID: "olt2", Type: NodeTypeOLT},
			"sp1":  {ID: "sp1", Type: NodeTypeSplitter, InsertionLossDB: 3.5, HasInsertionLoss: true},
			"sp2":  {ID: "sp2", Type: NodeTypeSplitter, InsertionLossDB: 3.5, HasInsertionLoss: true},
			"ont1": {ID: "ont1", Type: NodeTypeONT}, // Connected to OLT1
			"ont2": {ID: "ont2", Type: NodeTypeONT}, // Connected to OLT1
			"ont3": {ID: "ont3", Type: NodeTypeONT}, // Connected to OLT2
			"ont4": {ID: "ont4", Type: NodeTypeONT}, // Connected to OLT2
			"ont5": {ID: "ont5", Type: NodeTypeONT}, // Connected to OLT2
		},
		Edges: map[string]map[string]*Edge{
			// OLT1 network
			"olt1": {
				"sp1": {LinkID: "link1", SourceID: "olt1", TargetID: "sp1", FiberLossDB: 5.0},
			},
			"sp1": {
				"olt1": {LinkID: "link1", SourceID: "sp1", TargetID: "olt1", FiberLossDB: 5.0},
				"ont1": {LinkID: "link2", SourceID: "sp1", TargetID: "ont1", FiberLossDB: 2.0},
				"ont2": {LinkID: "link3", SourceID: "sp1", TargetID: "ont2", FiberLossDB: 2.5},
			},
			"ont1": {
				"sp1": {LinkID: "link2", SourceID: "ont1", TargetID: "sp1", FiberLossDB: 2.0},
			},
			"ont2": {
				"sp1": {LinkID: "link3", SourceID: "ont2", TargetID: "sp1", FiberLossDB: 2.5},
			},
			// OLT2 network
			"olt2": {
				"sp2": {LinkID: "link10", SourceID: "olt2", TargetID: "sp2", FiberLossDB: 5.0},
			},
			"sp2": {
				"olt2": {LinkID: "link10", SourceID: "sp2", TargetID: "olt2", FiberLossDB: 5.0},
				"ont3": {LinkID: "link11", SourceID: "sp2", TargetID: "ont3", FiberLossDB: 2.0},
				"ont4": {LinkID: "link12", SourceID: "sp2", TargetID: "ont4", FiberLossDB: 2.5},
				"ont5": {LinkID: "link13", SourceID: "sp2", TargetID: "ont5", FiberLossDB: 3.0},
			},
			"ont3": {
				"sp2": {LinkID: "link11", SourceID: "ont3", TargetID: "sp2", FiberLossDB: 2.0},
			},
			"ont4": {
				"sp2": {LinkID: "link12", SourceID: "ont4", TargetID: "sp2", FiberLossDB: 2.5},
			},
			"ont5": {
				"sp2": {LinkID: "link13", SourceID: "ont5", TargetID: "sp2", FiberLossDB: 3.0},
			},
		},
	}

	// Changed link: OLT1-SP1 (link1) - should only affect OLT1's ONTs
	affectedONTs, err := FindAffectedONTs(g, []string{"link1"})
	if err != nil {
		t.Fatalf("FindAffectedONTs failed: %v", err)
	}

	// Should find only 2 ONTs (ont1, ont2) - not ont3, ont4, ont5
	if len(affectedONTs) != 2 {
		t.Errorf("Expected 2 affected ONTs, got %d: %v", len(affectedONTs), affectedONTs)
	}

	// Check ONT IDs (sorted)
	expected := []string{"ont1", "ont2"}
	for i, ontID := range expected {
		if i >= len(affectedONTs) || affectedONTs[i] != ontID {
			t.Errorf("Expected ONT[%d]=%s, got %v", i, ontID, affectedONTs)
		}
	}
}

// TestFindAffectedONTsByDevices_OLTChange tests finding affected ONTs when OLT changes.
// Changed Device: OLT1 (e.g., tx_power changed)
// Expected: All ONTs connected to OLT1
func TestFindAffectedONTsByDevices_OLTChange(t *testing.T) {
	// Build test graph (same as complex topology)
	g := &Graph{
		Nodes: map[string]*Node{
			"olt1": {ID: "olt1", Type: NodeTypeOLT},
			"sp1":  {ID: "sp1", Type: NodeTypeSplitter, InsertionLossDB: 3.5, HasInsertionLoss: true},
			"ont1": {ID: "ont1", Type: NodeTypeONT},
			"ont2": {ID: "ont2", Type: NodeTypeONT},
		},
		Edges: map[string]map[string]*Edge{
			"olt1": {
				"sp1": {LinkID: "link1", SourceID: "olt1", TargetID: "sp1", FiberLossDB: 5.0},
			},
			"sp1": {
				"olt1": {LinkID: "link1", SourceID: "sp1", TargetID: "olt1", FiberLossDB: 5.0},
				"ont1": {LinkID: "link2", SourceID: "sp1", TargetID: "ont1", FiberLossDB: 2.0},
				"ont2": {LinkID: "link3", SourceID: "sp1", TargetID: "ont2", FiberLossDB: 2.5},
			},
			"ont1": {
				"sp1": {LinkID: "link2", SourceID: "ont1", TargetID: "sp1", FiberLossDB: 2.0},
			},
			"ont2": {
				"sp1": {LinkID: "link3", SourceID: "ont2", TargetID: "sp1", FiberLossDB: 2.5},
			},
		},
	}

	// Changed device: OLT1 (e.g., tx_power_dbm changed)
	affectedONTs, err := FindAffectedONTsByDevices(g, []string{"olt1"})
	if err != nil {
		t.Fatalf("FindAffectedONTsByDevices failed: %v", err)
	}

	// Should find all 2 ONTs
	if len(affectedONTs) != 2 {
		t.Errorf("Expected 2 affected ONTs, got %d: %v", len(affectedONTs), affectedONTs)
	}

	// Check ONT IDs (sorted)
	expected := []string{"ont1", "ont2"}
	for i, ontID := range expected {
		if i >= len(affectedONTs) || affectedONTs[i] != ontID {
			t.Errorf("Expected ONT[%d]=%s, got %v", i, ontID, affectedONTs)
		}
	}
}

// TestFindAffectedONTsCombined tests the combined function with both link and device changes.
// Changed: Link1 (affects ONT1, ONT2) + Device OLT2 (affects ONT3, ONT4)
// Expected: All 4 ONTs (union of both sets)
func TestFindAffectedONTsCombined(t *testing.T) {
	// Build complex graph with 2 OLT networks
	g := &Graph{
		Nodes: map[string]*Node{
			"olt1": {ID: "olt1", Type: NodeTypeOLT},
			"olt2": {ID: "olt2", Type: NodeTypeOLT},
			"sp1":  {ID: "sp1", Type: NodeTypeSplitter, InsertionLossDB: 3.5, HasInsertionLoss: true},
			"sp2":  {ID: "sp2", Type: NodeTypeSplitter, InsertionLossDB: 3.5, HasInsertionLoss: true},
			"ont1": {ID: "ont1", Type: NodeTypeONT}, // OLT1
			"ont2": {ID: "ont2", Type: NodeTypeONT}, // OLT1
			"ont3": {ID: "ont3", Type: NodeTypeONT}, // OLT2
			"ont4": {ID: "ont4", Type: NodeTypeONT}, // OLT2
		},
		Edges: map[string]map[string]*Edge{
			// OLT1 network
			"olt1": {
				"sp1": {LinkID: "link1", SourceID: "olt1", TargetID: "sp1", FiberLossDB: 5.0},
			},
			"sp1": {
				"olt1": {LinkID: "link1", SourceID: "sp1", TargetID: "olt1", FiberLossDB: 5.0},
				"ont1": {LinkID: "link2", SourceID: "sp1", TargetID: "ont1", FiberLossDB: 2.0},
				"ont2": {LinkID: "link3", SourceID: "sp1", TargetID: "ont2", FiberLossDB: 2.5},
			},
			"ont1": {
				"sp1": {LinkID: "link2", SourceID: "ont1", TargetID: "sp1", FiberLossDB: 2.0},
			},
			"ont2": {
				"sp1": {LinkID: "link3", SourceID: "ont2", TargetID: "sp1", FiberLossDB: 2.5},
			},
			// OLT2 network
			"olt2": {
				"sp2": {LinkID: "link10", SourceID: "olt2", TargetID: "sp2", FiberLossDB: 5.0},
			},
			"sp2": {
				"olt2": {LinkID: "link10", SourceID: "sp2", TargetID: "olt2", FiberLossDB: 5.0},
				"ont3": {LinkID: "link11", SourceID: "sp2", TargetID: "ont3", FiberLossDB: 2.0},
				"ont4": {LinkID: "link12", SourceID: "sp2", TargetID: "ont4", FiberLossDB: 2.5},
			},
			"ont3": {
				"sp2": {LinkID: "link11", SourceID: "ont3", TargetID: "sp2", FiberLossDB: 2.0},
			},
			"ont4": {
				"sp2": {LinkID: "link12", SourceID: "ont4", TargetID: "sp2", FiberLossDB: 2.5},
			},
		},
	}

	// Changed: Link1 (OLT1-SP1) + Device OLT2
	// Expected: ont1, ont2 (from link1) + ont3, ont4 (from olt2) = 4 ONTs
	affectedONTs, err := FindAffectedONTsCombined(g, []string{"link1"}, []string{"olt2"})
	if err != nil {
		t.Fatalf("FindAffectedONTsCombined failed: %v", err)
	}

	// Should find all 4 ONTs
	if len(affectedONTs) != 4 {
		t.Errorf("Expected 4 affected ONTs, got %d: %v", len(affectedONTs), affectedONTs)
	}

	// Check ONT IDs (sorted)
	expected := []string{"ont1", "ont2", "ont3", "ont4"}
	for i, ontID := range expected {
		if i >= len(affectedONTs) || affectedONTs[i] != ontID {
			t.Errorf("Expected ONT[%d]=%s, got %v", i, ontID, affectedONTs)
		}
	}
}

// TestFindAffectedONTs_EmptyGraph tests behavior with empty graph.
// Expected: Empty result (not error)
func TestFindAffectedONTs_EmptyGraph(t *testing.T) {
	g := &Graph{
		Nodes: map[string]*Node{},
		Edges: map[string]map[string]*Edge{},
	}

	affectedONTs, err := FindAffectedONTs(g, []string{"link1"})
	if err != nil {
		t.Fatalf("FindAffectedONTs should not error on empty graph: %v", err)
	}

	if len(affectedONTs) != 0 {
		t.Errorf("Expected 0 affected ONTs for empty graph, got %d", len(affectedONTs))
	}
}

// TestFindAffectedONTs_NilGraph tests error handling with nil graph.
// Expected: Error returned
func TestFindAffectedONTs_NilGraph(t *testing.T) {
	_, err := FindAffectedONTs(nil, []string{"link1"})
	if err == nil {
		t.Fatal("Expected error for nil graph, got nil")
	}

	expectedMsg := "graph is nil"
	if err.Error() != expectedMsg {
		t.Errorf("Expected error message '%s', got '%s'", expectedMsg, err.Error())
	}
}

// TestFindAffectedONTsByDevices_NonexistentDevice tests behavior with non-existent device.
// Expected: Empty result (not error)
func TestFindAffectedONTsByDevices_NonexistentDevice(t *testing.T) {
	g := &Graph{
		Nodes: map[string]*Node{
			"olt1": {ID: "olt1", Type: NodeTypeOLT},
			"ont1": {ID: "ont1", Type: NodeTypeONT},
		},
		Edges: map[string]map[string]*Edge{
			"olt1": {
				"ont1": {LinkID: "link1", SourceID: "olt1", TargetID: "ont1", FiberLossDB: 5.0},
			},
			"ont1": {
				"olt1": {LinkID: "link1", SourceID: "ont1", TargetID: "olt1", FiberLossDB: 5.0},
			},
		},
	}

	affectedONTs, err := FindAffectedONTsByDevices(g, []string{"nonexistent_device"})
	if err != nil {
		t.Fatalf("FindAffectedONTsByDevices should not error on non-existent device: %v", err)
	}

	if len(affectedONTs) != 0 {
		t.Errorf("Expected 0 affected ONTs for non-existent device, got %d", len(affectedONTs))
	}
}
