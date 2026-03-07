import type { HudEntry } from '../stores/interactionHudStore.js'
// Lightweight selection entry subset to avoid import cycle
export interface SelectionEntry { id: string; kind: 'device' | 'link' | string }

export interface HudManagerState {
    visible: boolean
    lastActivity: number
    autoHideMs: number
    entries: HudEntry[]
    linkToolActive: boolean
    dragInfo: { active: boolean; multi: boolean; count: number }
    undoAvailable: boolean
    redoAvailable: boolean
}

export interface HudManager {
    state: HudManagerState
    ensureBaseEntries(): void
    toggleVisible(force?: boolean): void
    activity(): void
    setLinkTool(active: boolean): void
    setDragState(info: { active: boolean; multi?: boolean; count?: number }): void
    setUndoRedo(undo: boolean, redo: boolean): void
}

export function createHudManager(selectionProvider: () => SelectionEntry[]): HudManager {
    const state: HudManagerState = {
        visible: false,
        lastActivity: 0,
        autoHideMs: 6500,
        entries: [],
        linkToolActive: false,
        dragInfo: { active: false, multi: false, count: 0 },
        undoAvailable: false,
        redoAvailable: false,
    }

    function ensureBaseEntries() {
        const items = selectionProvider()
        const deviceCount = items.filter(i => i.kind === 'device').length
        const linkCount = items.filter(i => i.kind === 'link').length
        const selectionDetail = (deviceCount || linkCount) ? `${deviceCount} Dev / ${linkCount} Link` : '0'
        const base: HudEntry[] = [
            { id: 'help-shortcut', label: '? – HUD umschalten' },
            { id: 'link-mode', label: 'K – Link Tool', detail: state.linkToolActive ? 'AKTIV' : 'inaktiv' },
            { id: 'link-create', label: 'L – Link zwischen 2 selektierten' },
            { id: 'undo', label: 'Undo / Redo', detail: `${state.undoAvailable ? '✔' : '–'}/${state.redoAvailable ? '✔' : '–'}` },
            { id: 'selection', label: 'Auswahl', detail: selectionDetail },
            { id: 'esc', label: 'Esc – abbrechen / nur Links leeren' },
        ]
        if (state.dragInfo.active) {
            base.push({ id: 'drag', label: state.dragInfo.multi ? `Drag (${state.dragInfo.count} Nodes)` : 'Drag (1 Node)' })
        }
        state.entries = base
    }

    function toggleVisible(force?: boolean) {
        state.visible = typeof force === 'boolean' ? force : !state.visible
        state.lastActivity = Date.now()
        ensureBaseEntries()
    }
    function activity() {
        state.lastActivity = Date.now()
        if (!state.visible) return
        ensureBaseEntries()
    }
    function setLinkTool(active: boolean) { state.linkToolActive = active; activity() }
    function setDragState(info: { active: boolean; multi?: boolean; count?: number }) {
        state.dragInfo = { active: info.active, multi: !!info.multi, count: info.count || 0 }
        activity()
    }
    function setUndoRedo(undo: boolean, redo: boolean) { state.undoAvailable = undo; state.redoAvailable = redo; activity() }

    return { state, ensureBaseEntries, toggleVisible, activity, setLinkTool, setDragState, setUndoRedo }
}
