package traffic

import (
	"math"
	"sort"

	"github.com/rs/zerolog/log"
	"github.com/unoc/engine-go/internal/graph"
	"github.com/unoc/engine-go/internal/models"
)

// LeafTypes defines device types that generate traffic (ONT, BUSINESS_ONT, AON_CPE)
var LeafTypes = map[models.DeviceType]bool{
	models.DeviceTypeONT:         true,
	models.DeviceTypeBusinessONT: true,
	models.DeviceTypeAONCPE:      true,
}

// FlowMetrics holds traffic metrics for a device or link
type FlowMetrics struct {
	UpBps   float64 // Upstream traffic in bits per second
	DownBps float64 // Downstream traffic in bits per second
}

// Flow is one leaf's requested traffic and the path it takes to its anchor.
// Scales start at 1.0 and are reduced by shaping when a path link is over
// capacity; delivered traffic is demand multiplied by the direction's scale.
type Flow struct {
	LeafID        string
	DemandUpBps   float64
	DemandDownBps float64
	ScaleUp       float64
	ScaleDown     float64
	PathNodes     []string
	PathLinks     []string
}

// DeliveredUpBps returns the post-shaping upstream traffic for the flow.
func (f *Flow) DeliveredUpBps() float64 { return f.DemandUpBps * f.ScaleUp }

// DeliveredDownBps returns the post-shaping downstream traffic for the flow.
func (f *Flow) DeliveredDownBps() float64 { return f.DemandDownBps * f.ScaleDown }

// LeafShaping summarizes the shaping outcome for one leaf.
type LeafShaping struct {
	ScaleUp   float64
	ScaleDown float64
	Throttled bool
}

// GenerationResult contains all generated traffic data
type GenerationResult struct {
	DeviceMetrics  map[string]*FlowMetrics // device_id -> delivered traffic (post shaping)
	LinkMetrics    map[string]*FlowMetrics // link_id -> delivered traffic (post shaping)
	DeviceDemand   map[string]*FlowMetrics // device_id -> requested traffic (pre shaping)
	LinkDemand     map[string]*FlowMetrics // link_id -> requested traffic (pre shaping)
	LeafShaping    map[string]*LeafShaping // leaf_id -> shaping outcome
	ShapingEnabled bool                    // whether shaping ran this tick
	LeavesCount    int                     // Number of leaves that generated traffic
	DebugInfo      map[string]interface{}  // Debug information (optional)
}

// GenerateFlows generates traffic for eligible leaf devices (ONTs, CPEs)
// Ports Python generate_flows_for_leaves() from backend/services/traffic/v2_tick.py
// Shaping is controlled by TRAFFIC_SHAPING_ENABLED (default enabled).
func GenerateFlows(
	cache *models.TopologyCache,
	adjacency *graph.AdjacencyGraph,
	tick int,
	randomSeed int,
) *GenerationResult {
	return GenerateFlowsWithShaping(cache, adjacency, tick, randomSeed, ShapingEnabledFromEnv())
}

// GenerateFlowsWithShaping generates per-leaf flows, optionally applies
// proportional bottleneck shaping, then aggregates delivered traffic.
func GenerateFlowsWithShaping(
	cache *models.TopologyCache,
	adjacency *graph.AdjacencyGraph,
	tick int,
	randomSeed int,
	shapingEnabled bool,
) *GenerationResult {
	flows := collectFlows(cache, adjacency, tick, randomSeed)

	if shapingEnabled {
		ShapeFlows(flows, cache)
	}

	result := aggregateFlows(flows, shapingEnabled)

	log.Debug().
		Int("leaves_processed", result.LeavesCount).
		Int("devices_with_traffic", len(result.DeviceMetrics)).
		Int("links_with_traffic", len(result.LinkMetrics)).
		Bool("shaping_enabled", shapingEnabled).
		Msg("Generated traffic flows")

	return result
}

// collectFlows discovers eligible leaves and builds one Flow per valid leaf
// path. Leaf eligibility rules are unchanged from B1 (provisioned, effective
// status UP per HGO-007, tariff assigned, path to an anchor exists).
func collectFlows(
	cache *models.TopologyCache,
	adjacency *graph.AdjacencyGraph,
	tick int,
	randomSeed int,
) []*Flow {
	// Track anchor types (devices that act as traffic aggregation points)
	anchorTypes := map[models.DeviceType]bool{
		models.DeviceTypeBackboneGateway: true,
		models.DeviceTypePOP:             true,
		models.DeviceTypeCoreSite:        true,
		models.DeviceTypeCoreRouter:      true,
	}

	log.Debug().Int("total_devices", len(cache.DeviceByID)).Msg("Processing devices for traffic generation")

	// Deterministic leaf order: map iteration is randomized in Go, and shaping
	// plus float aggregation must produce bit-identical output for identical
	// (topology, tick, seed) inputs.
	leafIDs := make([]string, 0, len(cache.DeviceByID))
	for deviceID, device := range cache.DeviceByID {
		if LeafTypes[device.Type] {
			leafIDs = append(leafIDs, deviceID)
		}
	}
	sort.Strings(leafIDs)

	flows := make([]*Flow, 0, len(leafIDs))

	for _, deviceID := range leafIDs {
		device := cache.DeviceByID[deviceID]

		log.Debug().
			Str("device_id", device.ID).
			Str("type", string(device.Type)).
			Bool("provisioned", device.Provisioned).
			Bool("tariff_valid", device.TariffID.Valid).
			Msg("Found leaf device")

		// Skip if not provisioned
		if !device.Provisioned {
			log.Debug().Str("device_id", device.ID).Msg("Skipped: not provisioned")
			continue
		}

		// HGO-007: DOWN leaves must not generate demand traffic now that status
		// persistence and provisioning parent checks are reliable.
		if device.EffectiveStatus() != models.StatusUP {
			log.Debug().Str("device_id", device.ID).Str("effective_status", string(device.EffectiveStatus())).Msg("Skipped: leaf not UP")
			continue
		}

		// Skip if no tariff assigned
		if !device.TariffID.Valid {
			log.Debug().Str("device_id", device.ID).Msg("Skipped: no tariff assigned")
			continue
		}

		tariff := cache.TariffByID[device.TariffID.Int64]
		if tariff == nil {
			log.Debug().Str("device_id", device.ID).Int64("tariff_id", device.TariffID.Int64).Msg("Skipped: tariff not found in cache")
			continue
		}

		log.Debug().
			Str("device_id", device.ID).
			Int64("tariff_id", device.TariffID.Int64).
			Float64("max_up_mbps", tariff.MaxUpMbps).
			Msg("Processing leaf device for traffic generation")

		// Generate deterministic demand (80-100% of tariff limits)
		// Using hash-based deterministic randomness like Python
		randomFactor := deterministicRandom(randomSeed, tick, device.ID)
		upBps := math.Max(tariff.MaxUpMbps, 0.0) * 1e6 * randomFactor
		downBps := math.Max(tariff.MaxDownMbps, 0.0) * 1e6 * randomFactor

		// Find path to nearest anchor device via BFS
		pathNodes, pathLinks := bfsPickAnchor(device.ID, adjacency, cache, anchorTypes)

		// If no valid path (only leaf device), skip generation
		if len(pathNodes) <= 1 {
			continue
		}

		flows = append(flows, &Flow{
			LeafID:        device.ID,
			DemandUpBps:   upBps,
			DemandDownBps: downBps,
			ScaleUp:       1.0,
			ScaleDown:     1.0,
			PathNodes:     pathNodes,
			PathLinks:     pathLinks,
		})
	}

	return flows
}

// aggregateFlows sums delivered and requested traffic onto every path device
// and link, and records the per-leaf shaping outcome.
func aggregateFlows(flows []*Flow, shapingEnabled bool) *GenerationResult {
	result := &GenerationResult{
		DeviceMetrics:  make(map[string]*FlowMetrics),
		LinkMetrics:    make(map[string]*FlowMetrics),
		DeviceDemand:   make(map[string]*FlowMetrics),
		LinkDemand:     make(map[string]*FlowMetrics),
		LeafShaping:    make(map[string]*LeafShaping, len(flows)),
		ShapingEnabled: shapingEnabled,
		LeavesCount:    len(flows),
		DebugInfo:      make(map[string]interface{}),
	}

	for _, flow := range flows {
		deliveredUp := flow.DeliveredUpBps()
		deliveredDown := flow.DeliveredDownBps()

		for _, deviceID := range flow.PathNodes {
			if result.DeviceMetrics[deviceID] == nil {
				result.DeviceMetrics[deviceID] = &FlowMetrics{}
				result.DeviceDemand[deviceID] = &FlowMetrics{}
			}
			result.DeviceMetrics[deviceID].UpBps += deliveredUp
			result.DeviceMetrics[deviceID].DownBps += deliveredDown
			result.DeviceDemand[deviceID].UpBps += flow.DemandUpBps
			result.DeviceDemand[deviceID].DownBps += flow.DemandDownBps
		}

		for _, linkID := range flow.PathLinks {
			if result.LinkMetrics[linkID] == nil {
				result.LinkMetrics[linkID] = &FlowMetrics{}
				result.LinkDemand[linkID] = &FlowMetrics{}
			}
			result.LinkMetrics[linkID].UpBps += deliveredUp
			result.LinkMetrics[linkID].DownBps += deliveredDown
			result.LinkDemand[linkID].UpBps += flow.DemandUpBps
			result.LinkDemand[linkID].DownBps += flow.DemandDownBps
		}

		result.LeafShaping[flow.LeafID] = &LeafShaping{
			ScaleUp:   flow.ScaleUp,
			ScaleDown: flow.ScaleDown,
			Throttled: flow.ScaleUp < ThrottleScaleThreshold || flow.ScaleDown < ThrottleScaleThreshold,
		}
	}

	return result
}

// deterministicRandom generates a deterministic random value in range [0.8, 1.0]
// Matches Python's deterministic_rand01 behavior (80-100% of tariff capacity)
func deterministicRandom(seed, tick int, deviceID string) float64 {
	// Simple hash-based PRNG (matches Python behavior)
	hash := uint64(seed)
	hash ^= uint64(tick)
	for _, c := range deviceID {
		hash = hash*31 + uint64(c)
	}

	// LCG (Linear Congruential Generator) for deterministic output
	hash = (hash*1103515245 + 12345) & 0x7fffffff

	// Map to [0.8, 1.0] range
	normalized := float64(hash) / float64(0x7fffffff)
	return 0.8 + (normalized * 0.2)
}

// bfsPickAnchor finds the shortest path from a leaf device to an anchor device
// Ports Python bfs_pick_anchor() from backend/services/traffic/v2_path.py
func bfsPickAnchor(
	startID string,
	adjacency *graph.AdjacencyGraph,
	cache *models.TopologyCache,
	anchorTypes map[models.DeviceType]bool,
) ([]string, []string) {
	// Parent tracking (NO PATH COPYING!)
	type parentInfo struct {
		deviceID string
		linkID   string
	}
	parents := make(map[string]parentInfo)
	parents[startID] = parentInfo{deviceID: "", linkID: ""}

	// BFS queue: just device IDs (no path storage!)
	queue := make([]string, 0, len(cache.DeviceByID))
	queue = append(queue, startID)

	visited := map[string]bool{startID: true}
	head := 0

	// Track ALL anchors found, then pick best one (BACKBONE > CORE > POP > other)
	var backboneAnchor, coreAnchor, popAnchor, anyAnchor string

	for head < len(queue) {
		currentID := queue[head]
		head++

		currentDevice := cache.DeviceByID[currentID]
		if currentDevice == nil {
			continue
		}

		// Track anchors by preference order (BACKBONE > CORE > POP > other)
		if anchorTypes[currentDevice.Type] && currentID != startID {
			switch currentDevice.Type {
			case "BACKBONE_GATEWAY":
				if backboneAnchor == "" {
					backboneAnchor = currentID
				}
			case "CORE_ROUTER", "CORE_SITE":
				if coreAnchor == "" {
					coreAnchor = currentID
				}
			case "POP":
				if popAnchor == "" {
					popAnchor = currentID
				}
			default:
				if anyAnchor == "" {
					anyAnchor = currentID
				}
			}
			// Don't break! Continue BFS to find ALL anchors
		}

		// Explore neighbors
		neighbors := adjacency.GetNeighbors(currentID)
		for _, neighborID := range neighbors {
			if visited[neighborID] {
				continue
			}

			neighborDevice := cache.DeviceByID[neighborID]
			if neighborDevice == nil {
				continue
			}

			// Only traverse UP devices
			if neighborDevice.EffectiveStatus() != models.StatusUP {
				continue
			}

			visited[neighborID] = true

			// Record parent + link
			linkID := adjacency.GetLinkBetween(currentID, neighborID)
			parents[neighborID] = parentInfo{
				deviceID: currentID,
				linkID:   linkID,
			}

			queue = append(queue, neighborID)
		}
	}

	// Pick BEST anchor by preference order: BACKBONE > CORE > POP > other
	anchorID := backboneAnchor
	if anchorID == "" {
		anchorID = coreAnchor
	}
	if anchorID == "" {
		anchorID = popAnchor
	}
	if anchorID == "" {
		anchorID = anyAnchor
	}

	// Reconstruct path from anchor back to start (ONLY ONCE!)
	if anchorID == "" {
		// No anchor found
		return []string{startID}, []string{}
	}

	// Backtrack from anchor → start
	pathNodes := []string{}
	pathLinks := []string{}
	current := anchorID

	for current != "" {
		pathNodes = append(pathNodes, current)
		parent := parents[current]
		if parent.linkID != "" {
			pathLinks = append(pathLinks, parent.linkID)
		}
		current = parent.deviceID
	}

	// Reverse paths (built backwards)
	for i, j := 0, len(pathNodes)-1; i < j; i, j = i+1, j-1 {
		pathNodes[i], pathNodes[j] = pathNodes[j], pathNodes[i]
	}
	for i, j := 0, len(pathLinks)-1; i < j; i, j = i+1, j-1 {
		pathLinks[i], pathLinks[j] = pathLinks[j], pathLinks[i]
	}

	return pathNodes, pathLinks
}
