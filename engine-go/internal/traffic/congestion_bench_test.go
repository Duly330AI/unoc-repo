package traffic

import (
	"fmt"
	"testing"

	"github.com/unoc/engine-go/internal/graph"
	"github.com/unoc/engine-go/internal/models"
)

// BenchmarkDetectCongestion_Small benchmarks congestion detection for small topology
func BenchmarkDetectCongestion_Small(b *testing.B) {
	cache, adj := buildSmallCongTopology()
	result := GenerateFlows(cache, adj, 1, 42)
	prevState := NewCongestionState()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = DetectCongestion(result, cache, prevState)
	}
}

// BenchmarkDetectCongestion_Medium benchmarks congestion detection for medium topology
func BenchmarkDetectCongestion_Medium(b *testing.B) {
	cache, adj := buildMediumCongTopology()
	result := GenerateFlows(cache, adj, 1, 42)
	prevState := NewCongestionState()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = DetectCongestion(result, cache, prevState)
	}
}

// BenchmarkDetectCongestion_Large benchmarks congestion detection for large topology
func BenchmarkDetectCongestion_Large(b *testing.B) {
	cache, adj := buildLargeCongTopology()
	result := GenerateFlows(cache, adj, 1, 42)
	prevState := NewCongestionState()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = DetectCongestion(result, cache, prevState)
	}
}

// buildSmallCongTopology creates small test topology (10 devices, 9 links)
func buildSmallCongTopology() (*models.TopologyCache, *graph.AdjacencyGraph) {
	var devices []models.Device
	var links []models.Link

	// 1 Core
	devices = append(devices, models.Device{
		ID:     "core1",
		Type:   models.DeviceTypeCoreRouter,
		Status: models.StatusUP,
	})

	// 1 OLT
	devices = append(devices, models.Device{
		ID:     "olt1",
		Type:   models.DeviceTypeOLT,
		Status: models.StatusUP,
	})

	// 8 ONTs
	for i := 1; i <= 8; i++ {
		devices = append(devices, models.Device{
			ID:     fmt.Sprintf("ont%d", i),
			Type:   models.DeviceTypeONT,
			Status: models.StatusUP,
		})
	}

	// Core → OLT link
	links = append(links, models.Link{
		ID:           "link_core1_olt1",
		AInterfaceID: "core1-eth0",
		BInterfaceID: "olt1-uplink0",
		Status:       models.StatusUP,
	})

	// OLT → ONT links
	for i := 1; i <= 8; i++ {
		links = append(links, models.Link{
			ID:           fmt.Sprintf("link_olt1_ont%d", i),
			AInterfaceID: fmt.Sprintf("olt1-pon%d", i),
			BInterfaceID: fmt.Sprintf("ont%d-eth0", i),
			Status:       models.StatusUP,
		})
	}

	return buildCongTopologyCache(devices, links)
}

// buildMediumCongTopology creates medium test topology (100 devices, ~100 links)
func buildMediumCongTopology() (*models.TopologyCache, *graph.AdjacencyGraph) {
	var devices []models.Device
	var links []models.Link

	// 2 Cores
	for i := 1; i <= 2; i++ {
		devices = append(devices, models.Device{
			ID:     fmt.Sprintf("core%d", i),
			Type:   models.DeviceTypeCoreRouter,
			Status: models.StatusUP,
		})
	}

	// 8 OLTs
	for i := 1; i <= 8; i++ {
		devices = append(devices, models.Device{
			ID:     fmt.Sprintf("olt%d", i),
			Type:   models.DeviceTypeOLT,
			Status: models.StatusUP,
		})
	}

	// 90 ONTs
	for i := 1; i <= 90; i++ {
		devices = append(devices, models.Device{
			ID:     fmt.Sprintf("ont%d", i),
			Type:   models.DeviceTypeONT,
			Status: models.StatusUP,
		})
	}

	// Core interconnect
	links = append(links, models.Link{
		ID:           "link_core1_core2",
		AInterfaceID: "core1-eth0",
		BInterfaceID: "core2-eth0",
		Status:       models.StatusUP,
	})

	// Core → OLT links (4 each)
	for i := 1; i <= 4; i++ {
		links = append(links, models.Link{
			ID:           fmt.Sprintf("link_core1_olt%d", i),
			AInterfaceID: fmt.Sprintf("core1-eth%d", i),
			BInterfaceID: fmt.Sprintf("olt%d-uplink0", i),
			Status:       models.StatusUP,
		})
	}
	for i := 5; i <= 8; i++ {
		links = append(links, models.Link{
			ID:           fmt.Sprintf("link_core2_olt%d", i),
			AInterfaceID: fmt.Sprintf("core2-eth%d", i-4),
			BInterfaceID: fmt.Sprintf("olt%d-uplink0", i),
			Status:       models.StatusUP,
		})
	}

	// OLT → ONT links (~11 per OLT)
	ontIdx := 1
	for oltID := 1; oltID <= 8; oltID++ {
		ontsPerOlt := 11
		if oltID <= 2 {
			ontsPerOlt = 12 // First 2 OLTs get 12
		}

		for portIdx := 0; portIdx < ontsPerOlt && ontIdx <= 90; portIdx++ {
			links = append(links, models.Link{
				ID:           fmt.Sprintf("link_olt%d_ont%d", oltID, ontIdx),
				AInterfaceID: fmt.Sprintf("olt%d-pon%d", oltID, portIdx),
				BInterfaceID: fmt.Sprintf("ont%d-eth0", ontIdx),
				Status:       models.StatusUP,
			})
			ontIdx++
		}
	}

	return buildCongTopologyCache(devices, links)
}

// buildLargeCongTopology creates large test topology (500 devices, ~500 links)
func buildLargeCongTopology() (*models.TopologyCache, *graph.AdjacencyGraph) {
	var devices []models.Device
	var links []models.Link

	// 4 Cores
	for i := 1; i <= 4; i++ {
		devices = append(devices, models.Device{
			ID:     fmt.Sprintf("core%d", i),
			Type:   models.DeviceTypeCoreRouter,
			Status: models.StatusUP,
		})
	}

	// 16 OLTs
	for i := 1; i <= 16; i++ {
		devices = append(devices, models.Device{
			ID:     fmt.Sprintf("olt%d", i),
			Type:   models.DeviceTypeOLT,
			Status: models.StatusUP,
		})
	}

	// 480 ONTs
	for i := 1; i <= 480; i++ {
		devices = append(devices, models.Device{
			ID:     fmt.Sprintf("ont%d", i),
			Type:   models.DeviceTypeONT,
			Status: models.StatusUP,
		})
	}

	// Core mesh (6 links: full mesh of 4 cores)
	coreLinks := [][2]int{{1, 2}, {1, 3}, {1, 4}, {2, 3}, {2, 4}, {3, 4}}
	for _, pair := range coreLinks {
		links = append(links, models.Link{
			ID:           fmt.Sprintf("link_core%d_core%d", pair[0], pair[1]),
			AInterfaceID: fmt.Sprintf("core%d-eth%d", pair[0], pair[1]),
			BInterfaceID: fmt.Sprintf("core%d-eth%d", pair[1], pair[0]),
			Status:       models.StatusUP,
		})
	}

	// Core → OLT links (4 per core)
	for i := 1; i <= 4; i++ {
		for j := 1; j <= 4; j++ {
			oltID := (i-1)*4 + j
			links = append(links, models.Link{
				ID:           fmt.Sprintf("link_core%d_olt%d", i, oltID),
				AInterfaceID: fmt.Sprintf("core%d-eth%d", i, j+10),
				BInterfaceID: fmt.Sprintf("olt%d-uplink0", oltID),
				Status:       models.StatusUP,
			})
		}
	}

	// OLT → ONT links (30 per OLT)
	for oltID := 1; oltID <= 16; oltID++ {
		for portIdx := 1; portIdx <= 30; portIdx++ {
			ontID := (oltID-1)*30 + portIdx
			links = append(links, models.Link{
				ID:           fmt.Sprintf("link_olt%d_ont%d", oltID, ontID),
				AInterfaceID: fmt.Sprintf("olt%d-pon%d", oltID, portIdx),
				BInterfaceID: fmt.Sprintf("ont%d-eth0", ontID),
				Status:       models.StatusUP,
			})
		}
	}

	return buildCongTopologyCache(devices, links)
}

// Helper: buildCongTopologyCache creates cache from devices + links + tariff
func buildCongTopologyCache(devices []models.Device, links []models.Link) (*models.TopologyCache, *graph.AdjacencyGraph) {
	cache := &models.TopologyCache{
		DeviceByID:       make(map[string]*models.Device),
		InterfaceByID:    make(map[string]*models.Interface),
		LinksByInterface: make(map[string][]models.Link),
		LinkByID:         make(map[string]*models.Link),
		TariffByID:       make(map[int64]*models.Tariff),
	}

	// Add devices
	for i := range devices {
		cache.DeviceByID[devices[i].ID] = &devices[i]
	}

	// Create a default tariff for ONTs
	tariff := &models.Tariff{
		ID:          1,
		Name:        "1Gbps",
		MaxUpMbps:   1000,
		MaxDownMbps: 1000,
	}
	cache.TariffByID[1] = tariff

	// Assign tariff to ONTs
	for id, dev := range cache.DeviceByID {
		if dev.IsLeaf() {
			dev.TariffID.Valid = true
			dev.TariffID.Int64 = 1
			cache.DeviceByID[id] = dev
		}
	}

	// Generate interfaces from links
	for _, link := range links {
		if _, exists := cache.InterfaceByID[link.AInterfaceID]; !exists {
			devID := extractDeviceIDFromInterface(link.AInterfaceID)
			cache.InterfaceByID[link.AInterfaceID] = &models.Interface{
				ID:          link.AInterfaceID,
				DeviceID:    devID,
				AdminStatus: models.AdminStatusUP,
			}
		}
		if _, exists := cache.InterfaceByID[link.BInterfaceID]; !exists {
			devID := extractDeviceIDFromInterface(link.BInterfaceID)
			cache.InterfaceByID[link.BInterfaceID] = &models.Interface{
				ID:          link.BInterfaceID,
				DeviceID:    devID,
				AdminStatus: models.AdminStatusUP,
			}
		}
	}

	// Add links
	for i := range links {
		cache.LinksByInterface[links[i].AInterfaceID] = append(cache.LinksByInterface[links[i].AInterfaceID], links[i])
		cache.LinksByInterface[links[i].BInterfaceID] = append(cache.LinksByInterface[links[i].BInterfaceID], links[i])
		cache.LinkByID[links[i].ID] = &links[i]
	}

	adj := graph.BuildAdjacency(cache)
	return cache, adj
}
