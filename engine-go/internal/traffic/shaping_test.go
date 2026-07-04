package traffic

import (
	"database/sql"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/unoc/engine-go/internal/graph"
	"github.com/unoc/engine-go/internal/models"
)

// deliveryEpsilonBps tolerates float rounding when comparing delivered sums
// against link capacity. The invariant is delivered <= capacity + epsilon.
const deliveryEpsilonBps = 1.0

func TestShapingEnabledFromEnv(t *testing.T) {
	cases := []struct {
		value   string
		enabled bool
	}{
		{"", true},
		{"true", true},
		{"1", true},
		{"yes", true},
		{"anything", true},
		{"false", false},
		{"FALSE", false},
		{" False ", false},
		{"0", false},
		{"no", false},
		{"off", false},
		{"OFF", false},
	}
	for _, tc := range cases {
		t.Run("value="+tc.value, func(t *testing.T) {
			t.Setenv(ShapingEnabledEnvVar, tc.value)
			assert.Equal(t, tc.enabled, ShapingEnabledFromEnv())
		})
	}
}

func TestShapeFlows_NoBottleneckKeepsScalesAtOne(t *testing.T) {
	// 2 ONTs x (100 up / 100 down) over 1000 Mbps links: no direction can
	// exceed capacity, so delivered must equal demand.
	cache, adjacency := buildSharedUplinkTopology(t, 2, 100, 100, 1000)

	result := GenerateFlowsWithShaping(cache, adjacency, 1, 42, true)

	require.Equal(t, 2, result.LeavesCount)
	assert.True(t, result.ShapingEnabled)
	for leafID, shaping := range result.LeafShaping {
		assert.Equal(t, 1.0, shaping.ScaleUp, "leaf %s up scale", leafID)
		assert.Equal(t, 1.0, shaping.ScaleDown, "leaf %s down scale", leafID)
		assert.False(t, shaping.Throttled, "leaf %s must not be throttled", leafID)
	}
	for devID, delivered := range result.DeviceMetrics {
		demand := result.DeviceDemand[devID]
		require.NotNil(t, demand)
		assert.Equal(t, demand.UpBps, delivered.UpBps, "device %s up", devID)
		assert.Equal(t, demand.DownBps, delivered.DownBps, "device %s down", devID)
	}
	assertLinkDeliveryWithinCapacity(t, result, cache)
}

func TestShapeFlows_SingleBottleneckProportionalDownscaling(t *testing.T) {
	// 3 ONTs x 500 Mbps down demand share a 1000 Mbps uplink: total down
	// demand is 1200-1500 Mbps, so every flow must be scaled by the same
	// ratio and the delivered sum must land on the capacity.
	cache, adjacency := buildSharedUplinkTopology(t, 3, 100, 500, 1000)

	result := GenerateFlowsWithShaping(cache, adjacency, 1, 42, true)

	require.Equal(t, 3, result.LeavesCount)
	uplink := result.LinkMetrics["uplink-olt1-core1"]
	require.NotNil(t, uplink)
	uplinkDemand := result.LinkDemand["uplink-olt1-core1"]
	require.NotNil(t, uplinkDemand)

	capBps := 1000.0 * 1_000_000
	assert.Greater(t, uplinkDemand.DownBps, capBps, "scenario must be overbooked downstream")
	assert.LessOrEqual(t, uplink.DownBps, capBps+deliveryEpsilonBps, "delivered downstream sum must respect capacity")
	assert.InDelta(t, capBps, uplink.DownBps, capBps*0.001, "proportional shaping should fill the bottleneck")

	// Proportionality: all flows cross the same single bottleneck, so all
	// down scales are identical and delivered stays proportional to demand.
	var expectedScale float64
	for leafID, shaping := range result.LeafShaping {
		require.NotNil(t, shaping)
		assert.Less(t, shaping.ScaleDown, 1.0, "leaf %s must be downscaled", leafID)
		assert.Equal(t, 1.0, shaping.ScaleUp, "upstream is not overbooked for leaf %s", leafID)
		assert.True(t, shaping.Throttled, "leaf %s must be throttled", leafID)
		if expectedScale == 0 {
			expectedScale = shaping.ScaleDown
		} else {
			assert.InDelta(t, expectedScale, shaping.ScaleDown, 1e-9, "equal proportional scale for leaf %s", leafID)
		}
		demand := result.DeviceDemand[leafID]
		delivered := result.DeviceMetrics[leafID]
		require.NotNil(t, demand)
		require.NotNil(t, delivered)
		assert.InDelta(t, demand.DownBps*shaping.ScaleDown, delivered.DownBps, deliveryEpsilonBps, "delivered = demand * scale for leaf %s", leafID)
		assert.Greater(t, demand.DownBps, delivered.DownBps, "leaf %s requested > delivered", leafID)
	}
	assertLinkDeliveryWithinCapacity(t, result, cache)
}

func TestShapeFlows_DirectionalShapingIsIndependent(t *testing.T) {
	// Upstream-heavy tariff: 3 x 500 Mbps up vs 1000 Mbps capacity, while
	// downstream (3 x 100 Mbps) stays under capacity. Only up may shrink.
	cache, adjacency := buildSharedUplinkTopology(t, 3, 500, 100, 1000)

	result := GenerateFlowsWithShaping(cache, adjacency, 1, 42, true)

	for leafID, shaping := range result.LeafShaping {
		assert.Less(t, shaping.ScaleUp, 1.0, "leaf %s upstream must be downscaled", leafID)
		assert.Equal(t, 1.0, shaping.ScaleDown, "leaf %s downstream must stay unscaled", leafID)
		assert.True(t, shaping.Throttled, leafID)
	}
	assertLinkDeliveryWithinCapacity(t, result, cache)
}

func TestShapeFlows_MultipleBottlenecksNeverOverdeliver(t *testing.T) {
	// Two bottlenecks in series for group 1 (ont1-3 via olt1), while group 2
	// (ont4-5 via olt2) crosses only the shared edge->core link:
	//   z-uplink-olt1-edge1: 600 Mbps (group 1 only, sorted LAST)
	//   b-uplink-edge1-core1: 1500 Mbps (all flows, sorted FIRST)
	// Sorted processing shapes the shared link first, then the tighter olt1
	// uplink again; group 1 flows are scaled twice (conservative), and no
	// link may ever exceed its capacity.
	devices := []models.Device{
		{ID: "core1", Type: models.DeviceTypeCoreRouter, Status: models.StatusUP, Provisioned: true},
		{ID: "edge1", Type: models.DeviceTypeEdgeRouter, Status: models.StatusUP, Provisioned: true},
		{ID: "olt1", Type: models.DeviceTypeOLT, Status: models.StatusUP, Provisioned: true},
		{ID: "olt2", Type: models.DeviceTypeOLT, Status: models.StatusUP, Provisioned: true},
	}
	interfaces := []models.Interface{
		{ID: "olt1-uplink0", DeviceID: "olt1", Name: "uplink0", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 600, Valid: true}},
		{ID: "edge1-eth-olt1", DeviceID: "edge1", Name: "eth-olt1", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 600, Valid: true}},
		{ID: "olt2-uplink0", DeviceID: "olt2", Name: "uplink0", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 5000, Valid: true}},
		{ID: "edge1-eth-olt2", DeviceID: "edge1", Name: "eth-olt2", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 5000, Valid: true}},
		{ID: "edge1-uplink0", DeviceID: "edge1", Name: "uplink0", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 1500, Valid: true}},
		{ID: "core1-eth0", DeviceID: "core1", Name: "eth0", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 1500, Valid: true}},
	}
	links := []models.Link{
		{ID: "z-uplink-olt1-edge1", AInterfaceID: "olt1-uplink0", BInterfaceID: "edge1-eth-olt1", Status: models.StatusUP},
		{ID: "m-uplink-olt2-edge1", AInterfaceID: "olt2-uplink0", BInterfaceID: "edge1-eth-olt2", Status: models.StatusUP},
		{ID: "b-uplink-edge1-core1", AInterfaceID: "edge1-uplink0", BInterfaceID: "core1-eth0", Status: models.StatusUP},
	}
	tariffs := []models.Tariff{{ID: 1, MaxUpMbps: 50, MaxDownMbps: 500}}

	group1 := []string{"ont1", "ont2", "ont3"}
	group2 := []string{"ont4", "ont5"}
	for _, ontID := range group1 {
		devices, interfaces, links = attachLeaf(devices, interfaces, links, ontID, "olt1")
	}
	for _, ontID := range group2 {
		devices, interfaces, links = attachLeaf(devices, interfaces, links, ontID, "olt2")
	}

	cache := models.BuildTopologyCacheWithCatalog(devices, links, interfaces, tariffs, nil, nil)
	adjacency := graph.BuildAdjacency(cache)

	result := GenerateFlowsWithShaping(cache, adjacency, 1, 42, true)
	require.Equal(t, 5, result.LeavesCount)

	assertLinkDeliveryWithinCapacity(t, result, cache)

	// Group 1 crossed both bottlenecks and must be scaled harder than group 2.
	for _, g1 := range group1 {
		require.NotNil(t, result.LeafShaping[g1])
		assert.True(t, result.LeafShaping[g1].Throttled, "group1 leaf %s throttled", g1)
		for _, g2 := range group2 {
			require.NotNil(t, result.LeafShaping[g2])
			assert.Less(t, result.LeafShaping[g1].ScaleDown, result.LeafShaping[g2].ScaleDown,
				"double-bottleneck leaf %s must be scaled below single-bottleneck leaf %s", g1, g2)
		}
	}

	// The tighter olt1 uplink is the binding constraint for group 1.
	olt1Uplink := result.LinkMetrics["z-uplink-olt1-edge1"]
	require.NotNil(t, olt1Uplink)
	assert.LessOrEqual(t, olt1Uplink.DownBps, 600.0*1_000_000+deliveryEpsilonBps)

	// Conservative under-delivery on the shared link is acceptable (group 1
	// was shaped twice); over-delivery is not.
	shared := result.LinkMetrics["b-uplink-edge1-core1"]
	require.NotNil(t, shared)
	assert.LessOrEqual(t, shared.DownBps, 1500.0*1_000_000+deliveryEpsilonBps)
}

func TestGenerateFlowsWithShaping_DisabledMatchesUnshapedDemand(t *testing.T) {
	// Same overbooked scenario as the single-bottleneck test, but with the
	// flag off: delivered must equal demand (B1 behavior) while the new
	// requested fields stay populated.
	cache, adjacency := buildSharedUplinkTopology(t, 3, 100, 500, 1000)

	result := GenerateFlowsWithShaping(cache, adjacency, 1, 42, false)

	require.Equal(t, 3, result.LeavesCount)
	assert.False(t, result.ShapingEnabled)
	for leafID, shaping := range result.LeafShaping {
		assert.Equal(t, 1.0, shaping.ScaleUp, leafID)
		assert.Equal(t, 1.0, shaping.ScaleDown, leafID)
		assert.False(t, shaping.Throttled, leafID)
	}
	for devID, delivered := range result.DeviceMetrics {
		demand := result.DeviceDemand[devID]
		require.NotNil(t, demand, devID)
		assert.Equal(t, demand.UpBps, delivered.UpBps, devID)
		assert.Equal(t, demand.DownBps, delivered.DownBps, devID)
	}

	// The overbooked uplink is delivered above capacity: exactly the B1
	// visibility behavior (congestion flags it; nothing is reduced).
	uplink := result.LinkMetrics["uplink-olt1-core1"]
	require.NotNil(t, uplink)
	assert.Greater(t, uplink.DownBps, 1000.0*1_000_000)
}

func TestGenerateFlows_EnvFlagDisablesShaping(t *testing.T) {
	t.Setenv(ShapingEnabledEnvVar, "false")
	cache, adjacency := buildSharedUplinkTopology(t, 3, 100, 500, 1000)

	result := GenerateFlows(cache, adjacency, 1, 42)

	assert.False(t, result.ShapingEnabled)
	uplink := result.LinkMetrics["uplink-olt1-core1"]
	require.NotNil(t, uplink)
	assert.Greater(t, uplink.DownBps, 1000.0*1_000_000, "flag off must not shape")

	t.Setenv(ShapingEnabledEnvVar, "true")
	result = GenerateFlows(cache, adjacency, 1, 42)
	assert.True(t, result.ShapingEnabled)
	uplink = result.LinkMetrics["uplink-olt1-core1"]
	require.NotNil(t, uplink)
	assert.LessOrEqual(t, uplink.DownBps, 1000.0*1_000_000+deliveryEpsilonBps, "flag on must shape")
}

func TestDetectCongestion_ThrottledLeafBecomesCongested(t *testing.T) {
	// ont1-3 share an overbooked 1000 Mbps uplink via olt1 (throttled);
	// ont9 sits on olt9 with a 10G uplink (unthrottled, full tariff demand).
	devices := []models.Device{
		{ID: "core1", Type: models.DeviceTypeCoreRouter, Status: models.StatusUP, Provisioned: true},
		{ID: "olt1", Type: models.DeviceTypeOLT, Status: models.StatusUP, Provisioned: true},
		{ID: "olt9", Type: models.DeviceTypeOLT, Status: models.StatusUP, Provisioned: true},
	}
	interfaces := []models.Interface{
		{ID: "olt1-uplink0", DeviceID: "olt1", Name: "uplink0", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 1000, Valid: true}},
		{ID: "core1-eth0", DeviceID: "core1", Name: "eth0", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 1000, Valid: true}},
		{ID: "olt9-uplink0", DeviceID: "olt9", Name: "uplink0", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 10_000, Valid: true}},
		{ID: "core1-eth9", DeviceID: "core1", Name: "eth9", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 10_000, Valid: true}},
	}
	links := []models.Link{
		{ID: "uplink-olt1-core1", AInterfaceID: "olt1-uplink0", BInterfaceID: "core1-eth0", Status: models.StatusUP},
		{ID: "uplink-olt9-core1", AInterfaceID: "olt9-uplink0", BInterfaceID: "core1-eth9", Status: models.StatusUP},
	}
	tariffs := []models.Tariff{{ID: 1, MaxUpMbps: 100, MaxDownMbps: 500}}
	for _, ontID := range []string{"ont1", "ont2", "ont3"} {
		devices, interfaces, links = attachLeaf(devices, interfaces, links, ontID, "olt1")
	}
	devices, interfaces, links = attachLeaf(devices, interfaces, links, "ont9", "olt9")

	cache := models.BuildTopologyCacheWithCatalog(devices, links, interfaces, tariffs, nil, nil)
	adjacency := graph.BuildAdjacency(cache)

	result := GenerateFlowsWithShaping(cache, adjacency, 1, 42, true)
	require.Equal(t, 4, result.LeavesCount)
	require.True(t, result.LeafShaping["ont1"].Throttled)
	require.False(t, result.LeafShaping["ont9"].Throttled)

	state := DetectCongestion(result, cache, NewCongestionState())

	assert.True(t, state.DeviceCongested["ont1"], "throttled leaf must be congested")
	assert.True(t, state.DeviceCongested["ont2"], "throttled leaf must be congested")
	assert.True(t, state.DeviceCongested["ont3"], "throttled leaf must be congested")
	assert.False(t, state.DeviceCongested["ont9"], "unthrottled leaf must stay uncongested despite full tariff demand")
	assert.True(t, state.LinkCongested["uplink-olt1-core1"], "shaped bottleneck link stays congested (delivered at capacity)")
}

func TestGenerateFlowsWithShaping_DownLeafStillGeneratesNoTraffic(t *testing.T) {
	// HGO-007 regression under the B2 flow refactor: a DOWN leaf produces no
	// flow, no demand, and no shaping entry.
	cache, adjacency := buildSharedUplinkTopology(t, 3, 100, 500, 1000)
	cache.DeviceByID["ont1"].Status = models.StatusDOWN

	result := GenerateFlowsWithShaping(cache, adjacency, 1, 42, true)

	assert.Equal(t, 2, result.LeavesCount)
	assert.Nil(t, result.DeviceMetrics["ont1"])
	assert.Nil(t, result.DeviceDemand["ont1"])
	assert.Nil(t, result.LeafShaping["ont1"])
	assertLinkDeliveryWithinCapacity(t, result, cache)
}

func TestGenerateFlowsWithShaping_Deterministic(t *testing.T) {
	cache, adjacency := buildSharedUplinkTopology(t, 3, 100, 500, 1000)

	first := GenerateFlowsWithShaping(cache, adjacency, 7, 4242, true)
	second := GenerateFlowsWithShaping(cache, adjacency, 7, 4242, true)

	require.Equal(t, first.LeavesCount, second.LeavesCount)
	require.Equal(t, len(first.DeviceMetrics), len(second.DeviceMetrics))
	for devID, m1 := range first.DeviceMetrics {
		m2 := second.DeviceMetrics[devID]
		require.NotNil(t, m2, devID)
		assert.Equal(t, m1.UpBps, m2.UpBps, devID)
		assert.Equal(t, m1.DownBps, m2.DownBps, devID)
	}
	for linkID, m1 := range first.LinkMetrics {
		m2 := second.LinkMetrics[linkID]
		require.NotNil(t, m2, linkID)
		assert.Equal(t, m1.UpBps, m2.UpBps, linkID)
		assert.Equal(t, m1.DownBps, m2.DownBps, linkID)
	}
	for leafID, s1 := range first.LeafShaping {
		s2 := second.LeafShaping[leafID]
		require.NotNil(t, s2, leafID)
		assert.Equal(t, s1.ScaleUp, s2.ScaleUp, leafID)
		assert.Equal(t, s1.ScaleDown, s2.ScaleDown, leafID)
		assert.Equal(t, s1.Throttled, s2.Throttled, leafID)
	}
}

// assertLinkDeliveryWithinCapacity enforces the core B2 invariant: for every
// link with known capacity, delivered traffic per direction must not exceed
// capacity (+ float epsilon).
func assertLinkDeliveryWithinCapacity(t *testing.T, result *GenerationResult, cache *models.TopologyCache) {
	t.Helper()
	for linkID, metrics := range result.LinkMetrics {
		capBps := EffectiveLinkCapacityMbps(cache.LinkByID[linkID], cache) * 1_000_000
		if capBps <= 0 {
			continue
		}
		assert.LessOrEqual(t, metrics.UpBps, capBps+deliveryEpsilonBps, "link %s upstream delivered <= capacity", linkID)
		assert.LessOrEqual(t, metrics.DownBps, capBps+deliveryEpsilonBps, "link %s downstream delivered <= capacity", linkID)
	}
}

// buildSharedUplinkTopology creates leafCount ONTs on olt1 with one shared
// uplink (uplinkCapacityMbps) to core1. Access links use default capacities
// large enough not to interfere.
func buildSharedUplinkTopology(
	t *testing.T,
	leafCount int,
	tariffUpMbps float64,
	tariffDownMbps float64,
	uplinkCapacityMbps int64,
) (*models.TopologyCache, *graph.AdjacencyGraph) {
	t.Helper()
	devices := []models.Device{
		{ID: "core1", Type: models.DeviceTypeCoreRouter, Status: models.StatusUP, Provisioned: true},
		{ID: "olt1", Type: models.DeviceTypeOLT, Status: models.StatusUP, Provisioned: true},
	}
	interfaces := []models.Interface{
		{ID: "olt1-uplink0", DeviceID: "olt1", Name: "uplink0", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: uplinkCapacityMbps, Valid: true}},
		{ID: "core1-eth0", DeviceID: "core1", Name: "eth0", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: uplinkCapacityMbps, Valid: true}},
	}
	links := []models.Link{
		{ID: "uplink-olt1-core1", AInterfaceID: "olt1-uplink0", BInterfaceID: "core1-eth0", Status: models.StatusUP},
	}
	tariffs := []models.Tariff{{ID: 1, MaxUpMbps: tariffUpMbps, MaxDownMbps: tariffDownMbps}}

	for i := 1; i <= leafCount; i++ {
		ontID := "ont" + string(rune('0'+i))
		devices, interfaces, links = attachLeaf(devices, interfaces, links, ontID, "olt1")
	}

	cache := models.BuildTopologyCacheWithCatalog(devices, links, interfaces, tariffs, nil, nil)
	return cache, graph.BuildAdjacency(cache)
}

// attachLeaf wires a provisioned UP BUSINESS_ONT with tariff 1 to the given
// parent device via a dedicated access link with ample capacity.
func attachLeaf(
	devices []models.Device,
	interfaces []models.Interface,
	links []models.Link,
	ontID string,
	parentID string,
) ([]models.Device, []models.Interface, []models.Link) {
	devices = append(devices, models.Device{
		ID:          ontID,
		Type:        models.DeviceTypeBusinessONT,
		Status:      models.StatusUP,
		Provisioned: true,
		TariffID:    sql.NullInt64{Int64: 1, Valid: true},
	})
	interfaces = append(interfaces,
		models.Interface{ID: ontID + "-eth0", DeviceID: ontID, Name: "eth0", AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 100_000, Valid: true}},
		models.Interface{ID: parentID + "-pon-" + ontID, DeviceID: parentID, Name: "pon-" + ontID, AdminStatus: models.AdminStatusUP, Capacity: sql.NullInt64{Int64: 100_000, Valid: true}},
	)
	links = append(links, models.Link{
		ID:           "access-" + ontID,
		AInterfaceID: ontID + "-eth0",
		BInterfaceID: parentID + "-pon-" + ontID,
		Status:       models.StatusUP,
	})
	return devices, interfaces, links
}
