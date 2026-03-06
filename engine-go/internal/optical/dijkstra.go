// Package optical implements Dijkstra's algorithm for optical path resolution.
// This is the Go port of the networkx.single_source_dijkstra logic from Python.
//
// Week 2 Day 6: Dijkstra's algorithm with priority queue
package optical

import (
	"container/heap"
	"fmt"
	"math"
)

// dijkstraResult holds the result of Dijkstra's algorithm.
type dijkstraResult struct {
	Distances map[string]float64  // Node ID -> shortest distance from source
	Paths     map[string][]string // Node ID -> shortest path from source
}

// weightFunc is a function that computes the weight of an edge.
// It takes the graph, source node, target node, and returns the weight.
type weightFunc func(g *Graph, sourceID, targetID string) float64

// priorityQueueItem represents an item in the priority queue.
type priorityQueueItem struct {
	nodeID   string
	distance float64
	index    int // Index in the heap (needed for heap.Interface)
}

// priorityQueue implements heap.Interface for Dijkstra's algorithm.
type priorityQueue []*priorityQueueItem

func (pq priorityQueue) Len() int { return len(pq) }

func (pq priorityQueue) Less(i, j int) bool {
	// Min-heap: smaller distance has higher priority
	return pq[i].distance < pq[j].distance
}

func (pq priorityQueue) Swap(i, j int) {
	pq[i], pq[j] = pq[j], pq[i]
	pq[i].index = i
	pq[j].index = j
}

func (pq *priorityQueue) Push(x interface{}) {
	n := len(*pq)
	item := x.(*priorityQueueItem)
	item.index = n
	*pq = append(*pq, item)
}

func (pq *priorityQueue) Pop() interface{} {
	old := *pq
	n := len(old)
	item := old[n-1]
	old[n-1] = nil  // Avoid memory leak
	item.index = -1 // Mark as removed
	*pq = old[0 : n-1]
	return item
}

// dijkstra runs Dijkstra's algorithm from a source node.
// Returns distances and paths to all reachable nodes.
// weightFn computes the weight of each edge (custom logic for fiber + insertion loss).
func dijkstra(g *Graph, sourceID string, weightFn weightFunc) (*dijkstraResult, error) {
	// Check if source node exists
	if _, ok := g.Nodes[sourceID]; !ok {
		return nil, fmt.Errorf("source node %s not found in graph", sourceID)
	}

	// Initialize distances and paths
	distances := make(map[string]float64)
	paths := make(map[string][]string)
	visited := make(map[string]bool)

	// All distances start at infinity except source (0)
	for nodeID := range g.Nodes {
		distances[nodeID] = math.Inf(1)
	}
	distances[sourceID] = 0.0
	paths[sourceID] = []string{sourceID}

	// Priority queue for unvisited nodes
	pq := &priorityQueue{}
	heap.Init(pq)
	heap.Push(pq, &priorityQueueItem{
		nodeID:   sourceID,
		distance: 0.0,
	})

	// Track items in queue to avoid duplicates
	inQueue := make(map[string]bool)
	inQueue[sourceID] = true

	// Dijkstra main loop
	for pq.Len() > 0 {
		// Extract node with minimum distance
		item := heap.Pop(pq).(*priorityQueueItem)
		currentID := item.nodeID
		currentDist := item.distance

		delete(inQueue, currentID)

		// Skip if already visited (can happen with priority queue updates)
		if visited[currentID] {
			continue
		}
		visited[currentID] = true

		// Check if distance changed (stale queue item)
		if currentDist > distances[currentID] {
			continue
		}

		// Relax all neighbors
		for neighborID := range g.Edges[currentID] {
			if visited[neighborID] {
				continue
			}

			// Compute edge weight using custom weight function
			weight := weightFn(g, currentID, neighborID)
			newDist := currentDist + weight

			// If we found a shorter path, update
			if newDist < distances[neighborID] {
				distances[neighborID] = newDist

				// Build path by appending neighbor to current path
				newPath := make([]string, len(paths[currentID]))
				copy(newPath, paths[currentID])
				newPath = append(newPath, neighborID)
				paths[neighborID] = newPath

				// Add/update in priority queue
				if !inQueue[neighborID] {
					heap.Push(pq, &priorityQueueItem{
						nodeID:   neighborID,
						distance: newDist,
					})
					inQueue[neighborID] = true
				}
			}
		}
	}

	// Remove unreachable nodes (distance = infinity)
	for nodeID, dist := range distances {
		if math.IsInf(dist, 1) {
			delete(distances, nodeID)
			delete(paths, nodeID)
		}
	}

	return &dijkstraResult{
		Distances: distances,
		Paths:     paths,
	}, nil
}

// computeEdgeWeight calculates the weight of an edge for Dijkstra.
// Matches Python weight_fn: fiber loss + passive insertion loss when entering target node.
func computeEdgeWeight(g *Graph, sourceID, targetID string, fiberTypes map[string]FiberType) float64 {
	weight := 0.0

	// 1. Fiber loss from edge
	edge, ok := g.GetEdge(sourceID, targetID)
	if ok && edge.HasFiberLoss {
		weight += edge.FiberLossDB
	}

	// 2. Passive insertion loss when ENTERING target node
	// Matches Python: if v_type in PASSIVE_NODE_TYPES, add insertion_loss_db
	targetNode, ok := g.Nodes[targetID]
	if ok && targetNode.Type.IsPassive() && targetNode.HasInsertionLoss {
		weight += targetNode.InsertionLossDB
	}

	return weight
}

// FiberType represents fiber attenuation characteristics.
// Matches Python FIBER_TYPES from backend/constants/__init__.py
type FiberType struct {
	Code               string
	AttenuationDBPerKm float64
}

// GetFiberTypes returns the fiber type catalog.
// TODO: Load from database or config file (for now, hardcoded from Python constants)
func GetFiberTypes() map[string]FiberType {
	return map[string]FiberType{
		"SM_G652D": {Code: "SM_G652D", AttenuationDBPerKm: 0.25}, // Standard single-mode
		"SM_G657A": {Code: "SM_G657A", AttenuationDBPerKm: 0.30}, // Bend-insensitive
		"MM_OM3":   {Code: "MM_OM3", AttenuationDBPerKm: 3.0},    // Multimode 850nm
		"MM_OM4":   {Code: "MM_OM4", AttenuationDBPerKm: 3.0},    // Multimode 850nm
	}
}
