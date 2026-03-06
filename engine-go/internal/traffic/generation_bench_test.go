package traffic

import (
	"database/sql"
	"fmt"
	"testing"

	"github.com/unoc/engine-go/internal/graph"
	"github.com/unoc/engine-go/internal/models"
)

// ========================================
// BENCHMARKS - Traffic Generation
// ========================================

// BenchmarkGenerateFlows_Small benchmarks traffic generation for small topology (1 ONT)
func BenchmarkGenerateFlows_Small(b *testing.B) {
	cache, adj := buildSmallGenTopology()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = GenerateFlows(cache, adj, 1, 42)
	}
}

// BenchmarkGenerateFlows_Medium benchmarks traffic generation for medium topology (50 ONTs)
func BenchmarkGenerateFlows_Medium(b *testing.B) {
	cache, adj := buildMediumGenTopology()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = GenerateFlows(cache, adj, 1, 42)
	}
}

// BenchmarkGenerateFlows_Large benchmarks traffic generation for large topology (200 ONTs)
func BenchmarkGenerateFlows_Large(b *testing.B) {
	cache, adj := buildLargeGenTopology()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = GenerateFlows(cache, adj, 1, 42)
	}
}

// Helper: buildSmallGenTopology creates 1-ONT topology (1 core, 1 olt, 1 ont)
func buildSmallGenTopology() (*models.TopologyCache, *graph.AdjacencyGraph) {
	devices := []models.Device{
		{ID: "core1", Type: models.DeviceTypeCoreRouter, Status: models.StatusUP},
		{ID: "olt1", Type: models.DeviceTypeOLT, Status: models.StatusUP},
		{ID: "ont1", Type: models.DeviceTypeONT, Status: models.StatusUP, TariffID: sql.NullInt64{Int64: 1, Valid: true}},
	}

	links := []models.Link{
		{ID: "link1", AInterfaceID: "ont1-eth0", BInterfaceID: "olt1-eth0", Status: models.StatusUP},
		{ID: "link2", AInterfaceID: "olt1-eth10", BInterfaceID: "core1-eth0", Status: models.StatusUP},
	}

	tariff := &models.Tariff{
		ID:          1,
		Name:        "GPON-100",
		MaxDownMbps: 100.0,
		MaxUpMbps:   50.0,
		Technology:  sql.NullString{String: "GPON", Valid: true},
	}

	cache := buildGenTestTopologyCache(devices, links, []*models.Tariff{tariff})
	adj := graph.BuildAdjacency(cache)
	return cache, adj
}

// Helper: buildMediumGenTopology creates 50-ONT topology (1 core, 4 olts, 50 onts)
func buildMediumGenTopology() (*models.TopologyCache, *graph.AdjacencyGraph) {
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

	// 50 ONTs
	for i := 1; i <= 50; i++ {
		devices = append(devices, models.Device{
			ID:       fmt.Sprintf("ont%d", i),
			Type:     models.DeviceTypeONT,
			Status:   models.StatusUP,
			TariffID: sql.NullInt64{Int64: 1, Valid: true},
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

	// Connect ONTs to OLTs (12-13 ONTs per OLT)
	ontIdx := 1
	for oltID := 1; oltID <= 4; oltID++ {
		ontsPerOlt := 12
		if oltID == 4 {
			ontsPerOlt = 14 // Last OLT gets 14 ONTs (50/4 = 12.5)
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

	tariff := &models.Tariff{
		ID:          1,
		Name:        "GPON-100",
		MaxDownMbps: 100.0,
		MaxUpMbps:   50.0,
		Technology:  sql.NullString{String: "GPON", Valid: true},
	}

	cache := buildGenTestTopologyCache(devices, links, []*models.Tariff{tariff})
	adj := graph.BuildAdjacency(cache)
	return cache, adj
}

// Helper: buildLargeGenTopology creates 200-ONT topology (2 cores, 8 olts, 200 onts)
func buildLargeGenTopology() (*models.TopologyCache, *graph.AdjacencyGraph) {
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

	// 200 ONTs
	for i := 1; i <= 200; i++ {
		devices = append(devices, models.Device{
			ID:       fmt.Sprintf("ont%d", i),
			Type:     models.DeviceTypeONT,
			Status:   models.StatusUP,
			TariffID: sql.NullInt64{Int64: 1, Valid: true},
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

	// Connect ONTs to OLTs (25 ONTs per OLT)
	ontIdx := 1
	for oltID := 1; oltID <= 8; oltID++ {
		for portIdx := 0; portIdx < 25; portIdx++ {
			links = append(links, models.Link{
				ID:           fmt.Sprintf("link_ont%d_olt%d", ontIdx, oltID),
				AInterfaceID: fmt.Sprintf("ont%d-eth0", ontIdx),
				BInterfaceID: fmt.Sprintf("olt%d-eth%d", oltID, portIdx),
				Status:       models.StatusUP,
			})
			ontIdx++
		}
	}

	tariff := &models.Tariff{
		ID:          1,
		Name:        "GPON-100",
		MaxDownMbps: 100.0,
		MaxUpMbps:   50.0,
		Technology:  sql.NullString{String: "GPON", Valid: true},
	}

	cache := buildGenTestTopologyCache(devices, links, []*models.Tariff{tariff})
	adj := graph.BuildAdjacency(cache)
	return cache, adj
}

// Helper: buildGenTestTopologyCache creates cache from devices + links + tariffs
func buildGenTestTopologyCache(devices []models.Device, links []models.Link, tariffs []*models.Tariff) *models.TopologyCache {
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

	// Add tariffs
	for _, tariff := range tariffs {
		cache.TariffByID[tariff.ID] = tariff
	}

	// Generate interfaces from links
	for _, link := range links {
		if _, exists := cache.InterfaceByID[link.AInterfaceID]; !exists {
			devID := extractDevIDFromIfaceID(link.AInterfaceID)
			cache.InterfaceByID[link.AInterfaceID] = &models.Interface{
				ID:          link.AInterfaceID,
				DeviceID:    devID,
				AdminStatus: models.AdminStatusUP,
			}
		}
		if _, exists := cache.InterfaceByID[link.BInterfaceID]; !exists {
			devID := extractDevIDFromIfaceID(link.BInterfaceID)
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

// Helper: extractDevIDFromIfaceID extracts device ID from interface ID
// Example: "ont1-eth0" → "ont1"
func extractDevIDFromIfaceID(interfaceID string) string {
	for i, c := range interfaceID {
		if c == '-' {
			return interfaceID[:i]
		}
	}
	return interfaceID
}

// Helper: intPtr returns pointer to int64
func intPtr(i int64) *int64 {
	return &i
}
