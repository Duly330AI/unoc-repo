import { computed, ref, watch, type ComputedRef } from 'vue'
import { useLinksStore, type Link as LinkModel } from '../stores/linksStore.js'
import { useToastStore } from '../stores/toastStore.js'

export type PhysicalMedium = {
  id: number
  code: string
  name: string
  kind: string
  max_range_km: number | null
}

export function useLinkOpticalEdit(link: ComputedRef<LinkModel | null | undefined>) {
  const links = useLinksStore()
  const toasts = useToastStore()

  const linkLenKm = ref<number | null>(null)
  const linkPhysicalMediumId = ref<number>(0)
  const allowedMedia = ref<PhysicalMedium[]>([])
  const allowedMediaLoading = ref(false)
  const allowedMediaError = ref('')
  const linkLenKmInvalid = computed(() => linkLenKm.value != null && linkLenKm.value < 0)
  const canUpdateLink = computed(() => !!link.value && !linkLenKmInvalid.value)

  async function fetchAllowedMedia(linkId: string) {
    allowedMediaError.value = ''
    allowedMediaLoading.value = true
    try {
      const resp = await fetch(`/api/physical/allowed-media/by-link/${encodeURIComponent(linkId)}`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const arr = (await resp.json()) as PhysicalMedium[]
      allowedMedia.value = Array.isArray(arr) ? arr : []
    } catch (e) {
      const msg = (e as Error)?.message || 'Failed to load allowed media'
      allowedMediaError.value = msg
      allowedMedia.value = []
    } finally {
      allowedMediaLoading.value = false
    }
  }

  async function commitLinkUpdate() {
    const l = link.value
    if (!l) return
    const patch: Record<string, unknown> = {}
    if (linkLenKm.value != null) patch.length_km = linkLenKm.value
    patch.physical_medium_id = linkPhysicalMediumId.value > 0 ? linkPhysicalMediumId.value : null
    try {
      await links.update(l.id, patch as { length_km?: number; physical_medium_id?: number | null })
      toasts.push('Link updated', 'success')
    } catch (e) {
      const msg = (e as Error)?.message || 'Update failed'
      toasts.push(msg, 'error')
      console.warn('Update link failed', e)
    }
  }

  watch(
    link,
    (l) => {
      const ll = l as unknown as LinkModel | null
      linkLenKm.value = (ll?.length_km ?? null) as number | null
      type LinkWithMedium = LinkModel & { physical_medium_id?: number | null }
      const pmid = (ll as LinkWithMedium)?.physical_medium_id as number | null | undefined
      linkPhysicalMediumId.value = pmid ?? 0
      if (ll?.id) void fetchAllowedMedia(ll.id)
    },
    { immediate: true }
  )

  return {
    linkLenKm,
    linkPhysicalMediumId,
    allowedMedia,
    allowedMediaLoading,
    allowedMediaError,
    linkLenKmInvalid,
    canUpdateLink,
    fetchAllowedMedia,
    commitLinkUpdate
  }
}
