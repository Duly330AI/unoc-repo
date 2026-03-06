import { useSelectionStore } from '../stores/selectionStore.js'
import { useDevicesStore } from '../stores/devicesStore.js'
import { useLinksStore } from '../stores/linksStore.js'
import { useToastStore } from '../stores/toastStore.js'
import type { DeviceOut } from '../types/domain.js'
import type { Link as LinkModel } from '../stores/linksStore.js'

interface DeleteResult { removed: string[]; failed: { id: string; error: string }[] }

export function useDeletion() {
    const selection = useSelectionStore()
    const devices = useDevicesStore()
    const links = useLinksStore()
    const toasts = useToastStore()

    async function deleteSelectedDevices(): Promise<DeleteResult> {
        const deviceIds = selection.items.filter(i => i.kind === 'device').map(i => i.id)
        if (!deviceIds.length) return { removed: [], failed: [] }

        // Collect all links touching any selected device (cascade removal)
        const affectedLinks = links.links.filter((l: LinkModel) => deviceIds.includes(l.a_device_id) || deviceIds.includes(l.b_device_id))
        const linkIds = affectedLinks.map((l: LinkModel) => l.id)

        const pendingId = toasts.pending(`Entferne ${deviceIds.length} Gerät(e)${linkIds.length ? ` & ${linkIds.length} Link(s)` : ''}…`)

        // 1. Delete links first (order matters for backend referential integrity)
        const failedLinks: string[] = []
        for (const lid of linkIds) {
            try {
                const resp = await fetch(`/api/links/${encodeURIComponent(lid)}`, { method: 'DELETE' })
                if (resp.status !== 204 && resp.status !== 404) {
                    failedLinks.push(lid)
                }
            } catch { failedLinks.push(lid) }
        }
        if (failedLinks.length) {
            // Remove only successfully deleted links from client cache
            const successLinkIds = linkIds.filter(id => !failedLinks.includes(id))
            if (successLinkIds.length) {
                links.links = links.links.filter((l) => !successLinkIds.includes(l.id))
            }
            toasts.push(`Einige Links konnten nicht gelöscht werden (${failedLinks.length}/${linkIds.length}). Geräte-Löschung wird fortgesetzt.`, 'warn')
        } else if (linkIds.length) {
            links.links = links.links.filter((l) => !linkIds.includes(l.id))
        }
        // Remove link selections for any removed links
        selection.items = selection.items.filter(i => !(i.kind === 'link' && linkIds.includes(i.id)))

        // 2. Delete devices
        const removed: string[] = []
        const failed: { id: string; error: string }[] = []
        for (const id of deviceIds) {
            try {
                const resp = await fetch(`/api/devices/${encodeURIComponent(id)}`, { method: 'DELETE' })
                if (resp.status === 204) { removed.push(id); continue }
                if (resp.status === 404) { // treat 404 as already gone
                    removed.push(id); continue
                }
                failed.push({ id, error: await resp.text() })
            } catch (e: unknown) { failed.push({ id, error: e instanceof Error ? e.message : String(e) }) }
        }

        if (removed.length) {
            devices.devices = devices.devices.filter((d: DeviceOut) => !removed.includes(d.id))
        }

        if (failed.length) {
            toasts.fail(pendingId, `Geräte teils gelöscht (${removed.length} ok / ${failed.length} Fehler${linkIds.length ? `, ${linkIds.length - failedLinks.length}/${linkIds.length} Links entfernt` : ''})`)
        } else {
            toasts.succeed(pendingId, `${removed.length} Gerät(e) gelöscht${linkIds.length ? ` (${linkIds.length - failedLinks.length} Link(s) entfernt)` : ''}`)
        }

        selection.items = selection.items.filter(i => !(i.kind === 'device' && removed.includes(i.id)))
        selection.lastUpdated = Date.now()
        return { removed, failed }
    }

    async function deleteSelectedLinks(): Promise<DeleteResult> {
        const ids = selection.items.filter(i => i.kind === 'link').map(i => i.id)
        if (!ids.length) return { removed: [], failed: [] }
        const pendingId = toasts.pending(`Lösche ${ids.length} Link(s)…`)
        const removed: string[] = []
        const failed: { id: string; error: string }[] = []
        for (const id of ids) {
            try {
                const resp = await fetch(`/api/links/${encodeURIComponent(id)}`, { method: 'DELETE' })
                if (resp.status === 204 || resp.status === 404) {
                    // 404 treated as already gone
                    removed.push(id)
                    continue
                }
                failed.push({ id, error: await resp.text() })
            } catch (e: unknown) { failed.push({ id, error: e instanceof Error ? e.message : String(e) }) }
        }
        if (removed.length) {
            links.links = links.links.filter((l) => !removed.includes(l.id))
        }
        if (failed.length) { toasts.fail(pendingId, `Links teils gelöscht (${removed.length} ok / ${failed.length} Fehler)`) }
        else { toasts.succeed(pendingId, `${removed.length} Link(s) gelöscht`) }
        selection.items = selection.items.filter(i => !(i.kind === 'link' && removed.includes(i.id)))
        selection.lastUpdated = Date.now()
        return { removed, failed }
    }

    return { deleteSelectedDevices, deleteSelectedLinks }
}
