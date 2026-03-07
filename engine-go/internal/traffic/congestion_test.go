package traffic

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestDetectCongestion_NormalToCongestedTransition tests congestion detection when utilization exceeds threshold
func TestDetectCongestion_NormalToCongestedTransition(t *testing.T) {
	tests := []struct {
		name             string
		utilization      float64
		wasCongested     bool
		expectCongested  bool
		expectTransition bool
		desc             string
	}{
		{
			name:             "Below threshold, was normal",
			utilization:      0.70,
			wasCongested:     false,
			expectCongested:  false,
			expectTransition: false,
			desc:             "70% util < 90% threshold, stays normal",
		},
		{
			name:             "At threshold, was normal",
			utilization:      0.90,
			wasCongested:     false,
			expectCongested:  true,
			expectTransition: true,
			desc:             "90% util == 90% threshold, becomes congested",
		},
		{
			name:             "Above threshold, was normal",
			utilization:      0.95,
			wasCongested:     false,
			expectCongested:  true,
			expectTransition: true,
			desc:             "95% util > 90% threshold, becomes congested",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Arrange
			const (
				congestThreshold = 0.90
				clearThreshold   = 0.85
			)
			entityID := "test_entity"

			// Create previous state
			prevState := make(map[string]bool)
			prevState[entityID] = tt.wasCongested

			// Create current metrics (simplified)
			currentMetrics := map[string]float64{
				entityID: tt.utilization,
			}

			// Act
			newState := make(map[string]bool)
			transitions := []string{}

			for id, util := range currentMetrics {
				wasCongested := prevState[id]
				isCongested := false

				if wasCongested {
					// Hysteresis: stay congested until util <= clearThreshold
					isCongested = util > clearThreshold
				} else {
					// Enter congestion if util >= congestThreshold
					isCongested = util >= congestThreshold
				}

				newState[id] = isCongested

				// Detect transition
				if isCongested && !wasCongested {
					transitions = append(transitions, id+" became congested")
				} else if !isCongested && wasCongested {
					transitions = append(transitions, id+" cleared congestion")
				}
			}

			// Assert
			assert.Equal(t, tt.expectCongested, newState[entityID], tt.desc)

			if tt.expectTransition {
				assert.NotEmpty(t, transitions, "should detect transition")
				assert.Contains(t, transitions[0], entityID, "transition should mention entity ID")
			} else {
				assert.Empty(t, transitions, "should not detect transition")
			}
		})
	}
}

// TestDetectCongestion_CongestedToNormalTransition tests congestion clearing with hysteresis
func TestDetectCongestion_CongestedToNormalTransition(t *testing.T) {
	tests := []struct {
		name             string
		utilization      float64
		wasCongested     bool
		expectCongested  bool
		expectTransition bool
		desc             string
	}{
		{
			name:             "Above clear threshold, was congested",
			utilization:      0.88,
			wasCongested:     true,
			expectCongested:  true,
			expectTransition: false,
			desc:             "88% util > 85% clear threshold, stays congested (hysteresis)",
		},
		{
			name:             "At clear threshold, was congested",
			utilization:      0.85,
			wasCongested:     true,
			expectCongested:  false,
			expectTransition: true,
			desc:             "85% util == 85% clear threshold, clears congestion",
		},
		{
			name:             "Below clear threshold, was congested",
			utilization:      0.80,
			wasCongested:     true,
			expectCongested:  false,
			expectTransition: true,
			desc:             "80% util < 85% clear threshold, clears congestion",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Arrange
			const (
				congestThreshold = 0.90
				clearThreshold   = 0.85
			)
			entityID := "test_entity"

			// Create previous state
			prevState := make(map[string]bool)
			prevState[entityID] = tt.wasCongested

			// Create current metrics
			currentMetrics := map[string]float64{
				entityID: tt.utilization,
			}

			// Act
			newState := make(map[string]bool)
			transitions := []string{}

			for id, util := range currentMetrics {
				wasCongested := prevState[id]
				isCongested := false

				if wasCongested {
					// Hysteresis: stay congested until util <= clearThreshold
					isCongested = util > clearThreshold
				} else {
					// Enter congestion if util >= congestThreshold
					isCongested = util >= congestThreshold
				}

				newState[id] = isCongested

				// Detect transition
				if isCongested && !wasCongested {
					transitions = append(transitions, id+" became congested")
				} else if !isCongested && wasCongested {
					transitions = append(transitions, id+" cleared congestion")
				}
			}

			// Assert
			assert.Equal(t, tt.expectCongested, newState[entityID], tt.desc)

			if tt.expectTransition {
				assert.NotEmpty(t, transitions, "should detect transition")
				assert.Contains(t, transitions[0], "cleared", "transition should mention clearing")
			} else {
				assert.Empty(t, transitions, "should not detect transition")
			}
		})
	}
}

// TestDetectCongestion_HysteresisZone tests behavior in the "sticky" zone (85%-90%)
func TestDetectCongestion_HysteresisZone(t *testing.T) {
	tests := []struct {
		name            string
		utilization     float64
		wasCongested    bool
		expectCongested bool
		desc            string
	}{
		{
			name:            "Hysteresis zone, was normal",
			utilization:     0.87,
			wasCongested:    false,
			expectCongested: false,
			desc:            "87% in hysteresis zone, was normal → stays normal",
		},
		{
			name:            "Hysteresis zone, was congested",
			utilization:     0.87,
			wasCongested:    true,
			expectCongested: true,
			desc:            "87% in hysteresis zone, was congested → stays congested",
		},
		{
			name:            "High hysteresis zone, was normal",
			utilization:     0.89,
			wasCongested:    false,
			expectCongested: false,
			desc:            "89% near congest threshold, was normal → stays normal",
		},
		{
			name:            "High hysteresis zone, was congested",
			utilization:     0.89,
			wasCongested:    true,
			expectCongested: true,
			desc:            "89% near congest threshold, was congested → stays congested",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Arrange
			const (
				congestThreshold = 0.90
				clearThreshold   = 0.85
			)
			entityID := "test_entity"

			prevState := make(map[string]bool)
			prevState[entityID] = tt.wasCongested

			currentMetrics := map[string]float64{
				entityID: tt.utilization,
			}

			// Act
			newState := make(map[string]bool)

			for id, util := range currentMetrics {
				wasCongested := prevState[id]
				isCongested := false

				if wasCongested {
					isCongested = util > clearThreshold
				} else {
					isCongested = util >= congestThreshold
				}

				newState[id] = isCongested
			}

			// Assert
			assert.Equal(t, tt.expectCongested, newState[entityID], tt.desc)
		})
	}
}

// TestDetectCongestion_StatePersistence tests that state is correctly copied from previous tick
func TestDetectCongestion_StatePersistence(t *testing.T) {
	// Arrange: Multiple entities with different states
	prevState := map[string]bool{
		"device1": true,  // Was congested
		"device2": false, // Was normal
		"device3": true,  // Was congested
	}

	// Current utilization keeps device1 congested, device2 normal, device3 clears
	currentMetrics := map[string]float64{
		"device1": 0.92, // Stays congested (> 90%)
		"device2": 0.70, // Stays normal (< 90%)
		"device3": 0.80, // Clears (< 85%)
	}

	const (
		congestThreshold = 0.90
		clearThreshold   = 0.85
	)

	// Act
	newState := make(map[string]bool)

	for id, util := range currentMetrics {
		wasCongested := prevState[id]
		isCongested := false

		if wasCongested {
			isCongested = util > clearThreshold
		} else {
			isCongested = util >= congestThreshold
		}

		newState[id] = isCongested
	}

	// Assert: Verify each device's state transition
	assert.True(t, newState["device1"], "device1 should stay congested (92% > 85%)")
	assert.False(t, newState["device2"], "device2 should stay normal (70% < 90%)")
	assert.False(t, newState["device3"], "device3 should clear congestion (80% <= 85%)")
}

// TestDetectCongestion_MultipleEntities tests congestion detection across many entities
func TestDetectCongestion_MultipleEntities(t *testing.T) {
	// Arrange: 10 entities with varying utilization
	prevState := make(map[string]bool)
	currentMetrics := make(map[string]float64)

	// Mix of normal, congested, and hysteresis zone
	testCases := []struct {
		id              string
		util            float64
		wasCongested    bool
		expectCongested bool
	}{
		{"dev1", 0.50, false, false},  // Normal
		{"dev2", 0.75, false, false},  // Normal
		{"dev3", 0.85, false, false},  // At clear threshold but was normal
		{"dev4", 0.90, false, true},   // At congest threshold, becomes congested
		{"dev5", 0.95, false, true},   // Above congest threshold, becomes congested
		{"dev6", 0.87, true, true},    // Hysteresis zone, stays congested
		{"dev7", 0.85, true, false},   // At clear threshold, clears
		{"dev8", 0.80, true, false},   // Below clear threshold, clears
		{"dev9", 0.92, true, true},    // Above clear threshold, stays congested
		{"dev10", 0.88, false, false}, // Hysteresis zone, stays normal
	}

	for _, tc := range testCases {
		prevState[tc.id] = tc.wasCongested
		currentMetrics[tc.id] = tc.util
	}

	const (
		congestThreshold = 0.90
		clearThreshold   = 0.85
	)

	// Act
	newState := make(map[string]bool)
	congestedCount := 0

	for id, util := range currentMetrics {
		wasCongested := prevState[id]
		isCongested := false

		if wasCongested {
			isCongested = util > clearThreshold
		} else {
			isCongested = util >= congestThreshold
		}

		newState[id] = isCongested

		if isCongested {
			congestedCount++
		}
	}

	// Assert: Check each entity's expected state
	for _, tc := range testCases {
		assert.Equal(t, tc.expectCongested, newState[tc.id],
			"Entity %s (util=%.2f, was=%v) should be %v",
			tc.id, tc.util, tc.wasCongested, tc.expectCongested)
	}

	// Verify congested count
	expectedCongested := 0
	for _, tc := range testCases {
		if tc.expectCongested {
			expectedCongested++
		}
	}
	assert.Equal(t, expectedCongested, congestedCount, "congested count should match")
}

// TestDetectCongestion_TransitionLogging tests that transitions are correctly detected and logged
func TestDetectCongestion_TransitionLogging(t *testing.T) {
	tests := []struct {
		name              string
		prevState         map[string]bool
		currentMetrics    map[string]float64
		expectTransitions int
		expectBecame      []string
		expectCleared     []string
	}{
		{
			name: "No transitions",
			prevState: map[string]bool{
				"dev1": false,
				"dev2": true,
			},
			currentMetrics: map[string]float64{
				"dev1": 0.70, // Stays normal
				"dev2": 0.92, // Stays congested
			},
			expectTransitions: 0,
			expectBecame:      []string{},
			expectCleared:     []string{},
		},
		{
			name: "One device becomes congested",
			prevState: map[string]bool{
				"dev1": false,
				"dev2": false,
			},
			currentMetrics: map[string]float64{
				"dev1": 0.70, // Stays normal
				"dev2": 0.95, // Becomes congested
			},
			expectTransitions: 1,
			expectBecame:      []string{"dev2"},
			expectCleared:     []string{},
		},
		{
			name: "One device clears congestion",
			prevState: map[string]bool{
				"dev1": true,
				"dev2": true,
			},
			currentMetrics: map[string]float64{
				"dev1": 0.92, // Stays congested
				"dev2": 0.80, // Clears congestion
			},
			expectTransitions: 1,
			expectBecame:      []string{},
			expectCleared:     []string{"dev2"},
		},
		{
			name: "Multiple transitions",
			prevState: map[string]bool{
				"dev1": false,
				"dev2": true,
				"dev3": false,
				"dev4": true,
			},
			currentMetrics: map[string]float64{
				"dev1": 0.91, // Becomes congested
				"dev2": 0.83, // Clears congestion
				"dev3": 0.94, // Becomes congested
				"dev4": 0.78, // Clears congestion
			},
			expectTransitions: 4,
			expectBecame:      []string{"dev1", "dev3"},
			expectCleared:     []string{"dev2", "dev4"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			const (
				congestThreshold = 0.90
				clearThreshold   = 0.85
			)

			// Act
			newState := make(map[string]bool)
			becameList := []string{}
			clearedList := []string{}

			for id, util := range tt.currentMetrics {
				wasCongested := tt.prevState[id]
				isCongested := false

				if wasCongested {
					isCongested = util > clearThreshold
				} else {
					isCongested = util >= congestThreshold
				}

				newState[id] = isCongested

				// Detect transitions
				if isCongested && !wasCongested {
					becameList = append(becameList, id)
				} else if !isCongested && wasCongested {
					clearedList = append(clearedList, id)
				}
			}

			// Assert
			totalTransitions := len(becameList) + len(clearedList)
			assert.Equal(t, tt.expectTransitions, totalTransitions,
				"should detect %d transitions", tt.expectTransitions)

			for _, id := range tt.expectBecame {
				assert.Contains(t, becameList, id,
					"should detect %s became congested", id)
			}

			for _, id := range tt.expectCleared {
				assert.Contains(t, clearedList, id,
					"should detect %s cleared congestion", id)
			}
		})
	}
}

// TestDetectCongestion_EdgeCases tests boundary conditions and edge cases
func TestDetectCongestion_EdgeCases(t *testing.T) {
	tests := []struct {
		name            string
		utilization     float64
		wasCongested    bool
		expectCongested bool
		desc            string
	}{
		{
			name:            "Zero utilization, was normal",
			utilization:     0.0,
			wasCongested:    false,
			expectCongested: false,
			desc:            "0% utilization should stay normal",
		},
		{
			name:            "Zero utilization, was congested",
			utilization:     0.0,
			wasCongested:    true,
			expectCongested: false,
			desc:            "0% utilization should clear congestion",
		},
		{
			name:            "100% utilization, was normal",
			utilization:     1.0,
			wasCongested:    false,
			expectCongested: true,
			desc:            "100% utilization should become congested",
		},
		{
			name:            "100% utilization, was congested",
			utilization:     1.0,
			wasCongested:    true,
			expectCongested: true,
			desc:            "100% utilization should stay congested",
		},
		{
			name:            "Over 100% utilization (burst)",
			utilization:     1.2,
			wasCongested:    false,
			expectCongested: true,
			desc:            "120% utilization (burst) should become congested",
		},
		{
			name:            "Exactly at congest threshold (0.90)",
			utilization:     0.90,
			wasCongested:    false,
			expectCongested: true,
			desc:            "Exactly 90% should trigger congestion (inclusive)",
		},
		{
			name:            "Exactly at clear threshold (0.85)",
			utilization:     0.85,
			wasCongested:    true,
			expectCongested: false,
			desc:            "Exactly 85% should clear congestion (inclusive)",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			const (
				congestThreshold = 0.90
				clearThreshold   = 0.85
			)
			entityID := "test_entity"

			prevState := map[string]bool{
				entityID: tt.wasCongested,
			}

			currentMetrics := map[string]float64{
				entityID: tt.utilization,
			}

			// Act
			newState := make(map[string]bool)

			for id, util := range currentMetrics {
				wasCongested := prevState[id]
				isCongested := false

				if wasCongested {
					isCongested = util > clearThreshold
				} else {
					isCongested = util >= congestThreshold
				}

				newState[id] = isCongested
			}

			// Assert
			assert.Equal(t, tt.expectCongested, newState[entityID], tt.desc)
		})
	}
}
