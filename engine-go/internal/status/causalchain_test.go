package status

import (
	"context"
	"fmt"
	"testing"
)

// Helper function to create a test device
func makeTestDevice(id string, typ DeviceType, role DeviceRole, status DeviceStatus, provisioned bool) *DeviceRecord {
	return &DeviceRecord{
		ID:          id,
		Type:        typ,
		Role:        role,
		Status:      status,
		Provisioned: provisioned,
	}
}

// Helper function to create a test link
func makeTestLink(id, aDevice, bDevice string, status DeviceStatus, viable bool) *LinkRecord {
	return &LinkRecord{
		ID:               id,
		ADeviceID:        aDevice,
		BDeviceID:        bDevice,
		Status:           status,
		PhysicallyViable: viable,
	}
}

// TestDetectCausalChain_SingleDeviceDown tests a simple cascade when one device goes down.
func TestDetectCausalChain_SingleDeviceDown(t *testing.T) {
	graph := NewDependencyGraph()

	// Topology: olt1 -> ont1 -> ont2 (linear chain)
	graph.AddDevice(makeTestDevice("olt1", DeviceTypeOLT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("ont1", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("ont2", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))

	_ = graph.AddLink(makeTestLink("link1", "olt1", "ont1", DeviceStatusUp, true), false) // directed
	_ = graph.AddLink(makeTestLink("link2", "ont1", "ont2", DeviceStatusUp, true), false) // directed

	ctx := context.Background()

	// Simulate olt1 going down
	result, err := DetectCausalChain(ctx, graph, []string{"olt1"}, []string{})

	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Should affect olt1, ont1, ont2 (cascading failure)
	if len(result.AffectedDevices) != 3 {
		t.Errorf("Expected 3 affected devices, got %d: %v", len(result.AffectedDevices), result.AffectedDevices)
	}

	// Check depths
	if result.Depths["olt1"] != 0 {
		t.Errorf("Expected depth 0 for olt1, got %d", result.Depths["olt1"])
	}
	if result.Depths["ont1"] != 1 {
		t.Errorf("Expected depth 1 for ont1, got %d", result.Depths["ont1"])
	}
	if result.Depths["ont2"] != 2 {
		t.Errorf("Expected depth 2 for ont2, got %d", result.Depths["ont2"])
	}

	// Check dependency paths
	if len(result.DependencyPaths["ont2"]) != 3 {
		t.Errorf("Expected path length 3 for ont2 [olt1 -> ont1 -> ont2], got %d: %v",
			len(result.DependencyPaths["ont2"]), result.DependencyPaths["ont2"])
	}
}

// TestDetectCausalChain_ComplexTopology tests a complex network with multiple paths.
func TestDetectCausalChain_ComplexTopology(t *testing.T) {
	graph := NewDependencyGraph()

	// Topology:
	//      core
	//     /    \
	//   olt1  olt2
	//   / \    / \
	// ont1 ont2 ont3 ont4

	graph.AddDevice(makeTestDevice("core", DeviceTypeCoreRouter, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("olt1", DeviceTypeOLT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("olt2", DeviceTypeOLT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("ont1", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("ont2", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("ont3", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("ont4", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))

	_ = graph.AddLink(makeTestLink("link_core_olt1", "core", "olt1", DeviceStatusUp, true), false)
	_ = graph.AddLink(makeTestLink("link_core_olt2", "core", "olt2", DeviceStatusUp, true), false)
	_ = graph.AddLink(makeTestLink("link_olt1_ont1", "olt1", "ont1", DeviceStatusUp, true), false)
	_ = graph.AddLink(makeTestLink("link_olt1_ont2", "olt1", "ont2", DeviceStatusUp, true), false)
	_ = graph.AddLink(makeTestLink("link_olt2_ont3", "olt2", "ont3", DeviceStatusUp, true), false)
	_ = graph.AddLink(makeTestLink("link_olt2_ont4", "olt2", "ont4", DeviceStatusUp, true), false)

	ctx := context.Background()

	// Simulate core router going down
	result, err := DetectCausalChain(ctx, graph, []string{"core"}, []string{})

	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Should affect all 7 devices (core + 2 OLTs + 4 ONTs)
	if len(result.AffectedDevices) != 7 {
		t.Errorf("Expected 7 affected devices, got %d: %v", len(result.AffectedDevices), result.AffectedDevices)
	}

	// Check depths
	if result.Depths["core"] != 0 {
		t.Errorf("Expected depth 0 for core, got %d", result.Depths["core"])
	}
	if result.Depths["olt1"] != 1 || result.Depths["olt2"] != 1 {
		t.Errorf("Expected depth 1 for OLTs, got olt1=%d, olt2=%d", result.Depths["olt1"], result.Depths["olt2"])
	}
	// ONTs should be at depth 2
	for _, ontID := range []string{"ont1", "ont2", "ont3", "ont4"} {
		if result.Depths[ontID] != 2 {
			t.Errorf("Expected depth 2 for %s, got %d", ontID, result.Depths[ontID])
		}
	}
}

// TestDetectCausalChain_CycleHandling tests that cycles in the topology don't cause infinite loops.
func TestDetectCausalChain_CycleHandling(t *testing.T) {
	graph := NewDependencyGraph()

	// Topology with cycle: A -> B -> C -> A
	graph.AddDevice(makeTestDevice("A", DeviceTypeCoreRouter, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("B", DeviceTypeCoreRouter, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("C", DeviceTypeCoreRouter, DeviceRoleActive, DeviceStatusUp, true))

	_ = graph.AddLink(makeTestLink("link_AB", "A", "B", DeviceStatusUp, true), false)
	_ = graph.AddLink(makeTestLink("link_BC", "B", "C", DeviceStatusUp, true), false)
	_ = graph.AddLink(makeTestLink("link_CA", "C", "A", DeviceStatusUp, true), false) // cycle!

	ctx := context.Background()

	// Simulate A going down
	result, err := DetectCausalChain(ctx, graph, []string{"A"}, []string{})

	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Should affect A, B, C (all 3 devices) without infinite loop
	if len(result.AffectedDevices) != 3 {
		t.Errorf("Expected 3 affected devices, got %d: %v", len(result.AffectedDevices), result.AffectedDevices)
	}

	// Each device should be visited exactly once
	visitedCount := make(map[string]int)
	for _, deviceID := range result.AffectedDevices {
		visitedCount[deviceID]++
	}
	for deviceID, count := range visitedCount {
		if count != 1 {
			t.Errorf("Device %s visited %d times (expected 1)", deviceID, count)
		}
	}
}

// TestDetectCausalChain_IsolatedChange tests that isolated devices don't affect others.
func TestDetectCausalChain_IsolatedChange(t *testing.T) {
	graph := NewDependencyGraph()

	// Topology: Two separate chains
	// Chain 1: olt1 -> ont1
	// Chain 2: olt2 -> ont2 (isolated)

	graph.AddDevice(makeTestDevice("olt1", DeviceTypeOLT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("ont1", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("olt2", DeviceTypeOLT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("ont2", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))

	_ = graph.AddLink(makeTestLink("link1", "olt1", "ont1", DeviceStatusUp, true), false)
	_ = graph.AddLink(makeTestLink("link2", "olt2", "ont2", DeviceStatusUp, true), false)

	ctx := context.Background()

	// Simulate olt1 going down
	result, err := DetectCausalChain(ctx, graph, []string{"olt1"}, []string{})

	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Should only affect olt1 and ont1 (NOT olt2, ont2)
	if len(result.AffectedDevices) != 2 {
		t.Errorf("Expected 2 affected devices, got %d: %v", len(result.AffectedDevices), result.AffectedDevices)
	}

	affectedSet := make(map[string]bool)
	for _, deviceID := range result.AffectedDevices {
		affectedSet[deviceID] = true
	}

	if !affectedSet["olt1"] || !affectedSet["ont1"] {
		t.Error("Expected olt1 and ont1 to be affected")
	}
	if affectedSet["olt2"] || affectedSet["ont2"] {
		t.Error("Did not expect olt2 or ont2 to be affected")
	}
}

// TestDetectCausalChain_AdminOverrideBlocks tests that admin override DOWN blocks propagation.
func TestDetectCausalChain_AdminOverrideBlocks(t *testing.T) {
	graph := NewDependencyGraph()

	// Topology: olt1 -> ont1 -> ont2
	// ont1 has admin override DOWN (should block propagation to ont2)

	graph.AddDevice(makeTestDevice("olt1", DeviceTypeOLT, DeviceRoleActive, DeviceStatusUp, true))

	statusDown := DeviceStatusDown
	ont1 := makeTestDevice("ont1", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true)
	ont1.AdminOverrideStatus = &statusDown
	graph.AddDevice(ont1)

	graph.AddDevice(makeTestDevice("ont2", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))

	_ = graph.AddLink(makeTestLink("link1", "olt1", "ont1", DeviceStatusUp, true), false)
	_ = graph.AddLink(makeTestLink("link2", "ont1", "ont2", DeviceStatusUp, true), false)

	ctx := context.Background()

	// Simulate olt1 going down
	result, err := DetectCausalChain(ctx, graph, []string{"olt1"}, []string{})

	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Should only affect olt1 (ont1 blocked by admin override, ont2 unreachable)
	if len(result.AffectedDevices) != 1 {
		t.Errorf("Expected 1 affected device (olt1 only), got %d: %v", len(result.AffectedDevices), result.AffectedDevices)
	}

	if result.AffectedDevices[0] != "olt1" {
		t.Errorf("Expected only olt1 to be affected, got: %v", result.AffectedDevices)
	}
}

// TestDetectCausalChain_UnprovisionedDeviceBlocks tests that unprovisioned ACTIVE devices block propagation.
func TestDetectCausalChain_UnprovisionedDeviceBlocks(t *testing.T) {
	graph := NewDependencyGraph()

	// Topology: olt1 -> ont1 -> ont2
	// ont1 is ACTIVE but unprovisioned (should block propagation to ont2)

	graph.AddDevice(makeTestDevice("olt1", DeviceTypeOLT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("ont1", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, false)) // NOT provisioned
	graph.AddDevice(makeTestDevice("ont2", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))

	_ = graph.AddLink(makeTestLink("link1", "olt1", "ont1", DeviceStatusUp, true), false)
	_ = graph.AddLink(makeTestLink("link2", "ont1", "ont2", DeviceStatusUp, true), false)

	ctx := context.Background()

	// Simulate olt1 going down
	result, err := DetectCausalChain(ctx, graph, []string{"olt1"}, []string{})

	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Should only affect olt1 (ont1 unprovisioned, ont2 unreachable)
	if len(result.AffectedDevices) != 1 {
		t.Errorf("Expected 1 affected device (olt1 only), got %d: %v", len(result.AffectedDevices), result.AffectedDevices)
	}

	if result.AffectedDevices[0] != "olt1" {
		t.Errorf("Expected only olt1 to be affected, got: %v", result.AffectedDevices)
	}
}

// TestDetectCausalChain_PassiveDevicesAlwaysPropagate tests that PASSIVE devices always allow propagation.
func TestDetectCausalChain_PassiveDevicesAlwaysPropagate(t *testing.T) {
	graph := NewDependencyGraph()

	// Topology: olt1 -> odf1 (passive) -> ont1
	// odf1 is PASSIVE and unprovisioned (should still allow propagation)

	graph.AddDevice(makeTestDevice("olt1", DeviceTypeOLT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("odf1", DeviceTypeODF, DeviceRolePassive, DeviceStatusUp, false)) // PASSIVE, unprovisioned
	graph.AddDevice(makeTestDevice("ont1", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))

	_ = graph.AddLink(makeTestLink("link1", "olt1", "odf1", DeviceStatusUp, true), false)
	_ = graph.AddLink(makeTestLink("link2", "odf1", "ont1", DeviceStatusUp, true), false)

	ctx := context.Background()

	// Simulate olt1 going down
	result, err := DetectCausalChain(ctx, graph, []string{"olt1"}, []string{})

	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Should affect all 3 devices (olt1, odf1, ont1) - PASSIVE allows propagation
	if len(result.AffectedDevices) != 3 {
		t.Errorf("Expected 3 affected devices, got %d: %v", len(result.AffectedDevices), result.AffectedDevices)
	}

	affectedSet := make(map[string]bool)
	for _, deviceID := range result.AffectedDevices {
		affectedSet[deviceID] = true
	}

	if !affectedSet["olt1"] || !affectedSet["odf1"] || !affectedSet["ont1"] {
		t.Error("Expected olt1, odf1, and ont1 to all be affected")
	}
}

// TestDetectCausalChain_EmptyInput tests behavior with no changed devices.
func TestDetectCausalChain_EmptyInput(t *testing.T) {
	graph := NewDependencyGraph()

	graph.AddDevice(makeTestDevice("olt1", DeviceTypeOLT, DeviceRoleActive, DeviceStatusUp, true))
	graph.AddDevice(makeTestDevice("ont1", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true))

	ctx := context.Background()

	// No changed devices
	result, err := DetectCausalChain(ctx, graph, []string{}, []string{})

	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Should have no affected devices
	if len(result.AffectedDevices) != 0 {
		t.Errorf("Expected 0 affected devices, got %d: %v", len(result.AffectedDevices), result.AffectedDevices)
	}
}

// TestDetectCausalChain_NilGraph tests error handling with nil graph.
func TestDetectCausalChain_NilGraph(t *testing.T) {
	ctx := context.Background()

	_, err := DetectCausalChain(ctx, nil, []string{"device1"}, []string{})

	if err == nil {
		t.Error("Expected error for nil graph, got nil")
	}
}

// TestDetectCausalChain_ContextCancellation tests graceful cancellation.
func TestDetectCausalChain_ContextCancellation(t *testing.T) {
	graph := NewDependencyGraph()

	// Create large topology (100 devices in chain)
	for i := 0; i < 100; i++ {
		deviceID := fmt.Sprintf("device%d", i)
		graph.AddDevice(makeTestDevice(deviceID, DeviceTypeCoreRouter, DeviceRoleActive, DeviceStatusUp, true))

		if i > 0 {
			linkID := fmt.Sprintf("link%d", i)
			prevDeviceID := fmt.Sprintf("device%d", i-1)
			_ = graph.AddLink(makeTestLink(linkID, prevDeviceID, deviceID, DeviceStatusUp, true), false)
		}
	}

	// Create context with immediate cancellation
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	_, err := DetectCausalChain(ctx, graph, []string{"device0"}, []string{})

	if err == nil {
		t.Error("Expected context cancellation error, got nil")
	}

	if err != context.Canceled {
		t.Errorf("Expected context.Canceled error, got: %v", err)
	}
}

// TestBuildDependencyGraphFromTopology tests graph construction from raw data.
func TestBuildDependencyGraphFromTopology(t *testing.T) {
	devices := []*DeviceRecord{
		makeTestDevice("olt1", DeviceTypeOLT, DeviceRoleActive, DeviceStatusUp, true),
		makeTestDevice("ont1", DeviceTypeONT, DeviceRoleActive, DeviceStatusUp, true),
	}

	links := []*LinkRecord{
		makeTestLink("link1", "olt1", "ont1", DeviceStatusUp, true),
	}

	interfaceToDevice := map[string]string{
		"olt1-if1": "olt1",
		"ont1-if1": "ont1",
	}

	graph := BuildDependencyGraphFromTopology(devices, links, interfaceToDevice)

	// Verify devices added
	if len(graph.Devices) != 2 {
		t.Errorf("Expected 2 devices, got %d", len(graph.Devices))
	}

	// Verify links added
	if len(graph.Links) != 1 {
		t.Errorf("Expected 1 link, got %d", len(graph.Links))
	}

	// Verify adjacency (bidirectional for undirected)
	if !graph.DownstreamEdges["olt1"]["ont1"] {
		t.Error("Expected olt1 -> ont1 edge")
	}
	if !graph.DownstreamEdges["ont1"]["olt1"] {
		t.Error("Expected ont1 -> olt1 edge (bidirectional)")
	}

	// Verify interface mapping
	if graph.InterfaceToDevice["olt1-if1"] != "olt1" {
		t.Error("Expected interface mapping for olt1-if1")
	}
}

// TestDetectCausalChain_ContainmentEdges tests parent-child container relationships.
func TestDetectCausalChain_ContainmentEdges(t *testing.T) {
	graph := NewDependencyGraph()

	// Topology: parent_container contains child1, child2
	parentID := "parent_container"
	graph.AddDevice(makeTestDevice(parentID, DeviceTypePOP, DeviceRoleAlwaysOnline, DeviceStatusUp, true))

	child1 := makeTestDevice("child1", DeviceTypeCoreRouter, DeviceRoleActive, DeviceStatusUp, true)
	child1.ParentContainerID = &parentID
	graph.AddDevice(child1)

	child2 := makeTestDevice("child2", DeviceTypeCoreRouter, DeviceRoleActive, DeviceStatusUp, true)
	child2.ParentContainerID = &parentID
	graph.AddDevice(child2)

	// Add containment edges
	graph.AddContainmentEdge(parentID, "child1")
	graph.AddContainmentEdge(parentID, "child2")

	ctx := context.Background()

	// Simulate parent going down
	result, err := DetectCausalChain(ctx, graph, []string{parentID}, []string{})

	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	// Should affect parent and both children
	if len(result.AffectedDevices) != 3 {
		t.Errorf("Expected 3 affected devices, got %d: %v", len(result.AffectedDevices), result.AffectedDevices)
	}

	affectedSet := make(map[string]bool)
	for _, deviceID := range result.AffectedDevices {
		affectedSet[deviceID] = true
	}

	if !affectedSet[parentID] || !affectedSet["child1"] || !affectedSet["child2"] {
		t.Error("Expected parent and both children to be affected")
	}
}
