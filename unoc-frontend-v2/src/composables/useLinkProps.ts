import { computed, type ComputedRef } from 'vue'

type LinkBasic = {
    id: string
    kind: string
    status: string
    a_device_id: string
    b_device_id: string
}

export function useLinkProps(activeLink: ComputedRef<LinkBasic | null>) {
    const linkProps = computed(() => {
        const l = activeLink.value
        if (!l) return [] as { key: string; value: string }[]
        return [
            { key: 'ID', value: l.id },
            { key: 'Typ', value: l.kind },
            { key: 'Status', value: l.status },
            { key: 'A Gerät', value: l.a_device_id },
            { key: 'B Gerät', value: l.b_device_id },
        ]
    })

    return { linkProps }
}
