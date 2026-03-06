/* eslint-disable @typescript-eslint/no-empty-object-type */
import { defineStore } from 'pinia'
import { useSelectionStore } from './selectionStore.js'
import type { SelectionEntry } from '../logic/selectionManager.js'
import { createHudManager } from '../logic/hudManager.js'

declare global {
    interface Window { _unocHudInstalled?: boolean }
    interface UnocLinkToolStateEvent extends CustomEvent<{ active: boolean }> { }
    interface UnocDragStateEvent extends CustomEvent<{ active: boolean; multi?: boolean; count?: number }> { }
    interface UnocLayoutStacksEvent extends CustomEvent<{ undo: number; redo: number }> { }
}

export interface HudEntry { id: string; label: string; detail?: string; dynamic?: () => string }

// Manager using selection provider to avoid tight coupling in tests
const hudManager = createHudManager(() => {
    try { return useSelectionStore().items as SelectionEntry[] } catch { return [] }
})

export const useInteractionHudStore = defineStore('interactionHud', {
    state: () => hudManager.state,
    actions: {
        ensureBaseEntries: hudManager.ensureBaseEntries,
        toggleVisible(force?: boolean) { hudManager.toggleVisible(force); localStorage.setItem('hudVisible', hudManager.state.visible ? '1' : '0') },
        activity: hudManager.activity,
        setLinkTool: hudManager.setLinkTool,
        setDragState: hudManager.setDragState,
        setUndoRedo: hudManager.setUndoRedo,
    }
})

// Global listeners wiring (called once from root)
export function installInteractionHudGlobal() {
    const store = useInteractionHudStore()
    if (window._unocHudInstalled) return
    window._unocHudInstalled = true
    // restore persisted visibility
    const persisted = localStorage.getItem('hudVisible')
    if (persisted === '1') store.visible = true
    window.addEventListener('keydown', (e) => {
        if (e.key === '?') { store.toggleVisible(); e.preventDefault() }
        if (store.visible) store.activity()
    })
    window.addEventListener('mousemove', () => store.activity())
    window.addEventListener('unoc:linkToolState', (e: Event) => { const ev = e as UnocLinkToolStateEvent; store.setLinkTool(!!ev.detail.active) })
    window.addEventListener('unoc:dragState', (e: Event) => { const ev = e as UnocDragStateEvent; store.setDragState(ev.detail) })
    window.addEventListener('unoc:layoutStacks', (e: Event) => { const ev = e as UnocLayoutStacksEvent; store.setUndoRedo(ev.detail.undo > 0, ev.detail.redo > 0) })
}
