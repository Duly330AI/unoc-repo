// Pathfinder implementation using existing types from types.go
// Ported from Python's backend/services/optical_path_resolver.py
package optical

import (
	"container/heap"
	"context"
	"database/sql"
	"fmt"
	"math"
	"sort"
	"strings"
)

// FiberAttenuationDB defines standard fiber attenuation rates (dB/km).
// Maps PhysicalMedium.code to attenuation rate.
var FiberAttenuationDB = map[string]float64{
	"SM_G652D":      0.35, // Single-mode G.652
	"SM_G657A":      0.30, // Single-mode G.657 (bend-insensitive)
	"MM_OM3":        3.00, // Multi-mode OM3
	"MM_OM4":        2.50, // Multi-mode OM4
	"FIBER_DEFAULT": 0.35, // Default fallback
}

// PriorityQueueItem represents a node in Dijkstra's priority queue.
type PriorityQueueItem struct {
	NodeID   string
	Distance float64
	Index    int
}

// PriorityQueue implements heap.Interface for Dijkstra's algorithm.
type PriorityQueue []*PriorityQueueItem

func (pq PriorityQueue) Len() int { return len(pq) }

func (pq PriorityQueue) Less(i, j int) bool {
	return pq[i].Distance < pq[j].Distance
}

func (pq PriorityQueue) Swap(i, j int) {
	pq[i], pq[j] = pq[j], pq[i]
	pq[i].Index = i
	pq[j].Index = j
}

func (pq *PriorityQueue) Push(x interface{}) {
	n := len(*pq)
	item := x.(*PriorityQueueItem)
	item.Index = n
	*pq = append(*pq, item)
}

func (pq *PriorityQueue) Pop() interface{} {
	old := *pq
	n := len(old)
	item := old[n-1]
	old[n-1] = nil  // avoid memory leak
	item.Index = -1 // for safety
	*pq = old[0 : n-1]
	return item
}

// PathFinder resolves optical paths using Dijkstra's algorithm.
type PathFinder struct {
	db *sql.DB
}

// NewPathFinder creates a new PathFinder instance.
func NewPathFinder(db *sql.DB) *PathFinder {
	return &PathFinder{db: db}
}

// buildGraph constructs the optical network graph from database.
// Uses existing Graph and Node/Edge types from types.go.
func (pf *PathFinder) buildGraph(ctx context.Context) (*Graph, error) {
	g := NewGraph()

	// Load all devices
	rows, err := pf.db.QueryContext(ctx, `
		SELECT id, type, insertion_loss_db
		FROM device
	`)
	if err != nil {
		return nil, fmt.Errorf("failed to query devices: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var id, deviceType string
		var insertionLossDB *float64
		if err := rows.Scan(&id, &deviceType, &insertionLossDB); err != nil {
			return nil, fmt.Errorf("failed to scan device: %w", err)
		}

		node := &Node{
			ID:               id,
			Type:             NodeType(deviceType),
			InsertionLossDB:  0.0,
			HasInsertionLoss: false,
		}
		if insertionLossDB != nil {
			node.InsertionLossDB = *insertionLossDB
			node.HasInsertionLoss = true
		}
		g.AddNode(node)
	}
	if rows.Err() != nil {
		return nil, fmt.Errorf("device rows error: %w", rows.Err())
	}

	// Load interface -> device mapping
	ifaceToDevice := make(map[string]string)
	rows2, err := pf.db.QueryContext(ctx, `SELECT id, device_id FROM interface`)
	if err != nil {
		return nil, fmt.Errorf("failed to query interfaces: %w", err)
	}
	defer rows2.Close()

	for rows2.Next() {
		var ifaceID, deviceID string
		if err := rows2.Scan(&ifaceID, &deviceID); err != nil {
			return nil, fmt.Errorf("failed to scan interface: %w", err)
		}
		ifaceToDevice[ifaceID] = deviceID
	}
	if rows2.Err() != nil {
		return nil, fmt.Errorf("interface rows error: %w", rows2.Err())
	}

	// Load all links with fiber loss calculation
	rows3, err := pf.db.QueryContext(ctx, `
		SELECT 
			l.id, 
			l.a_interface_id, 
			l.b_interface_id, 
			l.kind,
			l.length_km,
			l.physical_medium_id,
			pm.code
		FROM link l
		LEFT JOIN physicalmedium pm ON l.physical_medium_id = pm.id
	`)
	if err != nil {
		return nil, fmt.Errorf("failed to query links: %w", err)
	}
	defer rows3.Close()

	for rows3.Next() {
		var linkID, aInterfaceID, bInterfaceID, kind string
		var lengthKM *float64
		var physicalMediumID, pmCode *string
		if err := rows3.Scan(
			&linkID,
			&aInterfaceID,
			&bInterfaceID,
			&kind,
			&lengthKM,
			&physicalMediumID,
			&pmCode,
		); err != nil {
			return nil, fmt.Errorf("failed to scan link: %w", err)
		}

		// Resolve interface IDs to device IDs
		aDeviceID, aOK := ifaceToDevice[aInterfaceID]
		bDeviceID, bOK := ifaceToDevice[bInterfaceID]

		// Fallback for legacy "-if0" default interfaces
		if !aOK && strings.HasSuffix(aInterfaceID, "-if0") {
			aDeviceID = strings.TrimSuffix(aInterfaceID, "-if0")
			aOK = true
		}
		if !bOK && strings.HasSuffix(bInterfaceID, "-if0") {
			bDeviceID = strings.TrimSuffix(bInterfaceID, "-if0")
			bOK = true
		}

		if !aOK || !bOK {
			continue // Skip malformed links
		}

		// Calculate fiber loss (length_km * attenuation_db_per_km)
		fiberLoss := 0.0
		hasFiberLoss := false
		if lengthKM != nil && pmCode != nil {
			attenuationRate, ok := FiberAttenuationDB[*pmCode]
			if !ok {
				attenuationRate = FiberAttenuationDB["FIBER_DEFAULT"]
			}
			fiberLoss = *lengthKM * attenuationRate
			hasFiberLoss = true
		}

		// Prepare edge (Graph.AddEdge will create bidirectional)
		edge := &Edge{
			LinkID:         linkID,
			SourceID:       aDeviceID,
			TargetID:       bDeviceID,
			FiberLossDB:    fiberLoss,
			HasFiberLoss:   hasFiberLoss,
			LengthKm:       0.0,
			HasLengthKm:    false,
			PhysicalMedium: "",
		}
		if lengthKM != nil {
			edge.LengthKm = *lengthKM
			edge.HasLengthKm = true
		}
		if pmCode != nil {
			edge.PhysicalMedium = *pmCode
		}

		if err := g.AddEdge(edge); err != nil {
			return nil, fmt.Errorf("failed to add edge %s: %w", linkID, err)
		}
	}
	if rows3.Err() != nil {
		return nil, fmt.Errorf("link rows error: %w", rows3.Err())
	}

	return g, nil
}

// dijkstra implements Dijkstra's shortest path algorithm with custom edge weights.
// Returns distances and paths from startNodeID to all reachable nodes.
func (pf *PathFinder) dijkstra(g *Graph, startNodeID string) (map[string]float64, map[string][]string, error) {
	distances := make(map[string]float64)
	paths := make(map[string][]string)
	visited := make(map[string]bool)

	// Initialize all distances to infinity
	for nodeID := range g.Nodes {
		distances[nodeID] = math.Inf(1)
	}
	distances[startNodeID] = 0.0
	paths[startNodeID] = []string{startNodeID}

	// Priority queue for Dijkstra
	pq := &PriorityQueue{}
	heap.Init(pq)
	heap.Push(pq, &PriorityQueueItem{NodeID: startNodeID, Distance: 0.0})

	for pq.Len() > 0 {
		item := heap.Pop(pq).(*PriorityQueueItem)
		currentNode := item.NodeID
		currentDist := item.Distance

		if visited[currentNode] {
			continue
		}
		visited[currentNode] = true

		// Explore neighbors
		neighbors := g.GetNeighbors(currentNode)
		for _, neighborID := range neighbors {
			if visited[neighborID] {
				continue
			}

			edge, ok := g.GetEdge(currentNode, neighborID)
			if !ok {
				continue
			}

			// Calculate edge weight: fiber loss + passive insertion loss (if entering passive node)
			edgeWeight := edge.FiberLossDB
			if neighborNode, ok := g.Nodes[neighborID]; ok {
				// Check if neighbor is passive device type (matches Python's PASSIVE_NODE_TYPES)
				if neighborNode.Type.IsPassive() && neighborNode.HasInsertionLoss {
					edgeWeight += neighborNode.InsertionLossDB
				}
			}

			newDist := currentDist + edgeWeight
			if newDist < distances[neighborID] {
				distances[neighborID] = newDist
				paths[neighborID] = append([]string{}, paths[currentNode]...)
				paths[neighborID] = append(paths[neighborID], neighborID)
				heap.Push(pq, &PriorityQueueItem{NodeID: neighborID, Distance: newDist})
			}
		}
	}

	return distances, paths, nil
}

// ResolveOpticalPath finds the minimal-attenuation path from ONT to any reachable OLT.
// Returns nil if ONT not found or no path exists.
func (pf *PathFinder) ResolveOpticalPath(ctx context.Context, ontID string) (*OpticalPathResult, error) {
	// Build graph from database
	g, err := pf.buildGraph(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to build graph: %w", err)
	}

	// Check if ONT exists
	if _, exists := g.Nodes[ontID]; !exists {
		return nil, nil // ONT not found, return nil (no path)
	}

	// Run Dijkstra from ONT
	distances, paths, err := pf.dijkstra(g, ontID)
	if err != nil {
		return nil, fmt.Errorf("dijkstra failed: %w", err)
	}

	// Collect candidate OLTs
	type candidate struct {
		Distance  float64
		LengthKM  float64
		HopCount  int
		OLTID     string
		Signature string
		Path      []string
	}

	var candidates []candidate
	for nodeID, dist := range distances {
		node := g.Nodes[nodeID]
		if !node.Type.IsOLT() {
			continue
		}
		path, ok := paths[nodeID]
		if !ok || len(path) == 0 {
			continue
		}

		// Calculate total physical path length (km)
		lengthKM := 0.0
		for i := 0; i < len(path)-1; i++ {
			u, v := path[i], path[i+1]
			if edge, ok := g.GetEdge(u, v); ok && edge.HasLengthKm {
				lengthKM += edge.LengthKm
			}
		}

		hopCount := len(path) - 1
		signature := strings.Join(path, ",")

		candidates = append(candidates, candidate{
			Distance:  dist,
			LengthKM:  lengthKM,
			HopCount:  hopCount,
			OLTID:     nodeID,
			Signature: signature,
			Path:      path,
		})
	}

	if len(candidates) == 0 {
		return nil, nil // No path to any OLT
	}

	// Deterministic ordering: attenuation, physical length, hops, olt id, path signature
	// Matches Python: candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]))
	sort.Slice(candidates, func(i, j int) bool {
		ci, cj := candidates[i], candidates[j]
		if ci.Distance != cj.Distance {
			return ci.Distance < cj.Distance
		}
		if ci.LengthKM != cj.LengthKM {
			return ci.LengthKM < cj.LengthKM
		}
		if ci.HopCount != cj.HopCount {
			return ci.HopCount < cj.HopCount
		}
		if ci.OLTID != cj.OLTID {
			return ci.OLTID < cj.OLTID
		}
		return ci.Signature < cj.Signature
	})

	best := candidates[0]

	// Build path segments (matches Python PathSegment)
	segments := make([]PathSegment, 0, len(best.Path)-1)
	for i := 0; i < len(best.Path)-1; i++ {
		u, v := best.Path[i], best.Path[i+1]
		edge, _ := g.GetEdge(u, v)
		linkIDPtr := &edge.LinkID
		segments = append(segments, PathSegment{
			Src:           u,
			Dst:           v,
			LinkID:        linkIDPtr,
			AttenuationDB: edge.FiberLossDB,
		})
	}

	return &OpticalPathResult{
		OLTID:              best.OLTID,
		TotalAttenuationDB: best.Distance,
		Segments:           segments,
		TotalLengthKm:      best.LengthKM,
		HopCount:           best.HopCount,
	}, nil
}
