// Package optical implements optical path resolution using Dijkstra's algorithm.
// This is the Go port of backend/services/optical_path_resolver.py (TASK-034B).
//
// Architecture:
// - Graph structure: nodes (devices) and edges (links) with attenuation weights
// - Dijkstra algorithm: finds minimum-attenuation path from ONT to OLT
// - Custom weights: fiber loss (length_km * attenuation_db_per_km) + passive insertion loss
// - Deterministic ordering: attenuation → length → hops → OLT ID → path signature
//
// Week 2 Day 6: Data structures and graph representation
package optical

import "fmt"

// NodeType represents device types in the optical graph.
type NodeType string

const (
	NodeTypeOLT         NodeType = "OLT"
	NodeTypeONT         NodeType = "ONT"
	NodeTypeBusinessONT NodeType = "BUSINESS_ONT"
	NodeTypeSplitter    NodeType = "SPLITTER"
	NodeTypeHOP         NodeType = "HOP"
	NodeTypeNVT         NodeType = "NVT"
	NodeTypeODF         NodeType = "ODF"
)

// IsPassive returns true if the node type is a passive inline device.
// Matches Python PASSIVE_NODE_TYPES = {"SPLITTER", "HOP", "NVT", "ODF"}
func (nt NodeType) IsPassive() bool {
	switch nt {
	case NodeTypeSplitter, NodeTypeHOP, NodeTypeNVT, NodeTypeODF:
		return true
	default:
		return false
	}
}

// IsOLT returns true if the node type is an OLT.
func (nt NodeType) IsOLT() bool {
	return nt == NodeTypeOLT
}

// Node represents a device in the optical graph.
type Node struct {
	ID               string   // Device ID
	Type             NodeType // Device type (OLT, ONT, SPLITTER, etc.)
	InsertionLossDB  float64  // Insertion loss for passive devices (dB)
	HasInsertionLoss bool     // Whether insertion_loss_db is set (to distinguish 0.0 from NULL)
}

// Edge represents a link between two devices in the optical graph.
type Edge struct {
	LinkID         string  // Link ID from database
	SourceID       string  // Source device ID
	TargetID       string  // Target device ID
	FiberLossDB    float64 // Fiber attenuation: length_km * attenuation_db_per_km
	HasFiberLoss   bool    // Whether fiber loss is known (to distinguish 0.0 from NULL)
	LengthKm       float64 // Physical fiber length in km (for tie-breaking)
	HasLengthKm    bool    // Whether length_km is set
	PhysicalMedium string  // Physical medium code (e.g., "SM_G652D")
}

// Graph represents the optical network topology.
// This is a simple adjacency list representation optimized for Dijkstra.
type Graph struct {
	Nodes map[string]*Node            // Node ID -> Node data
	Edges map[string]map[string]*Edge // Source ID -> Target ID -> Edge data (undirected: both directions stored)
}

// NewGraph creates an empty optical graph.
func NewGraph() *Graph {
	return &Graph{
		Nodes: make(map[string]*Node),
		Edges: make(map[string]map[string]*Edge),
	}
}

// AddNode adds a node to the graph.
func (g *Graph) AddNode(node *Node) {
	if node == nil {
		return
	}
	g.Nodes[node.ID] = node
}

// AddEdge adds an undirected edge to the graph (stored in both directions).
func (g *Graph) AddEdge(edge *Edge) error {
	if edge == nil {
		return fmt.Errorf("cannot add nil edge")
	}
	if edge.SourceID == "" || edge.TargetID == "" {
		return fmt.Errorf("edge missing source or target ID")
	}

	// Ensure both nodes exist
	if _, ok := g.Nodes[edge.SourceID]; !ok {
		return fmt.Errorf("source node %s not found in graph", edge.SourceID)
	}
	if _, ok := g.Nodes[edge.TargetID]; !ok {
		return fmt.Errorf("target node %s not found in graph", edge.TargetID)
	}

	// Add edge in both directions (undirected graph)
	if g.Edges[edge.SourceID] == nil {
		g.Edges[edge.SourceID] = make(map[string]*Edge)
	}
	g.Edges[edge.SourceID][edge.TargetID] = edge

	// Add reverse edge
	reverseEdge := &Edge{
		LinkID:         edge.LinkID,
		SourceID:       edge.TargetID,
		TargetID:       edge.SourceID,
		FiberLossDB:    edge.FiberLossDB,
		HasFiberLoss:   edge.HasFiberLoss,
		LengthKm:       edge.LengthKm,
		HasLengthKm:    edge.HasLengthKm,
		PhysicalMedium: edge.PhysicalMedium,
	}
	if g.Edges[edge.TargetID] == nil {
		g.Edges[edge.TargetID] = make(map[string]*Edge)
	}
	g.Edges[edge.TargetID][edge.SourceID] = reverseEdge

	return nil
}

// GetNeighbors returns all neighbor node IDs for a given node.
func (g *Graph) GetNeighbors(nodeID string) []string {
	neighbors := make([]string, 0, len(g.Edges[nodeID]))
	for targetID := range g.Edges[nodeID] {
		neighbors = append(neighbors, targetID)
	}
	return neighbors
}

// GetEdge returns the edge between two nodes (if it exists).
func (g *Graph) GetEdge(sourceID, targetID string) (*Edge, bool) {
	if edges, ok := g.Edges[sourceID]; ok {
		if edge, ok := edges[targetID]; ok {
			return edge, true
		}
	}
	return nil, false
}

// PathSegment represents one hop in the optical path.
// Matches Python PathSegment dataclass.
type PathSegment struct {
	Src           string  // Source node ID
	Dst           string  // Destination node ID
	LinkID        *string // Link ID (nil if not available)
	AttenuationDB float64 // Attenuation for this segment (dB)
}

// OpticalPathResult represents the result of path resolution.
// Matches Python OpticalPathResult dataclass.
type OpticalPathResult struct {
	OLTID              string        // OLT device ID
	TotalAttenuationDB float64       // Total path attenuation (dB)
	Segments           []PathSegment // Path segments from ONT to OLT
	TotalLengthKm      float64       // Total physical path length (km) - for tie-breaking
	HopCount           int           // Number of hops - for tie-breaking
}

// DeviceRecord represents a device snapshot for graph building.
// Matches Python DeviceRecord dataclass from pathfinding.py
type DeviceRecord struct {
	ID              string   // Device ID
	Type            string   // Device type string (e.g., "OLT", "ONT")
	InsertionLossDB *float64 // Optional insertion loss for passive devices
}

// LinkRecord represents a link snapshot for graph building.
// Matches Python LinkRecord dataclass from pathfinding.py
type LinkRecord struct {
	ID             string   // Link ID
	ADeviceID      string   // Source device ID
	BDeviceID      string   // Target device ID
	Kind           string   // Link kind/class (e.g., "FIBER")
	LengthKm       *float64 // Optional fiber length in km
	PhysicalMedium *string  // Optional physical medium code
}
