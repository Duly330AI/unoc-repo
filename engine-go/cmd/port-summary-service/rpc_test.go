package main

import (
	"context"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	pb "github.com/unoc/engine-go/proto/port_summary"
)

func TestComputeOpticalPaths(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Setup test data: ONT → ODF → OLT PON port (classic PON path)
	// ONT device (Customer device)
	service.devices["ont1"] = &Device{ID: "ont1", Type: "ONT", Provisioned: true}
	// OLT device (Central office)
	service.devices["olt1"] = &Device{ID: "olt1", Type: "OLT", Provisioned: true}
	// ODF device (Optical Distribution Frame - passive patch panel)
	service.devices["odf1"] = &Device{ID: "odf1", Type: "ODF", Provisioned: true}

	// Interfaces
	portRolePON := "PON"
	portRoleOptical := "OPTICAL"
	portRoleAccess := "ACCESS"

	service.interfaces["ont1_optical"] = &Interface{ID: "ont1_optical", DeviceID: "ont1", Name: "optical0", PortRole: &portRoleOptical}
	service.interfaces["odf1_in"] = &Interface{ID: "odf1_in", DeviceID: "odf1", Name: "in1", PortRole: &portRoleAccess}
	service.interfaces["odf1_out"] = &Interface{ID: "odf1_out", DeviceID: "odf1", Name: "out1", PortRole: &portRoleAccess}
	service.interfaces["olt1_pon1"] = &Interface{ID: "olt1_pon1", DeviceID: "olt1", Name: "PON1/1/1", PortRole: &portRolePON}

	// Links: ONT → ODF → OLT
	ontIf := "ont1_optical"
	odfIn := "odf1_in"
	odfOut := "odf1_out"
	ponIf := "olt1_pon1"

	service.links["link1"] = &Link{ID: "link1", AInterfaceID: &ontIf, BInterfaceID: &odfIn}
	service.links["link2"] = &Link{ID: "link2", AInterfaceID: &odfOut, BInterfaceID: &ponIf}

	// CRITICAL: Build indexes first! (deviceInterfaces, interfaceLinks)
	service.buildIndexes()

	// Compute optical paths
	service.computeOpticalPaths()

	// Verify: ONT should be mapped to OLT PON port
	assert.Contains(t, service.opticalPaths, "ont1")
	assert.Equal(t, "olt1_pon1", service.opticalPaths["ont1"])
}

func TestComputePONOccupancy(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Setup test data
	service.devices["ont1"] = &Device{ID: "ont1", Type: "ONT", Provisioned: true}
	service.devices["ont2"] = &Device{ID: "ont2", Type: "ONT", Provisioned: true}
	service.devices["ont3"] = &Device{ID: "ont3", Type: "ONT", Provisioned: false} // Not provisioned
	service.devices["olt1"] = &Device{ID: "olt1", Type: "OLT", Provisioned: true}

	portRolePON := "PON"
	service.interfaces["olt1_pon1"] = &Interface{ID: "olt1_pon1", DeviceID: "olt1", PortRole: &portRolePON}
	service.interfaces["olt1_pon2"] = &Interface{ID: "olt1_pon2", DeviceID: "olt1", PortRole: &portRolePON}

	// Optical paths: 2 ONTs on PON1, 1 on PON2 (but not provisioned)
	service.opticalPaths = map[string]string{
		"ont1": "olt1_pon1",
		"ont2": "olt1_pon1",
		"ont3": "olt1_pon2", // Not provisioned, should not be counted
	}

	// Compute PON occupancy
	service.computePONOccupancy()

	// Verify: PON1 should have 2 ONTs, PON2 should have 0 (ont3 not provisioned)
	assert.Contains(t, service.ponOccupancy, "olt1")
	assert.Equal(t, 2, service.ponOccupancy["olt1"]["olt1_pon1"])
	assert.Equal(t, 0, service.ponOccupancy["olt1"]["olt1_pon2"]) // Not provisioned ONT not counted
}

func TestGetPortSummary(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Setup test data
	service.devices["dev1"] = &Device{ID: "dev1", Type: "ROUTER"}
	portRoleAccess := "ACCESS"
	portRoleUplink := "UPLINK"
	service.interfaces["if1"] = &Interface{ID: "if1", DeviceID: "dev1", Name: "eth0", PortRole: &portRoleAccess}
	service.interfaces["if2"] = &Interface{ID: "if2", DeviceID: "dev1", Name: "eth1", PortRole: &portRoleUplink}

	service.buildIndexes()

	// Call GetPortSummary
	ctx := context.Background()
	resp, err := service.GetPortSummary(ctx, &pb.DeviceRequest{DeviceId: "dev1"})

	// Verify
	require.NoError(t, err)
	assert.Len(t, resp.Interfaces, 2)

	// Check interface summaries
	foundIf1 := false
	foundIf2 := false
	for _, iface := range resp.Interfaces {
		if iface.Id == "if1" {
			foundIf1 = true
			assert.Equal(t, "eth0", iface.Name)
			assert.Equal(t, "ACCESS", iface.PortRole)
		}
		if iface.Id == "if2" {
			foundIf2 = true
			assert.Equal(t, "eth1", iface.Name)
			assert.Equal(t, "UPLINK", iface.PortRole)
		}
	}
	assert.True(t, foundIf1)
	assert.True(t, foundIf2)
}

func TestGetPortSummary_NoInterfaces(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Device with no interfaces
	service.devices["dev1"] = &Device{ID: "dev1", Type: "ROUTER"}

	ctx := context.Background()
	resp, err := service.GetPortSummary(ctx, &pb.DeviceRequest{DeviceId: "dev1"})

	require.NoError(t, err)
	assert.Len(t, resp.Interfaces, 0)
}

func TestGetBulkPortSummary(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Setup test data
	service.devices["dev1"] = &Device{ID: "dev1", Type: "ROUTER"}
	service.devices["dev2"] = &Device{ID: "dev2", Type: "SWITCH"}
	portRoleAccess := "ACCESS"
	service.interfaces["if1"] = &Interface{ID: "if1", DeviceID: "dev1", Name: "eth0", PortRole: &portRoleAccess}
	service.interfaces["if2"] = &Interface{ID: "if2", DeviceID: "dev2", Name: "eth0", PortRole: &portRoleAccess}

	service.buildIndexes()

	// Call GetBulkPortSummary
	ctx := context.Background()
	resp, err := service.GetBulkPortSummary(ctx, &pb.BulkDeviceRequest{
		DeviceIds: []string{"dev1", "dev2"},
	})

	// Verify
	require.NoError(t, err)
	assert.Len(t, resp.Summaries, 2)
	assert.Contains(t, resp.Summaries, "dev1")
	assert.Contains(t, resp.Summaries, "dev2")
	assert.Len(t, resp.Summaries["dev1"].Interfaces, 1)
	assert.Len(t, resp.Summaries["dev2"].Interfaces, 1)
}

func TestInvalidateCache(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Call InvalidateCache (placeholder for Phase 2)
	ctx := context.Background()
	resp, err := service.InvalidateCache(ctx, &pb.InvalidateCacheRequest{DeviceId: "dev1"})

	require.NoError(t, err)
	assert.NotNil(t, resp)
}
