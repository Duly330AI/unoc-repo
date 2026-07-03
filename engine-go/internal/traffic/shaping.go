package traffic

import (
	"os"
	"sort"
	"strings"

	"github.com/rs/zerolog/log"
	"github.com/unoc/engine-go/internal/models"
)

const (
	// ShapingEnabledEnvVar toggles proportional bottleneck shaping (B2).
	// Unset or any value other than false/0/no/off means enabled.
	ShapingEnabledEnvVar = "TRAFFIC_SHAPING_ENABLED"

	// ThrottleScaleThreshold marks a leaf as throttled when either direction
	// was scaled below this factor. Slightly under 1.0 so float noise from
	// near-capacity ratios does not flag unshaped leaves.
	ThrottleScaleThreshold = 0.98

	// shapingPasses bounds the fixed shaping loop. A single pass already
	// guarantees delivered <= capacity on every link (scales only shrink);
	// the extra passes are a cheap stabilizer across compounded bottlenecks
	// and exit early once nothing changes. Not a max-min fairness solver.
	shapingPasses = 3
)

// ShapingEnabledFromEnv reads TRAFFIC_SHAPING_ENABLED. Default: enabled.
func ShapingEnabledFromEnv() bool {
	value := strings.ToLower(strings.TrimSpace(os.Getenv(ShapingEnabledEnvVar)))
	switch value {
	case "false", "0", "no", "off":
		return false
	default:
		return true
	}
}

// ShapeFlows applies proportional downscaling per bottleneck link, per
// direction: every flow crossing an over-capacity link is scaled by
// capacity/demand for that direction, so delivered traffic proportionally
// shares the link and never exceeds it. A flow crossing several bottlenecks
// is scaled by each of them (conservative under-delivery is acceptable;
// over-delivery is not).
func ShapeFlows(flows []*Flow, cache *models.TopologyCache) {
	if len(flows) == 0 || cache == nil {
		return
	}

	// Resolve capacity once per crossed link and group flows by link.
	capacityBps := make(map[string]float64)
	flowsByLink := make(map[string][]*Flow)
	for _, flow := range flows {
		for _, linkID := range flow.PathLinks {
			if _, seen := capacityBps[linkID]; !seen {
				capacityBps[linkID] = EffectiveLinkCapacityMbps(cache.LinkByID[linkID], cache) * 1_000_000
			}
			flowsByLink[linkID] = append(flowsByLink[linkID], flow)
		}
	}

	// Sorted link order keeps float multiplication order deterministic.
	linkIDs := make([]string, 0, len(flowsByLink))
	for linkID := range flowsByLink {
		linkIDs = append(linkIDs, linkID)
	}
	sort.Strings(linkIDs)

	shapedLinks := 0
	for pass := 0; pass < shapingPasses; pass++ {
		changed := false
		for _, linkID := range linkIDs {
			capBps := capacityBps[linkID]
			if capBps <= 0 {
				// Unknown capacity: never shape on guesses.
				continue
			}

			var sumUpBps, sumDownBps float64
			for _, flow := range flowsByLink[linkID] {
				sumUpBps += flow.DeliveredUpBps()
				sumDownBps += flow.DeliveredDownBps()
			}

			if sumUpBps > capBps {
				ratio := capBps / sumUpBps
				for _, flow := range flowsByLink[linkID] {
					flow.ScaleUp *= ratio
				}
				changed = true
				shapedLinks++
				log.Debug().
					Str("link_id", linkID).
					Float64("demand_up_bps", sumUpBps).
					Float64("capacity_bps", capBps).
					Float64("ratio", ratio).
					Msg("Shaped upstream at bottleneck link")
			}

			if sumDownBps > capBps {
				ratio := capBps / sumDownBps
				for _, flow := range flowsByLink[linkID] {
					flow.ScaleDown *= ratio
				}
				changed = true
				shapedLinks++
				log.Debug().
					Str("link_id", linkID).
					Float64("demand_down_bps", sumDownBps).
					Float64("capacity_bps", capBps).
					Float64("ratio", ratio).
					Msg("Shaped downstream at bottleneck link")
			}
		}
		if !changed {
			break
		}
	}

	if shapedLinks > 0 {
		log.Debug().
			Int("shaped_link_directions", shapedLinks).
			Int("flows", len(flows)).
			Msg("Proportional shaping applied")
	}
}
