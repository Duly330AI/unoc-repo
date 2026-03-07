package status

import (
	"context"
	"fmt"
	"testing"
)

// BenchmarkDetectCausalChain_Small benchmarks causal chain detection with small topology (10 devices).
func BenchmarkDetectCausalChain_Small(b *testing.B) {
	graph := buildBenchmarkGraph(10)
	changedDevices := []string{"core-0"}
	changedLinks := []string{}
	ctx := context.Background()

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := DetectCausalChain(ctx, graph, changedDevices, changedLinks)
		if err != nil {
			b.Fatalf("DetectCausalChain failed: %v", err)
		}
	}
}

// BenchmarkDetectCausalChain_Medium benchmarks causal chain detection with medium topology (50 devices).
func BenchmarkDetectCausalChain_Medium(b *testing.B) {
	graph := buildBenchmarkGraph(50)
	changedDevices := []string{"core-0"}
	changedLinks := []string{}
	ctx := context.Background()

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := DetectCausalChain(ctx, graph, changedDevices, changedLinks)
		if err != nil {
			b.Fatalf("DetectCausalChain failed: %v", err)
		}
	}
}

// BenchmarkDetectCausalChain_Large benchmarks causal chain detection with large topology (100 devices).
func BenchmarkDetectCausalChain_Large(b *testing.B) {
	graph := buildBenchmarkGraph(100)
	changedDevices := []string{"core-0"}
	changedLinks := []string{}
	ctx := context.Background()

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := DetectCausalChain(ctx, graph, changedDevices, changedLinks)
		if err != nil {
			b.Fatalf("DetectCausalChain failed: %v", err)
		}
	}
}

// BenchmarkDetectCausalChain_XLarge benchmarks causal chain detection with extra-large topology (200 devices).
// Target: <10ms per operation (vs ~2000ms Python for full pipeline)
func BenchmarkDetectCausalChain_XLarge(b *testing.B) {
	graph := buildBenchmarkGraph(200)
	changedDevices := []string{"core-0"}
	changedLinks := []string{}
	ctx := context.Background()

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := DetectCausalChain(ctx, graph, changedDevices, changedLinks)
		if err != nil {
			b.Fatalf("DetectCausalChain failed: %v", err)
		}
	}
}

// BenchmarkBuildDependencyGraph_Small benchmarks graph construction with small topology.
func BenchmarkBuildDependencyGraph_Small(b *testing.B) {
	devices, links, interfaceToDevice := generateBenchmarkTopology(10)

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = BuildDependencyGraphFromTopology(devices, links, interfaceToDevice)
	}
}

// BenchmarkBuildDependencyGraph_Medium benchmarks graph construction with medium topology.
func BenchmarkBuildDependencyGraph_Medium(b *testing.B) {
	devices, links, interfaceToDevice := generateBenchmarkTopology(50)

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = BuildDependencyGraphFromTopology(devices, links, interfaceToDevice)
	}
}

// BenchmarkBuildDependencyGraph_Large benchmarks graph construction with large topology.
func BenchmarkBuildDependencyGraph_Large(b *testing.B) {
	devices, links, interfaceToDevice := generateBenchmarkTopology(100)

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = BuildDependencyGraphFromTopology(devices, links, interfaceToDevice)
	}
}

// BenchmarkBuildDependencyGraph_XLarge benchmarks graph construction with extra-large topology.
func BenchmarkBuildDependencyGraph_XLarge(b *testing.B) {
	devices, links, interfaceToDevice := generateBenchmarkTopology(200)

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = BuildDependencyGraphFromTopology(devices, links, interfaceToDevice)
	}
}

// buildBenchmarkGraph creates a tree topology for benchmarking.
// Topology: core-0 → (dist-0..N/4) → (access-0..N/2) → (ont-0..N/4)
func buildBenchmarkGraph(deviceCount int) *DependencyGraph {
	devices, links, interfaceToDevice := generateBenchmarkTopology(deviceCount)
	return BuildDependencyGraphFromTopology(devices, links, interfaceToDevice)
}

// generateBenchmarkTopology creates devices and links for benchmarking.
// Returns device slice, link slice, and interface-to-device mapping.
func generateBenchmarkTopology(deviceCount int) ([]*DeviceRecord, []*LinkRecord, map[string]string) {
	devicesSlice := make([]*DeviceRecord, 0, deviceCount)
	links := make([]*LinkRecord, 0, deviceCount)
	interfaceToDevice := make(map[string]string)

	// Calculate topology distribution
	coreCount := 1
	distCount := deviceCount / 4
	if distCount < 1 {
		distCount = 1
	}
	accessCount := deviceCount / 2
	if accessCount < 1 {
		accessCount = 1
	}
	ontCount := deviceCount - coreCount - distCount - accessCount
	if ontCount < 1 {
		ontCount = 1
	}

	// Create core device
	coreID := "core-0"
	coreIfaceID := coreID + "-if0"
	devicesSlice = append(devicesSlice, &DeviceRecord{
		ID:                  coreID,
		Type:                DeviceTypeCoreRouter,
		Role:                DeviceRoleActive,
		Status:              DeviceStatusUp,
		AdminOverrideStatus: nil,
		Provisioned:         true,
		ParentContainerID:   nil,
	})
	interfaceToDevice[coreIfaceID] = coreID

	// Create distribution devices and links from core
	for i := 0; i < distCount; i++ {
		distID := fmt.Sprintf("dist-%d", i)
		distIfaceID := distID + "-if0"
		devicesSlice = append(devicesSlice, &DeviceRecord{
			ID:                  distID,
			Type:                DeviceTypeEdgeRouter,
			Role:                DeviceRoleActive,
			Status:              DeviceStatusUp,
			AdminOverrideStatus: nil,
			Provisioned:         true,
			ParentContainerID:   nil,
		})
		interfaceToDevice[distIfaceID] = distID

		links = append(links, &LinkRecord{
			ID:                  fmt.Sprintf("link-core-dist-%d", i),
			ADeviceID:           coreID,
			BDeviceID:           distID,
			Status:              DeviceStatusUp,
			AdminOverrideStatus: nil,
			PhysicallyViable:    true,
		})
	}

	// Create access devices and links from distribution
	for i := 0; i < accessCount; i++ {
		accessID := fmt.Sprintf("access-%d", i)
		accessIfaceID := accessID + "-if0"
		devicesSlice = append(devicesSlice, &DeviceRecord{
			ID:                  accessID,
			Type:                DeviceTypeOLT,
			Role:                DeviceRoleActive,
			Status:              DeviceStatusUp,
			AdminOverrideStatus: nil,
			Provisioned:         true,
			ParentContainerID:   nil,
		})
		interfaceToDevice[accessIfaceID] = accessID

		// Connect to distribution layer (round-robin)
		distID := fmt.Sprintf("dist-%d", i%distCount)
		links = append(links, &LinkRecord{
			ID:                  fmt.Sprintf("link-dist-access-%d", i),
			ADeviceID:           distID,
			BDeviceID:           accessID,
			Status:              DeviceStatusUp,
			AdminOverrideStatus: nil,
			PhysicallyViable:    true,
		})
	}

	// Create ONT devices and links from access
	for i := 0; i < ontCount; i++ {
		ontID := fmt.Sprintf("ont-%d", i)
		ontIfaceID := ontID + "-if0"
		devicesSlice = append(devicesSlice, &DeviceRecord{
			ID:                  ontID,
			Type:                DeviceTypeONT,
			Role:                DeviceRoleActive,
			Status:              DeviceStatusUp,
			AdminOverrideStatus: nil,
			Provisioned:         true,
			ParentContainerID:   nil,
		})
		interfaceToDevice[ontIfaceID] = ontID

		// Connect to access layer (round-robin)
		accessID := fmt.Sprintf("access-%d", i%accessCount)
		links = append(links, &LinkRecord{
			ID:                  fmt.Sprintf("link-access-ont-%d", i),
			ADeviceID:           accessID,
			BDeviceID:           ontID,
			Status:              DeviceStatusUp,
			AdminOverrideStatus: nil,
			PhysicallyViable:    true,
		})
	}

	return devicesSlice, links, interfaceToDevice
}
