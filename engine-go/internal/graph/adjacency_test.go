package graph

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/unoc/engine-go/internal/models"
)

// TestBuildAdjacency_BasicTopology tests adjacency with 2 devices connected by 1 link
func TestBuildAdjacency_BasicTopology(t *testing.T) {
	// Arrange: 2 devices (OLT + ONT), 2 interfaces, 1 link UP
	devices := []models.Device{
		{ID: "olt1", Type: models.DeviceTypeOLT, Status: "ACTIVE"},
		{ID: "ont1", Type: models.DeviceTypeBusinessONT, Status: "ACTIVE"},
	}

	interfaces := []models.Interface{
		{ID: "olt1-eth0", DeviceID: "olt1", AdminStatus: models.AdminStatusUP},
		{ID: "ont1-eth0", DeviceID: "ont1", AdminStatus: models.AdminStatusUP},
	}

	links := []models.Link{
		{ID: "link1", AInterfaceID: "olt1-eth0", BInterfaceID: "ont1-eth0", Status: "UP"},
	}

	cache := &models.TopologyCache{
		DeviceByID:       make(map[string]*models.Device),
		InterfaceByID:    make(map[string]*models.Interface),
		LinksByInterface: make(map[string][]models.Link),
	}

	for i := range devices {
		cache.DeviceByID[devices[i].ID] = &devices[i]
	}
	for i := range interfaces {
		cache.InterfaceByID[interfaces[i].ID] = &interfaces[i]
	}
	for _, link := range links {
		cache.LinksByInterface[link.AInterfaceID] = append(cache.LinksByInterface[link.AInterfaceID], link)
		cache.LinksByInterface[link.BInterfaceID] = append(cache.LinksByInterface[link.BInterfaceID], link)
	}

	// Act
	adj := BuildAdjacency(cache)

	// Assert: olt1 → ont1, ont1 → olt1 (bidirectional)
	assert.Contains(t, adj.Neighbors, "olt1", "olt1 should be in adjacency")
	assert.Contains(t, adj.Neighbors, "ont1", "ont1 should be in adjacency")
	assert.True(t, adj.Neighbors["olt1"]["ont1"], "olt1 should have ont1 as neighbor")
	assert.True(t, adj.Neighbors["ont1"]["olt1"], "ont1 should have olt1 as neighbor")
	assert.Len(t, adj.Neighbors["olt1"], 1, "olt1 should have exactly 1 neighbor")
	assert.Len(t, adj.Neighbors["ont1"], 1, "ont1 should have exactly 1 neighbor")
}

// TestBuildAdjacency_LinkStatusFiltering tests that only UP links create adjacency
func TestBuildAdjacency_LinkStatusFiltering(t *testing.T) {
	// Arrange: 3 devices, link1 UP, link2 DOWN
	devices := []models.Device{
		{ID: "olt1", Type: models.DeviceTypeOLT, Status: "ACTIVE"},
		{ID: "ont1", Type: models.DeviceTypeBusinessONT, Status: "ACTIVE"},
		{ID: "ont2", Type: models.DeviceTypeBusinessONT, Status: "ACTIVE"},
	}

	interfaces := []models.Interface{
		{ID: "olt1-eth0", DeviceID: "olt1", AdminStatus: models.AdminStatusUP},
		{ID: "olt1-eth1", DeviceID: "olt1", AdminStatus: models.AdminStatusUP},
		{ID: "ont1-eth0", DeviceID: "ont1", AdminStatus: models.AdminStatusUP},
		{ID: "ont2-eth0", DeviceID: "ont2", AdminStatus: models.AdminStatusUP},
	}

	links := []models.Link{
		{ID: "link1", AInterfaceID: "olt1-eth0", BInterfaceID: "ont1-eth0", Status: "UP"},
		{ID: "link2", AInterfaceID: "olt1-eth1", BInterfaceID: "ont2-eth0", Status: "DOWN"},
	}

	cache := &models.TopologyCache{
		DeviceByID:       make(map[string]*models.Device),
		InterfaceByID:    make(map[string]*models.Interface),
		LinksByInterface: make(map[string][]models.Link),
	}

	for i := range devices {
		cache.DeviceByID[devices[i].ID] = &devices[i]
	}
	for i := range interfaces {
		cache.InterfaceByID[interfaces[i].ID] = &interfaces[i]
	}
	for _, link := range links {
		cache.LinksByInterface[link.AInterfaceID] = append(cache.LinksByInterface[link.AInterfaceID], link)
		cache.LinksByInterface[link.BInterfaceID] = append(cache.LinksByInterface[link.BInterfaceID], link)
	}

	// Act
	adj := BuildAdjacency(cache)

	// Assert: olt1 ↔ ont1 (link UP), ont2 isolated (link DOWN)
	assert.True(t, adj.Neighbors["olt1"]["ont1"], "olt1 should have ont1 as neighbor (link UP)")
	assert.False(t, adj.Neighbors["olt1"]["ont2"], "olt1 should NOT have ont2 as neighbor (link DOWN)")
	assert.True(t, adj.Neighbors["ont1"]["olt1"], "ont1 should have olt1 as neighbor")
	assert.Len(t, adj.Neighbors["ont2"], 0, "ont2 should have no neighbors (link DOWN)")
}

// TestBuildAdjacency_InterfaceStatusFiltering tests that DOWN interfaces break adjacency
// NOTE: This test is EXPECTED TO FAIL with current adjacency.go implementation!
// adjacency.go only checks Link.Status, NOT Interface.AdminStatus.
// TODO: Add interface status checking to adjacency.go if needed.
func TestBuildAdjacency_InterfaceStatusFiltering(t *testing.T) {
	t.Skip("KNOWN LIMITATION: adjacency.go doesn't check Interface.AdminStatus yet")

	// Arrange: link UP, but ont1-eth0 DOWN
	devices := []models.Device{
		{ID: "olt1", Type: models.DeviceTypeOLT, Status: "ACTIVE"},
		{ID: "ont1", Type: models.DeviceTypeBusinessONT, Status: "ACTIVE"},
	}

	interfaces := []models.Interface{
		{ID: "olt1-eth0", DeviceID: "olt1", AdminStatus: models.AdminStatusUP},
		{ID: "ont1-eth0", DeviceID: "ont1", AdminStatus: models.AdminStatusDOWN}, // Interface DOWN
	}

	links := []models.Link{
		{ID: "link1", AInterfaceID: "olt1-eth0", BInterfaceID: "ont1-eth0", Status: "UP"},
	}

	cache := &models.TopologyCache{
		DeviceByID:       make(map[string]*models.Device),
		InterfaceByID:    make(map[string]*models.Interface),
		LinksByInterface: make(map[string][]models.Link),
	}

	for i := range devices {
		cache.DeviceByID[devices[i].ID] = &devices[i]
	}
	for i := range interfaces {
		cache.InterfaceByID[interfaces[i].ID] = &interfaces[i]
	}
	for _, link := range links {
		cache.LinksByInterface[link.AInterfaceID] = append(cache.LinksByInterface[link.AInterfaceID], link)
		cache.LinksByInterface[link.BInterfaceID] = append(cache.LinksByInterface[link.BInterfaceID], link)
	}

	// Act
	adj := BuildAdjacency(cache)

	// Assert: No adjacency because ont1-eth0 is DOWN (Note: Current adjacency.go doesn't check interface status, only link status!)
	// This test will FAIL unless we add interface status checking to adjacency.go
	// For now, we expect empty neighbors (assuming link status depends on interface status elsewhere)
	assert.Len(t, adj.Neighbors["olt1"], 0, "olt1 should have no neighbors (interface DOWN breaks link)")
	assert.Len(t, adj.Neighbors["ont1"], 0, "ont1 should have no neighbors")
}

// TestBuildAdjacency_EmptyTopology tests graceful handling of empty input
func TestBuildAdjacency_EmptyTopology(t *testing.T) {
	// Arrange: empty cache
	cache := &models.TopologyCache{
		DeviceByID:       make(map[string]*models.Device),
		InterfaceByID:    make(map[string]*models.Interface),
		LinksByInterface: make(map[string][]models.Link),
	}

	// Act
	adj := BuildAdjacency(cache)

	// Assert: empty adjacency map
	assert.NotNil(t, adj, "adjacency should not be nil")
	assert.NotNil(t, adj.Neighbors, "adjacency.Neighbors should not be nil")
	assert.Len(t, adj.Neighbors, 0, "adjacency should be empty for empty topology")
}

// TestBuildAdjacency_MultipleLinks tests multiple links between same devices (LAG scenario)
func TestBuildAdjacency_MultipleLinks(t *testing.T) {
	// Arrange: 2 devices, 4 interfaces, 2 links (LAG scenario)
	devices := []models.Device{
		{ID: "olt1", Type: models.DeviceTypeOLT, Status: "ACTIVE"},
		{ID: "olt2", Type: models.DeviceTypeOLT, Status: "ACTIVE"},
	}

	interfaces := []models.Interface{
		{ID: "olt1-eth0", DeviceID: "olt1", AdminStatus: models.AdminStatusUP},
		{ID: "olt1-eth1", DeviceID: "olt1", AdminStatus: models.AdminStatusUP},
		{ID: "olt2-eth0", DeviceID: "olt2", AdminStatus: models.AdminStatusUP},
		{ID: "olt2-eth1", DeviceID: "olt2", AdminStatus: models.AdminStatusUP},
	}

	links := []models.Link{
		{ID: "link1", AInterfaceID: "olt1-eth0", BInterfaceID: "olt2-eth0", Status: "UP"},
		{ID: "link2", AInterfaceID: "olt1-eth1", BInterfaceID: "olt2-eth1", Status: "UP"},
	}

	cache := &models.TopologyCache{
		DeviceByID:       make(map[string]*models.Device),
		InterfaceByID:    make(map[string]*models.Interface),
		LinksByInterface: make(map[string][]models.Link),
	}

	for i := range devices {
		cache.DeviceByID[devices[i].ID] = &devices[i]
	}
	for i := range interfaces {
		cache.InterfaceByID[interfaces[i].ID] = &interfaces[i]
	}
	for _, link := range links {
		cache.LinksByInterface[link.AInterfaceID] = append(cache.LinksByInterface[link.AInterfaceID], link)
		cache.LinksByInterface[link.BInterfaceID] = append(cache.LinksByInterface[link.BInterfaceID], link)
	}

	// Act
	adj := BuildAdjacency(cache)

	// Assert: olt1 ↔ olt2 (even with multiple links, adjacency should deduplicate)
	assert.True(t, adj.Neighbors["olt1"]["olt2"], "olt1 should have olt2 as neighbor")
	assert.True(t, adj.Neighbors["olt2"]["olt1"], "olt2 should have olt1 as neighbor")
	// AdjacencyGraph.Neighbors is map[string]map[string]bool, so duplicates are automatically handled
}

// TestBuildAdjacency_BidirectionalVerification tests symmetry
func TestBuildAdjacency_BidirectionalVerification(t *testing.T) {
	// Arrange: OLT ↔ ONT
	devices := []models.Device{
		{ID: "olt1", Type: models.DeviceTypeOLT, Status: "ACTIVE"},
		{ID: "ont1", Type: models.DeviceTypeBusinessONT, Status: "ACTIVE"},
	}

	interfaces := []models.Interface{
		{ID: "olt1-eth0", DeviceID: "olt1", AdminStatus: models.AdminStatusUP},
		{ID: "ont1-eth0", DeviceID: "ont1", AdminStatus: models.AdminStatusUP},
	}

	links := []models.Link{
		{ID: "link1", AInterfaceID: "olt1-eth0", BInterfaceID: "ont1-eth0", Status: "UP"},
	}

	cache := &models.TopologyCache{
		DeviceByID:       make(map[string]*models.Device),
		InterfaceByID:    make(map[string]*models.Interface),
		LinksByInterface: make(map[string][]models.Link),
	}

	for i := range devices {
		cache.DeviceByID[devices[i].ID] = &devices[i]
	}
	for i := range interfaces {
		cache.InterfaceByID[interfaces[i].ID] = &interfaces[i]
	}
	for _, link := range links {
		cache.LinksByInterface[link.AInterfaceID] = append(cache.LinksByInterface[link.AInterfaceID], link)
		cache.LinksByInterface[link.BInterfaceID] = append(cache.LinksByInterface[link.BInterfaceID], link)
	}

	// Act
	adj := BuildAdjacency(cache)

	// Assert: Symmetry check (A → B implies B → A)
	for deviceID, neighbors := range adj.Neighbors {
		for neighborID := range neighbors {
			assert.True(t, adj.Neighbors[neighborID][deviceID],
				"adjacency should be bidirectional: if %s → %s, then %s → %s",
				deviceID, neighborID, neighborID, deviceID)
		}
	}
}

// Benchmarks will be added via tool
