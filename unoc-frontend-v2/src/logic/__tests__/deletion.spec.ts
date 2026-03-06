import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDevicesStore } from '../../stores/devicesStore'
import { useLinksStore } from '../../stores/linksStore'
import { useSelectionStore } from '../../stores/selectionStore'
import { useToastStore } from '../../stores/toastStore'
import { useDeletion } from '../../composables/useDeletion'

// Helper to create a mock device
function device(id: string, type = 'CORE_ROUTER') {
    return { id, name: id, role: 'active', status: 'UP', type } as any
}

function link(a: string, b: string) {
    const ordered = [a, b].sort()
    return { id: `${ordered[0]}__${ordered[1]}`, a_device_id: ordered[0], b_device_id: ordered[1], a_interface_id: `${ordered[0]}-if0`, b_interface_id: `${ordered[1]}-if0`, status: 'UP', kind: 'FIBER' } as any
}

describe('Deletion logic with linked devices (cascade link removal)', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    it('auto-removes links of a selected single device (cascade) and deletes device', async () => {
        const devices = useDevicesStore()
        const links = useLinksStore()
        const selection = useSelectionStore()
        const _toasts = useToastStore()
        const deletion = useDeletion()

        devices.devices = [device('a'), device('b')]
        links.links = [link('a', 'b')]
        // mock backend deletes: first link delete(s) then device
        const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((input: any, _init: any) => {
            const url = typeof input === 'string' ? input : input.toString()
            if (url.includes('/api/links/')) return Promise.resolve(new Response(null, { status: 204 }))
            if (url.includes('/api/devices/')) return Promise.resolve(new Response(null, { status: 204 }))
            return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }))
        })
        selection.toggle('a', 'device', false)
        const result = await deletion.deleteSelectedDevices()
        expect(result.failed).toHaveLength(0)
        expect(result.removed).toContain('a')
        // device a removed, link removed
        expect(devices.devices.find(d => d.id === 'a')).toBeFalsy()
        expect(links.links.find(l => l.a_device_id === 'a' || l.b_device_id === 'a')).toBeFalsy()
        fetchSpy.mockRestore()
    })

    it('deletes device after its links are removed', async () => {
        const devices = useDevicesStore()
        const links = useLinksStore()
        const selection = useSelectionStore()
        const deletion = useDeletion()

        devices.devices = [device('x'), device('y')]
        // initially linked
        links.links = [link('x', 'y')]
        selection.toggle('x', 'device', false)

        // First attempt should be blocked
        await deletion.deleteSelectedDevices()
        expect(devices.devices.find(d => d.id === 'x')).toBeTruthy()

        // Remove link then retry
        links.links = []
        // mock fetch delete success
        const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }))
        // Ensure device x is selected (use select to avoid toggling off)
        if (!selection.items.find(i => i.kind === 'device' && i.id === 'x')) {
            ; (selection as any).select('x', 'device', false)
        } else {
            // re-select explicitly to update lastUpdated if needed
            ; (selection as any).select('x', 'device', false)
        }
        const result2 = await deletion.deleteSelectedDevices()
        expect(result2.removed).toContain('x')
        expect(devices.devices.find(d => d.id === 'x')).toBeFalsy()
        fetchSpy.mockRestore()
    })

    it('removes only links touching selected devices and deletes all selected (multi-select cascade)', async () => {
        const devices = useDevicesStore()
        const links = useLinksStore()
        const selection = useSelectionStore()
        const deletion = useDeletion()

        devices.devices = [device('a'), device('b'), device('c')]
        links.links = [link('a', 'b')]

        selection.toggle('a', 'device', false)
        selection.toggle('b', 'device', true)
        selection.toggle('c', 'device', true)
        const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((input: any) => {
            const url = typeof input === 'string' ? input : input.toString()
            if (url.includes('/api/links/')) return Promise.resolve(new Response(null, { status: 204 }))
            if (url.includes('/api/devices/')) return Promise.resolve(new Response(null, { status: 204 }))
            return Promise.resolve(new Response(null, { status: 200 }))
        })
        const result = await deletion.deleteSelectedDevices()
        expect(result.failed).toHaveLength(0)
        expect(result.removed.sort()).toEqual(['a', 'b', 'c'])
        expect(devices.devices.length).toBe(0)
        expect(links.links.length).toBe(0)
        fetchSpy.mockRestore()
    })

    it('deletes a single unlinked device directly', async () => {
        const devices = useDevicesStore()
        const links = useLinksStore()
        const selection = useSelectionStore()
        const deletion = useDeletion()
        devices.devices = [device('solo'), device('other')]
        links.links = []
        selection.toggle('solo', 'device', false)
        const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }))
        const result = await deletion.deleteSelectedDevices()
        expect(result.removed).toContain('solo')
        expect(devices.devices.find(d => d.id === 'solo')).toBeFalsy()
        fetchSpy.mockRestore()
    })
})
