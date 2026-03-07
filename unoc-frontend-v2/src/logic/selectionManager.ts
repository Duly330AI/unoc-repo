export type SelectableKind = 'device' | 'link'
export interface SelectionEntry { id: string; kind: SelectableKind }
export interface SelectionState { items: SelectionEntry[]; lastUpdated: number }

export function createSelectionManager(now: () => number = () => Date.now()) {
    const state: SelectionState = { items: [], lastUpdated: now() }
    function select(id: string, kind: SelectableKind = 'device', multi = false) { if (!multi) state.items = []; if (!state.items.some(e => e.id === id && e.kind === kind)) state.items.push({ id, kind }); state.lastUpdated = now() }
    function toggle(id: string, kind: SelectableKind = 'device', multi = false) { if (!multi) { const already = state.items.length === 1 && state.items[0].id === id && state.items[0].kind === kind; state.items = already ? [] : [{ id, kind }] } else { const idx = state.items.findIndex(e => e.id === id && e.kind === kind); if (idx >= 0) state.items.splice(idx, 1); else state.items.push({ id, kind }) } state.lastUpdated = now() }
    function clear() { state.items = []; state.lastUpdated = now() }
    function isSelected(id: string, kind: SelectableKind = 'device') { return state.items.some(e => e.id === id && e.kind === kind) }
    return { state, select, toggle, clear, isSelected }
}
