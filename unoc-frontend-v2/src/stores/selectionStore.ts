import { defineStore } from 'pinia'
import type { SelectionEntry, SelectableKind } from '../logic/selectionManager.js'

// Internal reactive implementation (avoids external object re-wrapping issues)
export const useSelectionStore = defineStore('selection', {
    state: () => ({
        items: [] as SelectionEntry[],
        lastUpdated: Date.now()
    }),
    getters: {
        isSelected: (state) => (id: string, kind: SelectableKind = 'device') => state.items.some((e: SelectionEntry) => e.id === id && e.kind === kind)
    },
    actions: {
        select(id: string, kind: SelectableKind = 'device', multi = false) {
            if (!multi) this.items = []
            if (!this.items.some((e: SelectionEntry) => e.id === id && e.kind === kind)) this.items.push({ id, kind })
            this.lastUpdated = Date.now()
        },
        toggle(id: string, kind: SelectableKind = 'device', multi = false) {
            if (!multi) {
                const already = this.items.length === 1 && this.items[0].id === id && this.items[0].kind === kind
                this.items = already ? [] : [{ id, kind }]
            } else {
                const idx = this.items.findIndex((e: SelectionEntry) => e.id === id && e.kind === kind)
                if (idx >= 0) this.items.splice(idx, 1); else this.items.push({ id, kind })
            }
            this.lastUpdated = Date.now()
        },
        clear() {
            this.items = []
            this.lastUpdated = Date.now()
        }
    }
})
