package main

import (
	"context"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"google.golang.org/protobuf/types/known/emptypb"
)

func TestNewPortSummaryService(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)
	assert.NotNil(t, service)
	assert.NotNil(t, service.devices)
	assert.NotNil(t, service.interfaces)
	assert.NotNil(t, service.links)
}

func TestHealthCheck(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Add some test data
	service.devices["dev1"] = &Device{ID: "dev1", Type: "ROUTER"}
	service.interfaces["if1"] = &Interface{ID: "if1", Name: "eth0", DeviceID: "dev1"}
	service.links["link1"] = &Link{ID: "link1"}

	ctx := context.Background()
	resp, err := service.HealthCheck(ctx, &emptypb.Empty{})
	require.NoError(t, err)
	assert.True(t, resp.Healthy)
	assert.Equal(t, int32(1), resp.CachedDevices)
	assert.Equal(t, int32(1), resp.CachedInterfaces)
	assert.Equal(t, int32(1), resp.CachedLinks)
}

func TestLoadDevices(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Mock query result - matches actual query: SELECT id, type, status, provisioned, parent_container_id FROM device
	rows := sqlmock.NewRows([]string{"id", "type", "status", "provisioned", "parent_container_id"}).
		AddRow("dev1", "ROUTER", "online", true, nil).
		AddRow("dev2", "SWITCH", "online", true, nil)

	mock.ExpectQuery("SELECT id, type, status, provisioned, parent_container_id FROM device").
		WillReturnRows(rows)

	err = service.loadDevices()
	require.NoError(t, err)
	assert.Len(t, service.devices, 2)
	assert.Equal(t, "ROUTER", service.devices["dev1"].Type)
	assert.Equal(t, "SWITCH", service.devices["dev2"].Type)
}

func TestLoadInterfaces(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Mock query result - matches actual query: SELECT id, device_id, name, port_role, profile_name, admin_status FROM interface
	portRoleUplink := "UPLINK"
	portRoleAccess := "ACCESS"
	rows := sqlmock.NewRows([]string{"id", "device_id", "name", "port_role", "profile_name", "admin_status"}).
		AddRow("if1", "dev1", "eth0", &portRoleUplink, nil, "up").
		AddRow("if2", "dev1", "eth1", &portRoleAccess, nil, "up")

	mock.ExpectQuery("SELECT id, device_id, name, port_role, profile_name, admin_status FROM interface").
		WillReturnRows(rows)

	err = service.loadInterfaces()
	require.NoError(t, err)
	assert.Len(t, service.interfaces, 2)
	assert.Equal(t, "eth0", service.interfaces["if1"].Name)
	assert.Equal(t, "eth1", service.interfaces["if2"].Name)
}

func TestBuildIndexes(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Setup test data
	service.devices["dev1"] = &Device{ID: "dev1"}
	service.interfaces["if1"] = &Interface{ID: "if1", DeviceID: "dev1"}
	service.interfaces["if2"] = &Interface{ID: "if2", DeviceID: "dev1"}

	ifA := "if1"
	ifB := "if2"
	service.links["link1"] = &Link{ID: "link1", AInterfaceID: &ifA, BInterfaceID: &ifB}

	service.buildIndexes()

	// Check device → interfaces index
	assert.Len(t, service.deviceInterfaces["dev1"], 2)

	// Check interface → links index
	assert.Len(t, service.interfaceLinks["if1"], 1)
	assert.Len(t, service.interfaceLinks["if2"], 1)
}

func TestComputeOccupancy_PON(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Setup PON occupancy map
	service.ponOccupancy = make(map[string]map[string]int)
	service.ponOccupancy["dev1"] = map[string]int{
		"if1": 5,
	}

	portRole := "PON"
	iface := &Interface{
		ID:       "if1",
		DeviceID: "dev1",
		PortRole: &portRole,
	}

	occupancy := service.computeOccupancy(iface)
	assert.Equal(t, int32(5), occupancy)
}

func TestComputeOccupancy_ACCESS(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Setup interface → links index
	ifID := "if1"
	service.interfaceLinks = make(map[string][]*Link)
	service.interfaceLinks["if1"] = []*Link{
		{ID: "link1", AInterfaceID: &ifID},
		{ID: "link2", BInterfaceID: &ifID},
	}

	portRole := "ACCESS"
	iface := &Interface{
		ID:       "if1",
		PortRole: &portRole,
	}

	occupancy := service.computeOccupancy(iface)
	assert.Equal(t, int32(2), occupancy)
}

func TestComputeOccupancy_UPLINK(t *testing.T) {
	db, _, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	service := NewPortSummaryService(db)

	// Setup interface → links index
	ifID := "if1"
	service.interfaceLinks = make(map[string][]*Link)
	service.interfaceLinks["if1"] = []*Link{
		{ID: "link1", AInterfaceID: &ifID},
	}

	portRole := "UPLINK"
	iface := &Interface{
		ID:       "if1",
		PortRole: &portRole,
	}

	occupancy := service.computeOccupancy(iface)
	assert.Equal(t, int32(1), occupancy)
}
