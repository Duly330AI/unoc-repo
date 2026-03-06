package models

import "github.com/rs/zerolog/log"

// TopologyCache provides O(1) lookup maps for topology data
type TopologyCache struct {
	DeviceByID       map[string]*Device
	LinkByID         map[string]*Link  // link_id -> link (NEW for HGO-006)
	LinksByInterface map[string][]Link // interface_id -> links connected to it
	InterfaceByID    map[string]*Interface
	TariffByID       map[int64]*Tariff
}

// BuildTopologyCache creates index maps from raw data for fast lookups
func BuildTopologyCache(devices []Device, links []Link, interfaces []Interface, tariffs []Tariff) *TopologyCache {
	cache := &TopologyCache{
		DeviceByID:       make(map[string]*Device, len(devices)),
		LinkByID:         make(map[string]*Link, len(links)),
		LinksByInterface: make(map[string][]Link, len(interfaces)),
		InterfaceByID:    make(map[string]*Interface, len(interfaces)),
		TariffByID:       make(map[int64]*Tariff, len(tariffs)),
	}

	// Index devices
	for i := range devices {
		cache.DeviceByID[devices[i].ID] = &devices[i]
	}

	// Index interfaces
	for i := range interfaces {
		cache.InterfaceByID[interfaces[i].ID] = &interfaces[i]
	}

	// Index tariffs
	for i := range tariffs {
		cache.TariffByID[tariffs[i].ID] = &tariffs[i]
	}

	// Index links by ID and by connected interfaces
	for i := range links {
		cache.LinkByID[links[i].ID] = &links[i]
		cache.LinksByInterface[links[i].AInterfaceID] = append(cache.LinksByInterface[links[i].AInterfaceID], links[i])
		cache.LinksByInterface[links[i].BInterfaceID] = append(cache.LinksByInterface[links[i].BInterfaceID], links[i])
	}

	log.Info().
		Int("devices", len(cache.DeviceByID)).
		Int("interfaces", len(cache.InterfaceByID)).
		Int("links", len(links)).
		Int("tariffs", len(cache.TariffByID)).
		Msg("Built topology cache")

	return cache
}
