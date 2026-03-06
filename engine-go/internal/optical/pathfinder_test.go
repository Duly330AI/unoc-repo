package optical

import (
	"container/heap"
	"testing"
)

func TestPriorityQueue(t *testing.T) {
	pq := &PriorityQueue{}
	heap.Init(pq) // Must initialize heap!

	// Test empty queue
	if pq.Len() != 0 {
		t.Errorf("expected empty queue, got len=%d", pq.Len())
	}

	// Test Push (using heap.Push, not pq.Push!)
	item1 := &PriorityQueueItem{NodeID: "node1", Distance: 5.0}
	item2 := &PriorityQueueItem{NodeID: "node2", Distance: 2.0}
	item3 := &PriorityQueueItem{NodeID: "node3", Distance: 8.0}

	heap.Push(pq, item1)
	heap.Push(pq, item2)
	heap.Push(pq, item3)

	if pq.Len() != 3 {
		t.Errorf("expected len=3, got %d", pq.Len())
	}

	// Test Pop (should return min distance first using heap.Pop!)
	popped := heap.Pop(pq).(*PriorityQueueItem)
	if popped.NodeID != "node2" || popped.Distance != 2.0 {
		t.Errorf("expected node2 with distance 2.0, got %s with distance %f", popped.NodeID, popped.Distance)
	}

	popped = heap.Pop(pq).(*PriorityQueueItem)
	if popped.NodeID != "node1" || popped.Distance != 5.0 {
		t.Errorf("expected node1 with distance 5.0, got %s with distance %f", popped.NodeID, popped.Distance)
	}

	popped = heap.Pop(pq).(*PriorityQueueItem)
	if popped.NodeID != "node3" || popped.Distance != 8.0 {
		t.Errorf("expected node3 with distance 8.0, got %s with distance %f", popped.NodeID, popped.Distance)
	}
}

func TestDijkstra_SimpleGraph(t *testing.T) {
	// Create a simple test graph: A -> B -> C
	// A (ONT) -> B (SPLITTER with 0.5dB insertion) -> C (OLT)
	insertionLoss := 0.5
	g := NewGraph()

	// Add nodes
	g.AddNode(&Node{ID: "A", Type: NodeTypeONT, InsertionLossDB: 0.0, HasInsertionLoss: false})
	g.AddNode(&Node{ID: "B", Type: NodeTypeSplitter, InsertionLossDB: insertionLoss, HasInsertionLoss: true})
	g.AddNode(&Node{ID: "C", Type: NodeTypeOLT, InsertionLossDB: 0.0, HasInsertionLoss: false})

	// Add edges (Graph.AddEdge creates bidirectional automatically)
	err := g.AddEdge(&Edge{
		LinkID:       "link-ab",
		SourceID:     "A",
		TargetID:     "B",
		FiberLossDB:  1.0,
		HasFiberLoss: true,
	})
	if err != nil {
		t.Fatalf("failed to add edge A->B: %v", err)
	}

	err = g.AddEdge(&Edge{
		LinkID:       "link-bc",
		SourceID:     "B",
		TargetID:     "C",
		FiberLossDB:  2.0,
		HasFiberLoss: true,
	})
	if err != nil {
		t.Fatalf("failed to add edge B->C: %v", err)
	}

	pf := &PathFinder{}
	distances, paths, err := pf.dijkstra(g, "A")
	if err != nil {
		t.Fatalf("dijkstra failed: %v", err)
	}

	// Check distances
	// A -> B: 1.0 (fiber) + 0.5 (insertion) = 1.5
	// A -> C: 1.5 + 2.0 (fiber) = 3.5
	expectedDistances := map[string]float64{
		"A": 0.0,
		"B": 1.5,
		"C": 3.5,
	}

	for node, expectedDist := range expectedDistances {
		actualDist := distances[node]
		if actualDist != expectedDist {
			t.Errorf("node %s: expected distance %f, got %f", node, expectedDist, actualDist)
		}
	}

	// Check paths
	expectedPath := []string{"A", "B", "C"}
	actualPath := paths["C"]
	if len(actualPath) != len(expectedPath) {
		t.Fatalf("path to C: expected length %d, got %d", len(expectedPath), len(actualPath))
	}
	for i := range expectedPath {
		if actualPath[i] != expectedPath[i] {
			t.Errorf("path to C[%d]: expected %s, got %s", i, expectedPath[i], actualPath[i])
		}
	}
}

func TestDijkstra_MultipleOLTs(t *testing.T) {
	// Create graph with multiple OLTs:
	//     OLT1 (5.0dB)
	//    /
	//  ONT
	//    \
	//     OLT2 (2.0dB - shorter path)

	g := NewGraph()
	g.AddNode(&Node{ID: "ONT", Type: NodeTypeONT})
	g.AddNode(&Node{ID: "OLT1", Type: NodeTypeOLT})
	g.AddNode(&Node{ID: "OLT2", Type: NodeTypeOLT})

	g.AddEdge(&Edge{
		LinkID:       "link-ont-olt1",
		SourceID:     "ONT",
		TargetID:     "OLT1",
		FiberLossDB:  5.0,
		HasFiberLoss: true,
	})
	g.AddEdge(&Edge{
		LinkID:       "link-ont-olt2",
		SourceID:     "ONT",
		TargetID:     "OLT2",
		FiberLossDB:  2.0,
		HasFiberLoss: true,
	})

	pf := &PathFinder{}
	distances, _, err := pf.dijkstra(g, "ONT")
	if err != nil {
		t.Fatalf("dijkstra failed: %v", err)
	}

	// OLT2 should be closer
	if distances["OLT2"] != 2.0 {
		t.Errorf("expected distance to OLT2 = 2.0, got %f", distances["OLT2"])
	}
	if distances["OLT1"] != 5.0 {
		t.Errorf("expected distance to OLT1 = 5.0, got %f", distances["OLT1"])
	}
}

func TestNodeTypeIsPassive(t *testing.T) {
	passiveTypes := []NodeType{NodeTypeSplitter, NodeTypeHOP, NodeTypeNVT, NodeTypeODF}
	for _, nt := range passiveTypes {
		if !nt.IsPassive() {
			t.Errorf("expected %s to be passive", nt)
		}
	}

	nonPassiveTypes := []NodeType{NodeTypeOLT, NodeTypeONT, NodeTypeBusinessONT}
	for _, nt := range nonPassiveTypes {
		if nt.IsPassive() {
			t.Errorf("expected %s to NOT be passive", nt)
		}
	}
}

func TestFiberAttenuationDB(t *testing.T) {
	testCases := []struct {
		code     string
		expected float64
	}{
		{"SM_G652D", 0.35},
		{"SM_G657A", 0.30},
		{"MM_OM3", 3.00},
		{"MM_OM4", 2.50},
		{"FIBER_DEFAULT", 0.35},
	}

	for _, tc := range testCases {
		actual := FiberAttenuationDB[tc.code]
		if actual != tc.expected {
			t.Errorf("fiber %s: expected %f dB/km, got %f", tc.code, tc.expected, actual)
		}
	}
}

func TestGraphOperations(t *testing.T) {
	g := NewGraph()

	// Test AddNode
	g.AddNode(&Node{ID: "node1", Type: NodeTypeONT})
	if _, ok := g.Nodes["node1"]; !ok {
		t.Error("failed to add node1")
	}

	// Test GetNeighbors (empty)
	neighbors := g.GetNeighbors("node1")
	if len(neighbors) != 0 {
		t.Errorf("expected 0 neighbors, got %d", len(neighbors))
	}

	// Add second node and edge
	g.AddNode(&Node{ID: "node2", Type: NodeTypeOLT})
	err := g.AddEdge(&Edge{
		LinkID:       "link1",
		SourceID:     "node1",
		TargetID:     "node2",
		FiberLossDB:  1.5,
		HasFiberLoss: true,
	})
	if err != nil {
		t.Fatalf("failed to add edge: %v", err)
	}

	// Test GetNeighbors (should have 1 neighbor now)
	neighbors = g.GetNeighbors("node1")
	if len(neighbors) != 1 {
		t.Errorf("expected 1 neighbor, got %d", len(neighbors))
	}
	if neighbors[0] != "node2" {
		t.Errorf("expected neighbor node2, got %s", neighbors[0])
	}

	// Test GetEdge
	edge, ok := g.GetEdge("node1", "node2")
	if !ok {
		t.Error("expected edge to exist")
	}
	if edge.FiberLossDB != 1.5 {
		t.Errorf("expected fiber loss 1.5, got %f", edge.FiberLossDB)
	}

	// Test reverse edge (should be automatic)
	reverseEdge, ok := g.GetEdge("node2", "node1")
	if !ok {
		t.Error("expected reverse edge to exist")
	}
	if reverseEdge.FiberLossDB != 1.5 {
		t.Errorf("expected reverse fiber loss 1.5, got %f", reverseEdge.FiberLossDB)
	}
}
