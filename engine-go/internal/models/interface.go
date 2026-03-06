package models

import "database/sql"

// InterfaceRole represents the functional role of an interface
type InterfaceRole string

const (
	InterfaceRoleManagement InterfaceRole = "management"
	InterfaceRoleP2PUplink  InterfaceRole = "p2p_uplink"
	InterfaceRoleAccess     InterfaceRole = "access"
)

// PortRole represents the port type
type PortRole string

const (
	PortRoleAccess PortRole = "ACCESS"
	PortRoleUplink PortRole = "UPLINK"
	PortRolePON    PortRole = "PON"
	PortRoleTrunk  PortRole = "TRUNK"
)

// AdminStatus represents the administrative status
type AdminStatus string

const (
	AdminStatusUP   AdminStatus = "up"
	AdminStatusDOWN AdminStatus = "down"
)

// Interface represents a network interface on a device
type Interface struct {
	ID             string         `db:"id"`
	DeviceID       string         `db:"device_id"`
	Name           string         `db:"name"`
	Role           sql.NullString `db:"role"` // InterfaceRole or NULL
	AdminStatus    AdminStatus    `db:"admin_status"`
	Capacity       sql.NullInt64  `db:"capacity"`  // Mbps
	PortRole       sql.NullString `db:"port_role"` // PortRole or NULL
	BridgeDomainID sql.NullInt64  `db:"bridge_domain_id"`
	ProfileName    sql.NullString `db:"profile_name"`
	MACAddress     sql.NullString `db:"mac_address"`
}
