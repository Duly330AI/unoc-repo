package models

import "database/sql"

// DeviceType represents the type/category of a network device
type DeviceType string

const (
	DeviceTypeBackboneGateway DeviceType = "BACKBONE_GATEWAY"
	DeviceTypePOP             DeviceType = "POP"
	DeviceTypeCoreSite        DeviceType = "CORE_SITE"
	DeviceTypeCoreRouter      DeviceType = "CORE_ROUTER"
	DeviceTypeEdgeRouter      DeviceType = "EDGE_ROUTER"
	DeviceTypeAONSwitch       DeviceType = "AON_SWITCH"
	DeviceTypeOLT             DeviceType = "OLT"
	DeviceTypeONT             DeviceType = "ONT"
	DeviceTypeAONCPE          DeviceType = "AON_CPE"
	DeviceTypeSplitter        DeviceType = "SPLITTER"
	DeviceTypeHop             DeviceType = "HOP"
	DeviceTypeNVT             DeviceType = "NVT"
	DeviceTypeODF             DeviceType = "ODF"
	DeviceTypeBusinessONT     DeviceType = "BUSINESS_ONT"
)

// Status represents the operational status of a device or link
type Status string

const (
	StatusUP       Status = "UP"
	StatusDOWN     Status = "DOWN"
	StatusDEGRADED Status = "DEGRADED"
	StatusBLOCKING Status = "BLOCKING"
)

// DeviceRole represents the operational role of a device
type DeviceRole string

const (
	DeviceRoleActive       DeviceRole = "active"
	DeviceRolePassive      DeviceRole = "passive"
	DeviceRoleAlwaysOnline DeviceRole = "always_online"
)

// SignalStatus represents the optical signal quality
type SignalStatus string

const (
	SignalStatusOK       SignalStatus = "OK"
	SignalStatusWarning  SignalStatus = "WARNING"
	SignalStatusCritical SignalStatus = "CRITICAL"
	SignalStatusNoSignal SignalStatus = "NO_SIGNAL"
)

// Device represents a network device (router, switch, ONT, etc.)
type Device struct {
	ID                  string          `db:"id"`
	Name                string          `db:"name"`
	Type                DeviceType      `db:"type"`
	Status              Status          `db:"status"`
	Provisioned         bool            `db:"provisioned"`
	AdminOverrideStatus sql.NullString  `db:"admin_override_status"` // Status or NULL
	TxPowerDBM          sql.NullFloat64 `db:"tx_power_dbm"`
	SensitivityMinDBM   sql.NullFloat64 `db:"sensitivity_min_dbm"`
	InsertionLossDB     sql.NullFloat64 `db:"insertion_loss_db"`
	Capacity            sql.NullInt64   `db:"capacity"` // Mbps override
	SignalPowerDBM      sql.NullFloat64 `db:"signal_power_dbm"`
	SignalMarginDB      sql.NullFloat64 `db:"signal_margin_db"`
	SignalStatus        sql.NullString  `db:"signal_status"` // SignalStatus or NULL
	ParentContainerID   sql.NullString  `db:"parent_container_id"`
	SlotID              sql.NullString  `db:"slot_id"`
	TariffID            sql.NullInt64   `db:"tariff_id"`
	VRFID               sql.NullInt64   `db:"vrf_id"`
	HardwareModelID     sql.NullInt64   `db:"hardware_model_id"`
}

// DeriveRole calculates the device role based on device type
func (d *Device) DeriveRole() DeviceRole {
	// Passive optical elements (inline path components)
	switch d.Type {
	case DeviceTypeSplitter, DeviceTypeHop, DeviceTypeNVT, DeviceTypeODF:
		return DeviceRolePassive
	}

	// Always-online restricted: backbone gateway + POP/CORE_SITE only
	switch d.Type {
	case DeviceTypeBackboneGateway, DeviceTypePOP, DeviceTypeCoreSite:
		return DeviceRoleAlwaysOnline
	}

	return DeviceRoleActive
}

// IsLeaf checks if the device is a leaf device (generates traffic)
func (d *Device) IsLeaf() bool {
	switch d.Type {
	case DeviceTypeONT, DeviceTypeBusinessONT, DeviceTypeAONCPE:
		return true
	}
	return false
}

// EffectiveStatus returns the actual status (admin override if set, else status)
func (d *Device) EffectiveStatus() Status {
	if d.AdminOverrideStatus.Valid {
		return Status(d.AdminOverrideStatus.String)
	}
	return d.Status
}
