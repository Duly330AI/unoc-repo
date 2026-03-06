package models

import "database/sql"

// TariffTechnology represents the access technology
type TariffTechnology string

const (
	TariffTechnologyGPON TariffTechnology = "GPON"
	TariffTechnologyAON  TariffTechnology = "AON"
)

// Tariff represents a service plan with bandwidth limits
type Tariff struct {
	ID          int64          `db:"id"`
	Name        string         `db:"name"`
	MaxUpMbps   float64        `db:"max_up_mbps"`
	MaxDownMbps float64        `db:"max_down_mbps"`
	Technology  sql.NullString `db:"technology"` // TariffTechnology or NULL
}
