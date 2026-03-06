// physicsStore (TASK-093) skeleton
// Single lifetime force simulation holder (implementation later)

import { reactive } from 'vue'

export interface PhysicsNode {
    id: string
    x: number
    y: number
    vx?: number
    vy?: number
    fx?: number | null
    fy?: number | null
    userPinned?: boolean
    systemPinned?: boolean
}

export interface PhysicsLink {
    id: string
    source: string
    target: string
}

interface PhysicsState {
    nodes: Map<string, PhysicsNode>
    links: Map<string, PhysicsLink>
    initialized: boolean
}

const state: PhysicsState = reactive({
    nodes: new Map(),
    links: new Map(),
    initialized: false
})

export function usePhysicsStore() {
    function bootstrap(initial: { nodes: PhysicsNode[]; links: PhysicsLink[] }) {
        if (state.initialized) return
        for (const n of initial.nodes) state.nodes.set(n.id, { ...n })
        for (const l of initial.links) state.links.set(l.id, { ...l })
        state.initialized = true
        // d3.forceSimulation wiring will be added in later tasks
    }

    return {
        state,
        bootstrap
    }
}

export type PhysicsStore = ReturnType<typeof usePhysicsStore>