package graph

import (
	"github.com/rs/zerolog/log"
	"github.com/unoc/engine-go/internal/models"
)

// AdjacencyGraph represents device-to-device connectivity
type AdjacencyGraph struct {
	Neighbors   map[string]map[string]bool // device_id -> set of neighbor device_ids
	LinkByPair  map[string]string          // "dev_a|dev_b" -> link_id (sorted)
	IfaceDevice map[string]string          // interface_id -> device_id
}

// BuildAdjacency constructs adjacency graph from topology data
// Ports Python build_adjacency() from backend/services/traffic/v2_graph.py
// with inline link status evaluation (PERF-002 optimization)
func BuildAdjacency(cache *models.TopologyCache) *AdjacencyGraph {
	graph := &AdjacencyGraph{
		Neighbors:   make(map[string]map[string]bool),
		LinkByPair:  make(map[string]string),
		IfaceDevice: make(map[string]string),
	}

	// Build interface-to-device mapping (fast lookup)
	for ifaceID, iface := range cache.InterfaceByID {
		graph.IfaceDevice[ifaceID] = iface.DeviceID
	}

	// Build device override map for inline link status evaluation
	deviceOverrides := make(map[string]models.Status)
	for devID, dev := range cache.DeviceByID {
		if dev.AdminOverrideStatus.Valid {
			deviceOverrides[devID] = models.Status(dev.AdminOverrideStatus.String)
		}
	}

	linkCount := 0
	skipped := 0

	// Process all links
	for _, link := range cache.LinksByInterface {
		for _, ln := range link {
			// Inline link status evaluation (PERF-002 from Python)
			effectiveStatus := ln.Status

			// Admin override on link wins
			if ln.AdminOverrideStatus.Valid {
				effectiveStatus = models.Status(ln.AdminOverrideStatus.String)
			} else {
				// Check endpoint device overrides
				aDevID := graph.IfaceDevice[ln.AInterfaceID]
				bDevID := graph.IfaceDevice[ln.BInterfaceID]

				if deviceOverrides[aDevID] == models.StatusDOWN {
					effectiveStatus = models.StatusDOWN
				} else if deviceOverrides[bDevID] == models.StatusDOWN {
					effectiveStatus = models.StatusDOWN
				}
			}

			// Only process UP links
			if effectiveStatus != models.StatusUP {
				skipped++
				continue
			}

			// Get endpoint devices
			aDevID := graph.IfaceDevice[ln.AInterfaceID]
			bDevID := graph.IfaceDevice[ln.BInterfaceID]

			if aDevID == "" || bDevID == "" {
				skipped++
				continue
			}

			// Add bidirectional edges
			if graph.Neighbors[aDevID] == nil {
				graph.Neighbors[aDevID] = make(map[string]bool)
			}
			if graph.Neighbors[bDevID] == nil {
				graph.Neighbors[bDevID] = make(map[string]bool)
			}
			graph.Neighbors[aDevID][bDevID] = true
			graph.Neighbors[bDevID][aDevID] = true

			// Store link by sorted device pair (for lookup in aggregation)
			pairKey := makePairKey(aDevID, bDevID)
			graph.LinkByPair[pairKey] = ln.ID

			linkCount++
		}
	}

	log.Info().
		Int("passable_links", linkCount).
		Int("skipped_links", skipped).
		Int("devices_in_graph", len(graph.Neighbors)).
		Msg("Built adjacency graph")

	return graph
}

// makePairKey creates a consistent key for device pairs (sorted alphabetically)
func makePairKey(devA, devB string) string {
	if devA < devB {
		return devA + "|" + devB
	}
	return devB + "|" + devA
}

// GetNeighbors returns all neighbors of a device (or nil if device not in graph)
func (g *AdjacencyGraph) GetNeighbors(deviceID string) []string {
	neighbors := g.Neighbors[deviceID]
	if neighbors == nil {
		return nil
	}

	// Convert set to slice
	result := make([]string, 0, len(neighbors))
	for neighbor := range neighbors {
		result = append(result, neighbor)
	}
	return result
}

// GetLinkBetween returns link ID connecting two devices (or empty string if not connected)
func (g *AdjacencyGraph) GetLinkBetween(devA, devB string) string {
	return g.LinkByPair[makePairKey(devA, devB)]
}
