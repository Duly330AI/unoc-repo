package status

import (
	"context"
	"database/sql"
	"fmt"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/rs/zerolog"

	pb "github.com/unoc/engine-go/proto/status"
)

// stringPtr is a helper to convert string to *string for proto fields.
func stringPtr(s string) *string {
	return &s
}

// TestPropagateStatus_LinearTopology tests status propagation in a simple linear chain.
// Topology: olt1 → ont1 → ont2
// When olt1 changes, expect ont1 and ont2 to be affected.
func TestPropagateStatus_LinearTopology(t *testing.T) {
	// Create mock database
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("Failed to create mock database: %v", err)
	}
	defer db.Close()

	// Setup mock expectations for fetchTopologyData
	setupLinearTopologyMock(mock)

	// Create service with mock database
	logger := zerolog.Nop()
	service := NewService(db, logger)

	// Create PropagateStatus request
	req := &pb.PropagateRequest{
		ChangedDeviceIds:     []string{"olt1"},
		ChangedLinkIds:       []string{},
		ForceFullPropagation: false,
		RequestId:            stringPtr("test-linear-1"),
	}

	// Execute
	ctx := context.Background()
	resp, err := service.PropagateStatus(ctx, req)

	// Verify
	if err != nil {
		t.Fatalf("PropagateStatus failed: %v", err)
	}

	if resp.Status != "success" {
		t.Errorf("Expected status 'success', got '%s'", resp.Status)
	}

	// Expect 3 affected devices (olt1 seed + ont1 + ont2 downstream)
	expectedCount := int32(3)
	if resp.AffectedDevices != expectedCount {
		t.Errorf("Expected %d affected devices, got %d", expectedCount, resp.AffectedDevices)
	}

	// Verify affected device IDs
	expectedIDs := map[string]bool{"olt1": true, "ont1": true, "ont2": true}
	for _, deviceID := range resp.DeviceIds {
		if !expectedIDs[deviceID] {
			t.Errorf("Unexpected device ID in results: %s", deviceID)
		}
	}

	// Verify duration is reasonable (< 1 second)
	if resp.DurationMs > 1000 {
		t.Errorf("PropagateStatus took too long: %dms", resp.DurationMs)
	}

	// Verify all expectations were met
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("Unfulfilled mock expectations: %v", err)
	}
}

// TestPropagateStatus_TreeTopology tests status propagation in a tree structure.
// Topology: core → (olt1, olt2) → (ont1, ont2, ont3, ont4)
// When core changes, expect all 7 devices to be affected.
func TestPropagateStatus_TreeTopology(t *testing.T) {
	// Create mock database
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("Failed to create mock database: %v", err)
	}
	defer db.Close()

	// Setup mock expectations for tree topology
	setupTreeTopologyMock(mock)

	// Create service with mock database
	logger := zerolog.Nop()
	service := NewService(db, logger)

	// Create PropagateStatus request
	req := &pb.PropagateRequest{
		ChangedDeviceIds:     []string{"core"},
		ChangedLinkIds:       []string{},
		ForceFullPropagation: false,
		RequestId:            stringPtr("test-tree-1"),
	}

	// Execute
	ctx := context.Background()
	resp, err := service.PropagateStatus(ctx, req)

	// Verify
	if err != nil {
		t.Fatalf("PropagateStatus failed: %v", err)
	}

	if resp.Status != "success" {
		t.Errorf("Expected status 'success', got '%s'", resp.Status)
	}

	// Expect 7 affected devices (core + 2 OLTs + 4 ONTs)
	expectedCount := int32(7)
	if resp.AffectedDevices != expectedCount {
		t.Errorf("Expected %d affected devices, got %d", expectedCount, resp.AffectedDevices)
	}

	// Verify all expectations were met
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("Unfulfilled mock expectations: %v", err)
	}
}

// TestPropagateStatus_IsolatedChains tests that separate chains don't cross-affect.
// Topology: olt1→ont1 (isolated), olt2→ont2 (isolated)
// When olt1 changes, expect only olt1 and ont1 affected (not olt2, ont2).
func TestPropagateStatus_IsolatedChains(t *testing.T) {
	// Create mock database
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("Failed to create mock database: %v", err)
	}
	defer db.Close()

	// Setup mock expectations for isolated chains
	setupIsolatedChainsMock(mock)

	// Create service with mock database
	logger := zerolog.Nop()
	service := NewService(db, logger)

	// Create PropagateStatus request (only olt1 changes)
	req := &pb.PropagateRequest{
		ChangedDeviceIds:     []string{"olt1"},
		ChangedLinkIds:       []string{},
		ForceFullPropagation: false,
		RequestId:            stringPtr("test-isolated-1"),
	}

	// Execute
	ctx := context.Background()
	resp, err := service.PropagateStatus(ctx, req)

	// Verify
	if err != nil {
		t.Fatalf("PropagateStatus failed: %v", err)
	}

	// Expect only 2 affected devices (olt1 + ont1, NOT olt2 or ont2)
	expectedCount := int32(2)
	if resp.AffectedDevices != expectedCount {
		t.Errorf("Expected %d affected devices, got %d", expectedCount, resp.AffectedDevices)
	}

	// Verify olt2 and ont2 are NOT in the affected list
	for _, deviceID := range resp.DeviceIds {
		if deviceID == "olt2" || deviceID == "ont2" {
			t.Errorf("Device %s should not be affected (isolated chain)", deviceID)
		}
	}

	// Verify all expectations were met
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("Unfulfilled mock expectations: %v", err)
	}
}

// TestPropagateStatus_AdminOverrideBlocks tests that admin override DOWN blocks propagation.
// Topology: olt1 → ont1(override DOWN) → ont2
// When olt1 changes, expect only olt1 affected (ont1 blocked, ont2 unreachable).
func TestPropagateStatus_AdminOverrideBlocks(t *testing.T) {
	// Create mock database
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("Failed to create mock database: %v", err)
	}
	defer db.Close()

	// Setup mock expectations with admin override
	setupAdminOverrideBlocksMock(mock)

	// Create service with mock database
	logger := zerolog.Nop()
	service := NewService(db, logger)

	// Create PropagateStatus request
	req := &pb.PropagateRequest{
		ChangedDeviceIds:     []string{"olt1"},
		ChangedLinkIds:       []string{},
		ForceFullPropagation: false,
		RequestId:            stringPtr("test-override-1"),
	}

	// Execute
	ctx := context.Background()
	resp, err := service.PropagateStatus(ctx, req)

	// Verify
	if err != nil {
		t.Fatalf("PropagateStatus failed: %v", err)
	}

	// Expect only 1 affected device (olt1, ont1 blocked by admin override)
	expectedCount := int32(1)
	if resp.AffectedDevices != expectedCount {
		t.Errorf("Expected %d affected devices, got %d", expectedCount, resp.AffectedDevices)
	}

	// Verify ont1 and ont2 are NOT affected
	for _, deviceID := range resp.DeviceIds {
		if deviceID == "ont1" || deviceID == "ont2" {
			t.Errorf("Device %s should not be affected (blocked by admin override)", deviceID)
		}
	}

	// Verify all expectations were met
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("Unfulfilled mock expectations: %v", err)
	}
}

// TestPropagateStatus_EmptyInput tests handling of empty input.
func TestPropagateStatus_EmptyInput(t *testing.T) {
	// Create mock database
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("Failed to create mock database: %v", err)
	}
	defer db.Close()

	// Setup mock expectations (still fetch topology, but no propagation)
	setupEmptyTopologyMock(mock)

	// Create service with mock database
	logger := zerolog.Nop()
	service := NewService(db, logger)

	// Create PropagateStatus request with no changed devices
	req := &pb.PropagateRequest{
		ChangedDeviceIds:     []string{},
		ChangedLinkIds:       []string{},
		ForceFullPropagation: false,
		RequestId:            stringPtr("test-empty-1"),
	}

	// Execute
	ctx := context.Background()
	resp, err := service.PropagateStatus(ctx, req)

	// Verify
	if err != nil {
		t.Fatalf("PropagateStatus failed: %v", err)
	}

	// Expect 0 affected devices
	if resp.AffectedDevices != 0 {
		t.Errorf("Expected 0 affected devices, got %d", resp.AffectedDevices)
	}

	if len(resp.DeviceIds) != 0 {
		t.Errorf("Expected empty device list, got %d devices", len(resp.DeviceIds))
	}

	// Verify all expectations were met
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("Unfulfilled mock expectations: %v", err)
	}
}

// TestPropagateStatus_DatabaseError tests handling of database errors.
func TestPropagateStatus_DatabaseError(t *testing.T) {
	// Create mock database
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("Failed to create mock database: %v", err)
	}
	defer db.Close()

	// Setup mock to return error on device query
	mock.ExpectQuery("SELECT (.+) FROM device").
		WillReturnError(sql.ErrConnDone)

	// Create service with mock database
	logger := zerolog.Nop()
	service := NewService(db, logger)

	// Create PropagateStatus request
	req := &pb.PropagateRequest{
		ChangedDeviceIds:     []string{"olt1"},
		ChangedLinkIds:       []string{},
		ForceFullPropagation: false,
		RequestId:            stringPtr("test-error-1"),
	}

	// Execute
	ctx := context.Background()
	resp, err := service.PropagateStatus(ctx, req)

	// Verify error is returned
	if err == nil {
		t.Fatal("Expected error from database failure, got nil")
	}

	// Response should indicate error
	if resp.Status != "error" {
		t.Errorf("Expected status 'error', got '%s'", resp.Status)
	}

	if len(resp.Errors) == 0 {
		t.Error("Expected error messages, got empty list")
	}

	// Verify all expectations were met
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("Unfulfilled mock expectations: %v", err)
	}
}

// TestPropagateStatus_ContextCancellation tests graceful handling of context cancellation.
func TestPropagateStatus_ContextCancellation(t *testing.T) {
	// Create mock database
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("Failed to create mock database: %v", err)
	}
	defer db.Close()

	// Setup mock expectations
	setupLinearTopologyMock(mock)

	// Create service with mock database
	logger := zerolog.Nop()
	service := NewService(db, logger)

	// Create context that's already cancelled
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	// Create PropagateStatus request
	req := &pb.PropagateRequest{
		ChangedDeviceIds:     []string{"olt1"},
		ChangedLinkIds:       []string{},
		ForceFullPropagation: false,
		RequestId:            stringPtr("test-cancel-1"),
	}

	// Execute with cancelled context
	resp, err := service.PropagateStatus(ctx, req)

	// Verify context cancellation is handled
	// Note: Depending on timing, might succeed (queries fast) or fail (context cancelled)
	// Either way, should not panic
	if err != nil {
		// Check if error is context-related
		if ctx.Err() != context.Canceled {
			t.Errorf("Expected context.Canceled error, got: %v", err)
		}
	} else {
		// If no error, response should be valid
		if resp == nil {
			t.Error("Expected valid response, got nil")
		}
	}
}

// TestHealth tests the Health endpoint.
func TestHealth(t *testing.T) {
	// Create mock database with ping monitoring enabled
	db, mock, err := sqlmock.New(sqlmock.MonitorPingsOption(true))
	if err != nil {
		t.Fatalf("Failed to create mock database: %v", err)
	}
	defer db.Close()

	// Setup mock to return successful ping
	mock.ExpectPing()

	// Create service with mock database
	logger := zerolog.Nop()
	service := NewService(db, logger)

	// Create Health request
	req := &pb.HealthRequest{}

	// Execute
	ctx := context.Background()
	resp, err := service.Health(ctx, req)

	// Verify
	if err != nil {
		t.Fatalf("Health check failed: %v", err)
	}

	if resp.Status != "healthy" {
		t.Errorf("Expected status 'healthy', got '%s'", resp.Status)
	}

	if resp.DbStatus != "connected" {
		t.Errorf("Expected db_status 'connected', got '%s'", resp.DbStatus)
	}

	// Uptime should be >= 0 (may be 0 if test runs very fast)
	if resp.UptimeSeconds < 0 {
		t.Errorf("Expected non-negative uptime, got %d", resp.UptimeSeconds)
	}

	// Verify all expectations were met
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("Unfulfilled mock expectations: %v", err)
	}
}

// TestHealth_DatabaseDown tests Health endpoint with disconnected database.
func TestHealth_DatabaseDown(t *testing.T) {
	// Create mock database with ping monitoring enabled
	db, mock, err := sqlmock.New(sqlmock.MonitorPingsOption(true))
	if err != nil {
		t.Fatalf("Failed to create mock database: %v", err)
	}
	defer db.Close()

	// Setup mock to return error on ping
	mock.ExpectPing().WillReturnError(sql.ErrConnDone)

	// Create service with mock database
	logger := zerolog.Nop()
	service := NewService(db, logger)

	// Create Health request
	req := &pb.HealthRequest{}

	// Execute
	ctx := context.Background()
	resp, err := service.Health(ctx, req)

	// Verify - health check should still succeed but report unhealthy
	if err != nil {
		t.Fatalf("Health check failed: %v", err)
	}

	if resp.Status != "unhealthy" {
		t.Errorf("Expected status 'unhealthy', got '%s'", resp.Status)
	}

	if resp.DbStatus != "disconnected" {
		t.Errorf("Expected db_status 'disconnected', got '%s'", resp.DbStatus)
	}

	// Verify all expectations were met
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("Unfulfilled mock expectations: %v", err)
	}
}

// ============================================================================
// Mock Setup Helper Functions
// ============================================================================

// setupLinearTopologyMock configures mock database for linear topology (olt1 → ont1 → ont2).
func setupLinearTopologyMock(mock sqlmock.Sqlmock) {
	// Mock device query
	deviceRows := sqlmock.NewRows([]string{"id", "type", "status", "admin_override_status", "provisioned", "parent_container_id"}).
		AddRow("olt1", "OLT", "UP", nil, true, nil).
		AddRow("ont1", "ONT", "UP", nil, true, nil).
		AddRow("ont2", "ONT", "UP", nil, true, nil)

	mock.ExpectQuery("SELECT (.+) FROM device").WillReturnRows(deviceRows)

	// Mock link query (olt1 → ont1 → ont2)
	linkRows := sqlmock.NewRows([]string{"id", "a_device_id", "b_device_id", "status", "admin_override_status"}).
		AddRow("link1", "olt1", "ont1", "UP", nil).
		AddRow("link2", "ont1", "ont2", "UP", nil)

	mock.ExpectQuery("SELECT (.+) FROM link").WillReturnRows(linkRows)

	// Mock interface query
	interfaceRows := sqlmock.NewRows([]string{"id", "device_id"}).
		AddRow("olt1-if0", "olt1").
		AddRow("ont1-if0", "ont1").
		AddRow("ont2-if0", "ont2")

	mock.ExpectQuery("SELECT (.+) FROM interface").WillReturnRows(interfaceRows)

	// Mock bulk update expectations (one per affected device)
	mock.ExpectBegin()
	mock.ExpectExec("UPDATE device SET updated_at").WithArgs("olt1").WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectExec("UPDATE device SET updated_at").WithArgs("ont1").WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectExec("UPDATE device SET updated_at").WithArgs("ont2").WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectCommit()
}

// setupTreeTopologyMock configures mock database for tree topology.
func setupTreeTopologyMock(mock sqlmock.Sqlmock) {
	// Mock device query
	deviceRows := sqlmock.NewRows([]string{"id", "type", "status", "admin_override_status", "provisioned", "parent_container_id"}).
		AddRow("core", "CORE_ROUTER", "UP", nil, true, nil).
		AddRow("olt1", "OLT", "UP", nil, true, nil).
		AddRow("olt2", "OLT", "UP", nil, true, nil).
		AddRow("ont1", "ONT", "UP", nil, true, nil).
		AddRow("ont2", "ONT", "UP", nil, true, nil).
		AddRow("ont3", "ONT", "UP", nil, true, nil).
		AddRow("ont4", "ONT", "UP", nil, true, nil)

	mock.ExpectQuery("SELECT (.+) FROM device").WillReturnRows(deviceRows)

	// Mock link query (core → olt1, olt2; olt1 → ont1, ont2; olt2 → ont3, ont4)
	linkRows := sqlmock.NewRows([]string{"id", "a_device_id", "b_device_id", "status", "admin_override_status"}).
		AddRow("link1", "core", "olt1", "UP", nil).
		AddRow("link2", "core", "olt2", "UP", nil).
		AddRow("link3", "olt1", "ont1", "UP", nil).
		AddRow("link4", "olt1", "ont2", "UP", nil).
		AddRow("link5", "olt2", "ont3", "UP", nil).
		AddRow("link6", "olt2", "ont4", "UP", nil)

	mock.ExpectQuery("SELECT (.+) FROM link").WillReturnRows(linkRows)

	// Mock interface query
	interfaceRows := sqlmock.NewRows([]string{"id", "device_id"}).
		AddRow("core-if0", "core").
		AddRow("olt1-if0", "olt1").
		AddRow("olt2-if0", "olt2").
		AddRow("ont1-if0", "ont1").
		AddRow("ont2-if0", "ont2").
		AddRow("ont3-if0", "ont3").
		AddRow("ont4-if0", "ont4")

	mock.ExpectQuery("SELECT (.+) FROM interface").WillReturnRows(interfaceRows)

	// Mock bulk update expectations (7 devices)
	mock.ExpectBegin()
	for i := 0; i < 7; i++ {
		mock.ExpectExec("UPDATE device SET updated_at").WithArgs(sqlmock.AnyArg()).WillReturnResult(sqlmock.NewResult(0, 1))
	}
	mock.ExpectCommit()
}

// setupIsolatedChainsMock configures mock database for isolated chains.
func setupIsolatedChainsMock(mock sqlmock.Sqlmock) {
	// Mock device query
	deviceRows := sqlmock.NewRows([]string{"id", "type", "status", "admin_override_status", "provisioned", "parent_container_id"}).
		AddRow("olt1", "OLT", "UP", nil, true, nil).
		AddRow("ont1", "ONT", "UP", nil, true, nil).
		AddRow("olt2", "OLT", "UP", nil, true, nil).
		AddRow("ont2", "ONT", "UP", nil, true, nil)

	mock.ExpectQuery("SELECT (.+) FROM device").WillReturnRows(deviceRows)

	// Mock link query (two separate chains)
	linkRows := sqlmock.NewRows([]string{"id", "a_device_id", "b_device_id", "status", "admin_override_status"}).
		AddRow("link1", "olt1", "ont1", "UP", nil).
		AddRow("link2", "olt2", "ont2", "UP", nil)

	mock.ExpectQuery("SELECT (.+) FROM link").WillReturnRows(linkRows)

	// Mock interface query
	interfaceRows := sqlmock.NewRows([]string{"id", "device_id"}).
		AddRow("olt1-if0", "olt1").
		AddRow("ont1-if0", "ont1").
		AddRow("olt2-if0", "olt2").
		AddRow("ont2-if0", "ont2")

	mock.ExpectQuery("SELECT (.+) FROM interface").WillReturnRows(interfaceRows)

	// Mock bulk update expectations (only 2 devices from first chain)
	mock.ExpectBegin()
	mock.ExpectExec("UPDATE device SET updated_at").WithArgs("olt1").WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectExec("UPDATE device SET updated_at").WithArgs("ont1").WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectCommit()
}

// setupAdminOverrideBlocksMock configures mock database with admin override blocking.
func setupAdminOverrideBlocksMock(mock sqlmock.Sqlmock) {
	// Mock device query (ont1 has admin override DOWN)
	deviceRows := sqlmock.NewRows([]string{"id", "type", "status", "admin_override_status", "provisioned", "parent_container_id"}).
		AddRow("olt1", "OLT", "UP", nil, true, nil).
		AddRow("ont1", "ONT", "UP", "DOWN", true, nil).
		AddRow("ont2", "ONT", "UP", nil, true, nil)

	mock.ExpectQuery("SELECT (.+) FROM device").WillReturnRows(deviceRows)

	// Mock link query
	linkRows := sqlmock.NewRows([]string{"id", "a_device_id", "b_device_id", "status", "admin_override_status"}).
		AddRow("link1", "olt1", "ont1", "UP", nil).
		AddRow("link2", "ont1", "ont2", "UP", nil)

	mock.ExpectQuery("SELECT (.+) FROM link").WillReturnRows(linkRows)

	// Mock interface query
	interfaceRows := sqlmock.NewRows([]string{"id", "device_id"}).
		AddRow("olt1-if0", "olt1").
		AddRow("ont1-if0", "ont1").
		AddRow("ont2-if0", "ont2")

	mock.ExpectQuery("SELECT (.+) FROM interface").WillReturnRows(interfaceRows)

	// Mock bulk update expectations (only olt1, ont1 blocked)
	mock.ExpectBegin()
	mock.ExpectExec("UPDATE device SET updated_at").WithArgs("olt1").WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectCommit()
}

// setupEmptyTopologyMock configures mock database with empty topology.
func setupEmptyTopologyMock(mock sqlmock.Sqlmock) {
	// Mock device query (empty)
	deviceRows := sqlmock.NewRows([]string{"id", "type", "status", "admin_override_status", "provisioned", "parent_container_id"})
	mock.ExpectQuery("SELECT (.+) FROM device").WillReturnRows(deviceRows)

	// Mock link query (empty)
	linkRows := sqlmock.NewRows([]string{"id", "a_device_id", "b_device_id", "status", "admin_override_status"})
	mock.ExpectQuery("SELECT (.+) FROM link").WillReturnRows(linkRows)

	// Mock interface query (empty)
	interfaceRows := sqlmock.NewRows([]string{"id", "device_id"})
	mock.ExpectQuery("SELECT (.+) FROM interface").WillReturnRows(interfaceRows)

	// No bulk update expected (no devices to update)
}

// TestDeriveDeviceRole tests the deriveDeviceRole helper function.
func TestDeriveDeviceRole(t *testing.T) {
	tests := []struct {
		deviceType   DeviceType
		expectedRole DeviceRole
	}{
		// PASSIVE devices
		{DeviceTypeODF, DeviceRolePassive},
		{DeviceTypeSplitter, DeviceRolePassive},
		{DeviceTypeHOP, DeviceRolePassive},
		{DeviceTypeNVT, DeviceRolePassive},

		// ALWAYS_ONLINE devices
		{DeviceTypeBackboneGateway, DeviceRoleAlwaysOnline},
		{DeviceTypePOP, DeviceRoleAlwaysOnline},

		// ACTIVE devices
		{DeviceTypeOLT, DeviceRoleActive},
		{DeviceTypeONT, DeviceRoleActive},
		{DeviceTypeBusinessONT, DeviceRoleActive},
		{DeviceTypeAONSwitch, DeviceRoleActive},
		{DeviceTypeCoreRouter, DeviceRoleActive},
		{DeviceTypeEdgeRouter, DeviceRoleActive},
	}

	for _, tt := range tests {
		t.Run(string(tt.deviceType), func(t *testing.T) {
			role := deriveDeviceRole(tt.deviceType)
			if role != tt.expectedRole {
				t.Errorf("deriveDeviceRole(%s) = %s, want %s",
					tt.deviceType, role, tt.expectedRole)
			}
		})
	}
}

// ============================================================================
// Benchmark Tests
// ============================================================================

// BenchmarkPropagateStatus_Small benchmarks a small topology (10 devices, linear chain).
// Target: <5ms per operation
func BenchmarkPropagateStatus_Small(b *testing.B) {
	benchmarkPropagateStatus(b, 10, "small")
}

// BenchmarkPropagateStatus_Medium benchmarks a medium topology (50 devices, tree structure).
// Target: <20ms per operation
func BenchmarkPropagateStatus_Medium(b *testing.B) {
	benchmarkPropagateStatus(b, 50, "medium")
}

// BenchmarkPropagateStatus_Large benchmarks a large topology (100 devices, complex tree).
// Target: <50ms per operation
func BenchmarkPropagateStatus_Large(b *testing.B) {
	benchmarkPropagateStatus(b, 100, "large")
}

// BenchmarkPropagateStatus_XLarge benchmarks an extra-large topology (200 devices).
// Target: <100ms per operation (vs 2000ms Python = 20× speedup)
func BenchmarkPropagateStatus_XLarge(b *testing.B) {
	benchmarkPropagateStatus(b, 200, "xlarge")
}

// benchmarkPropagateStatus is a helper function that runs benchmarks for different topology sizes.
func benchmarkPropagateStatus(b *testing.B, deviceCount int, label string) {
	// Create mock database
	db, mock, err := sqlmock.New()
	if err != nil {
		b.Fatalf("Failed to create mock database: %v", err)
	}
	defer db.Close()

	// Create service with mock database
	logger := zerolog.Nop()
	service := NewService(db, logger)

	// Create PropagateStatus request (root device triggers cascade)
	req := &pb.PropagateRequest{
		ChangedDeviceIds:     []string{"core-0"},
		ChangedLinkIds:       []string{},
		ForceFullPropagation: false,
		RequestId:            stringPtr("bench-" + label),
	}

	ctx := context.Background()

	// Report memory allocations
	b.ReportAllocs()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		// Setup fresh mock expectations for each iteration
		setupBenchmarkTopologyMock(mock, deviceCount)

		// Execute
		_, err := service.PropagateStatus(ctx, req)
		if err != nil {
			b.Fatalf("PropagateStatus failed: %v", err)
		}
	}
}

// setupBenchmarkTopologyMock creates a tree topology with specified device count.
// Topology: core-0 → (dist-0..N) → (access-0..M) → (ont-0..K)
// Structure: 1 core, N/4 distribution, N/2 access, N/4 ONTs
func setupBenchmarkTopologyMock(mock sqlmock.Sqlmock, deviceCount int) {
	// Calculate topology distribution
	coreCount := 1
	distCount := deviceCount / 4
	if distCount < 1 {
		distCount = 1
	}
	accessCount := deviceCount / 2
	if accessCount < 2 {
		accessCount = 2
	}
	ontCount := deviceCount - coreCount - distCount - accessCount
	if ontCount < 1 {
		ontCount = 1
	}

	// Build device rows
	deviceRows := sqlmock.NewRows([]string{"id", "type", "status", "admin_override_status", "provisioned", "parent_container_id"})

	// Add core router
	deviceRows.AddRow("core-0", "CORE_ROUTER", "UP", nil, true, nil)

	// Add distribution routers
	for i := 0; i < distCount; i++ {
		deviceRows.AddRow(fmt.Sprintf("dist-%d", i), "EDGE_ROUTER", "UP", nil, true, nil)
	}

	// Add access switches
	for i := 0; i < accessCount; i++ {
		deviceRows.AddRow(fmt.Sprintf("access-%d", i), "OLT", "UP", nil, true, nil)
	}

	// Add ONTs
	for i := 0; i < ontCount; i++ {
		deviceRows.AddRow(fmt.Sprintf("ont-%d", i), "ONT", "UP", nil, true, nil)
	}

	mock.ExpectQuery("SELECT (.+) FROM device").WillReturnRows(deviceRows)

	// Build link rows (tree structure)
	linkRows := sqlmock.NewRows([]string{"id", "a_device_id", "b_device_id", "status", "admin_override_status"})

	linkID := 0

	// Core → Distribution links
	for i := 0; i < distCount; i++ {
		linkRows.AddRow(fmt.Sprintf("link-%d", linkID), "core-0", fmt.Sprintf("dist-%d", i), "UP", nil)
		linkID++
	}

	// Distribution → Access links (round-robin)
	for i := 0; i < accessCount; i++ {
		distIdx := i % distCount
		linkRows.AddRow(fmt.Sprintf("link-%d", linkID), fmt.Sprintf("dist-%d", distIdx), fmt.Sprintf("access-%d", i), "UP", nil)
		linkID++
	}

	// Access → ONT links (round-robin)
	for i := 0; i < ontCount; i++ {
		accessIdx := i % accessCount
		linkRows.AddRow(fmt.Sprintf("link-%d", linkID), fmt.Sprintf("access-%d", accessIdx), fmt.Sprintf("ont-%d", i), "UP", nil)
		linkID++
	}

	mock.ExpectQuery("SELECT (.+) FROM link").WillReturnRows(linkRows)

	// Build interface rows
	interfaceRows := sqlmock.NewRows([]string{"id", "device_id"})

	// Core interfaces
	interfaceRows.AddRow("core-0-if0", "core-0")

	// Distribution interfaces
	for i := 0; i < distCount; i++ {
		interfaceRows.AddRow(fmt.Sprintf("dist-%d-if0", i), fmt.Sprintf("dist-%d", i))
	}

	// Access interfaces
	for i := 0; i < accessCount; i++ {
		interfaceRows.AddRow(fmt.Sprintf("access-%d-if0", i), fmt.Sprintf("access-%d", i))
	}

	// ONT interfaces
	for i := 0; i < ontCount; i++ {
		interfaceRows.AddRow(fmt.Sprintf("ont-%d-if0", i), fmt.Sprintf("ont-%d", i))
	}

	mock.ExpectQuery("SELECT (.+) FROM interface").WillReturnRows(interfaceRows)

	// Mock bulk update expectations (all devices affected in tree topology)
	mock.ExpectBegin()
	for i := 0; i < deviceCount; i++ {
		mock.ExpectExec("UPDATE device SET updated_at").WithArgs(sqlmock.AnyArg()).WillReturnResult(sqlmock.NewResult(0, 1))
	}
	mock.ExpectCommit()
}
