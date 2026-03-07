// Package optical implements graph building from device and link records.
// This is the Go port of build_optical_graph from Python pathfinding.py
//
// Week 2 Day 6: Graph builder
package optical

import "fmt"

// BuildOpticalGraph constructs an optical graph from device and link records.
// Matches Python build_optical_graph logic from pathfinding.py
//
// Optical graph includes:
// - Active nodes: OLT
// - Terminator nodes: ONT, BUSINESS_ONT
// - Passive inline nodes: ODF, NVT, SPLITTER, HOP
// - Edges: optical_segment, optical_termination (fiber links)
func BuildOpticalGraph(devices []DeviceRecord, links []LinkRecord, fiberTypes map[string]FiberType) (*Graph, error) {
	g := NewGraph()

	// 1. Add all devices as nodes (filter to optical-relevant types)
	opticalTypes := map[NodeType]bool{
		NodeTypeOLT:         true,
		NodeTypeONT:         true,
		NodeTypeBusinessONT: true,
		NodeTypeSplitter:    true,
		NodeTypeHOP:         true,
		NodeTypeNVT:         true,
		NodeTypeODF:         true,
	}

	for _, dev := range devices {
		nodeType := NodeType(dev.Type)

		// Skip non-optical device types
		if !opticalTypes[nodeType] {
			continue
		}

		node := &Node{
			ID:   dev.ID,
			Type: nodeType,
		}

		// Add insertion loss for passive devices
		if dev.InsertionLossDB != nil {
			node.InsertionLossDB = *dev.InsertionLossDB
			node.HasInsertionLoss = true
		}

		g.AddNode(node)
	}

	// 2. Add links as edges (only fiber/optical links)
	opticalLinkKinds := map[string]bool{
		"FIBER":               true,
		"optical_segment":     true,
		"optical_termination": true,
	}

	for _, link := range links {
		// Skip non-optical link kinds
		if !opticalLinkKinds[link.Kind] {
			continue
		}

		// Skip links where endpoints aren't in graph (non-optical devices)
		if _, ok := g.Nodes[link.ADeviceID]; !ok {
			continue
		}
		if _, ok := g.Nodes[link.BDeviceID]; !ok {
			continue
		}

		// Compute fiber loss if physical medium and length are available
		fiberLossDB := 0.0
		hasFiberLoss := false
		lengthKm := 0.0
		hasLengthKm := false

		if link.LengthKm != nil && link.PhysicalMedium != nil {
			lengthKm = *link.LengthKm
			hasLengthKm = true

			// Look up attenuation from fiber types catalog
			if fiberType, ok := fiberTypes[*link.PhysicalMedium]; ok {
				fiberLossDB = lengthKm * fiberType.AttenuationDBPerKm
				hasFiberLoss = true
			}
		}

		edge := &Edge{
			LinkID:         link.ID,
			SourceID:       link.ADeviceID,
			TargetID:       link.BDeviceID,
			FiberLossDB:    fiberLossDB,
			HasFiberLoss:   hasFiberLoss,
			LengthKm:       lengthKm,
			HasLengthKm:    hasLengthKm,
			PhysicalMedium: "",
		}
		if link.PhysicalMedium != nil {
			edge.PhysicalMedium = *link.PhysicalMedium
		}

		if err := g.AddEdge(edge); err != nil {
			return nil, fmt.Errorf("failed to add edge %s: %w", link.ID, err)
		}
	}

	return g, nil
}

// ValidateGraph checks that the graph is well-formed for optical path resolution.
func ValidateGraph(g *Graph) error {
	// Check that at least one OLT exists
	hasOLT := false
	for _, node := range g.Nodes {
		if node.Type.IsOLT() {
			hasOLT = true
			break
		}
	}
	if !hasOLT {
		return fmt.Errorf("optical graph must contain at least one OLT")
	}

	// Check that edges reference valid nodes
	for sourceID, targets := range g.Edges {
		if _, ok := g.Nodes[sourceID]; !ok {
			return fmt.Errorf("edge references non-existent source node: %s", sourceID)
		}
		for targetID := range targets {
			if _, ok := g.Nodes[targetID]; !ok {
				return fmt.Errorf("edge references non-existent target node: %s", targetID)
			}
		}
	}

	return nil
}
