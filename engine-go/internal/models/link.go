package models

import "database/sql"

// LinkType represents the type of link
type LinkType string

const (
	LinkTypeFiber LinkType = "FIBER"
	LinkTypeP2P   LinkType = "P2P"
	LinkTypeMGMT  LinkType = "MGMT"
)

// Link represents a connection between two interfaces
type Link struct {
	ID                  string          `db:"id"`
	AInterfaceID        string          `db:"a_interface_id"`
	BInterfaceID        string          `db:"b_interface_id"`
	Status              Status          `db:"status"`
	Kind                LinkType        `db:"kind"`
	AdminOverrideStatus sql.NullString  `db:"admin_override_status"` // Status or NULL
	ProtectionMode      sql.NullString  `db:"protection_mode"`
	LengthKM            sql.NullFloat64 `db:"length_km"`
	PhysicalMediumID    sql.NullInt64   `db:"physical_medium_id"`
}

// EffectiveStatus returns the actual status (admin override if set, else status)
func (l *Link) EffectiveStatus() Status {
	if l.AdminOverrideStatus.Valid {
		return Status(l.AdminOverrideStatus.String)
	}
	return l.Status
}
