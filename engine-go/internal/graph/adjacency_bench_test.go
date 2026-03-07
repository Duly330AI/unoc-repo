package graph

import (
	"fmt"
	"testing"

	"github.com/unoc/engine-go/internal/models"
)

// ========================================
// BENCHMARKS - Adjacency Graph
// ========================================

// BenchmarkBuildAdjacency_Small benchmarks adjacency graph construction for small topology (5 devices, 4 links)
func BenchmarkBuildAdjacency_Small(b *testing.B) {
	cache := buildSmallTopologyCache()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = BuildAdjacency(cache)
	}
}

// BenchmarkBuildAdjacency_Medium benchmarks adjacency graph construction for medium topology (50 devices, 49 links)
func BenchmarkBuildAdjacency_Medium(b *testing.B) {
	cache := buildMediumTopologyCache()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = BuildAdjacency(cache)
	}
}

// BenchmarkBuildAdjacency_Large benchmarks adjacency graph construction for large topology (200 devices, 198 links)
func BenchmarkBuildAdjacency_Large(b *testing.B) {
	cache := buildLargeTopologyCache()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = BuildAdjacency(cache)
	}
}

// Helper: buildSmallTopologyCache creates 5-device topology (1 core, 1 olt, 3 onts)
func buildSmallTopologyCache() *models.TopologyCache {
	devices := []models.Device{
		{ID: "core1", Type: models.DeviceTypeCoreRouter, Status: models.StatusUP},
		{ID: "olt1", Type: models.DeviceTypeOLT, Status: models.StatusUP},
		{ID: "ont1", Type: models.DeviceTypeONT, Status: models.StatusUP},
		{ID: "ont2", Type: models.DeviceTypeONT, Status: models.StatusUP},
		{ID: "ont3", Type: models.DeviceTypeONT, Status: models.StatusUP},
	}

	links := []models.Link{
		{ID: "link1", AInterfaceID: "ont1-eth0", BInterfaceID: "olt1-eth0", Status: models.StatusUP},
		{ID: "link2", AInterfaceID: "ont2-eth0", BInterfaceID: "olt1-eth1", Status: models.StatusUP},
		{ID: "link3", AInterfaceID: "ont3-eth0", BInterfaceID: "olt1-eth2", Status: models.StatusUP},
		{ID: "link4", AInterfaceID: "olt1-eth10", BInterfaceID: "core1-eth0", Status: models.StatusUP},
	}

	return buildTestTopologyCache(devices, links)
}

// Helper: buildMediumTopologyCache creates 50-device topology (1 core, 4 olts, 45 onts)
func buildMediumTopologyCache() *models.TopologyCache {
	devices := []models.Device{
		{ID: "core1", Type: models.DeviceTypeCoreRouter, Status: models.StatusUP},
	}

	// 4 OLTs
	for i := 1; i <= 4; i++ {
		devices = append(devices, models.Device{
			ID:     fmt.Sprintf("olt%d", i),
			Type:   models.DeviceTypeOLT,
			Status: models.StatusUP,
		})
	}

	// 45 ONTs
	for i := 1; i <= 45; i++ {
		devices = append(devices, models.Device{
			ID:     fmt.Sprintf("ont%d", i),
			Type:   models.DeviceTypeONT,
			Status: models.StatusUP,
		})
	}

	var links []models.Link

	// Connect OLTs to core
	for i := 1; i <= 4; i++ {
		links = append(links, models.Link{
			ID:           fmt.Sprintf("link_olt%d_core", i),
			AInterfaceID: fmt.Sprintf("olt%d-eth10", i),
			BInterfaceID: fmt.Sprintf("core1-eth%d", i),
			Status:       models.StatusUP,
		})
	}

	// Connect ONTs to OLTs (distribute evenly: ~11 ONTs per OLT)
	ontIdx := 1
	for oltID := 1; oltID <= 4; oltID++ {
		ontsPerOlt := 11
		if oltID == 4 {
			ontsPerOlt = 12 // Last OLT gets 12 ONTs (45/4 = 11.25)
		}

		for portIdx := 0; portIdx < ontsPerOlt; portIdx++ {
			links = append(links, models.Link{
				ID:           fmt.Sprintf("link_ont%d_olt%d", ontIdx, oltID),
				AInterfaceID: fmt.Sprintf("ont%d-eth0", ontIdx),
				BInterfaceID: fmt.Sprintf("olt%d-eth%d", oltID, portIdx),
				Status:       models.StatusUP,
			})
			ontIdx++
		}
	}

	return buildTestTopologyCache(devices, links)
}

// Helper: buildLargeTopologyCache creates 200-device topology (2 cores, 8 olts, 190 onts)
func buildLargeTopologyCache() *models.TopologyCache {
	devices := []models.Device{
		{ID: "core1", Type: models.DeviceTypeCoreRouter, Status: models.StatusUP},
		{ID: "core2", Type: models.DeviceTypeCoreRouter, Status: models.StatusUP},
	}

	// 8 OLTs
	for i := 1; i <= 8; i++ {
		devices = append(devices, models.Device{
			ID:     fmt.Sprintf("olt%d", i),
			Type:   models.DeviceTypeOLT,
			Status: models.StatusUP,
		})
	}

	// 190 ONTs
	for i := 1; i <= 190; i++ {
		devices = append(devices, models.Device{
			ID:     fmt.Sprintf("ont%d", i),
			Type:   models.DeviceTypeONT,
			Status: models.StatusUP,
		})
	}

	var links []models.Link

	// Connect OLTs to cores (redundant links, alternating)
	for i := 1; i <= 8; i++ {
		coreID := 1 + (i % 2) // Alternate between core1 and core2
		links = append(links, models.Link{
			ID:           fmt.Sprintf("link_olt%d_core%d", i, coreID),
			AInterfaceID: fmt.Sprintf("olt%d-eth10", i),
			BInterfaceID: fmt.Sprintf("core%d-eth%d", coreID, i),
			Status:       models.StatusUP,
		})
	}

	// Connect ONTs to OLTs (23-24 ONTs per OLT)
	ontIdx := 1
	for oltID := 1; oltID <= 8; oltID++ {
		ontsPerOlt := 23
		if oltID <= 6 {
			ontsPerOlt = 24 // First 6 OLTs get 24 ONTs each
		}

		for portIdx := 0; portIdx < ontsPerOlt; portIdx++ {
			links = append(links, models.Link{
				ID:           fmt.Sprintf("link_ont%d_olt%d", ontIdx, oltID),
				AInterfaceID: fmt.Sprintf("ont%d-eth0", ontIdx),
				BInterfaceID: fmt.Sprintf("olt%d-eth%d", oltID, portIdx),
				Status:       models.StatusUP,
			})
			ontIdx++
		}
	}

	return buildTestTopologyCache(devices, links)
}

// Helper: buildTestTopologyCache creates cache from devices + links
func buildTestTopologyCache(devices []models.Device, links []models.Link) *models.TopologyCache {
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

	return cache
}

// Helper: extractDeviceIDFromInterface extracts device ID from interface ID
// Example: "ont1-eth0" → "ont1"
func extractDeviceIDFromInterface(interfaceID string) string {
	for i, c := range interfaceID {
		if c == '-' {
			return interfaceID[:i]
		}
	}
	return interfaceID
}
