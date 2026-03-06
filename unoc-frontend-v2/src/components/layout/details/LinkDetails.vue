<template>
    <div class="link-details">
        <div class="title-row">
            <span class="name" :title="link.id">Link</span>
            <span class="badge status" :data-status="(link as any).effective_status || link.status">{{ (link as any).effective_status || link.status }}</span>
        </div>
        <div class="meta-list">
            <div v-for="p in linkProps" :key="p.key" class="row">
                <label>{{ p.key }}</label>
                <span>{{ p.value }}</span>
            </div>
            <div class="row"><label>Utilization</label><span>{{ linkUtilText }}</span></div>
            <div class="row"><label>Throughput</label><span>{{ linkBpsText }}</span></div>
        </div>
        <div class="actions">
            <button class="btn sm" :disabled="overrideWorking" @click="forceDown">Force DOWN</button>
            <button
class="btn sm secondary" :disabled="overrideWorking || !link.admin_override_status"
                @click="clearOverride">Clear Override</button>
        </div>
        <div class="properties">
            <div class="optical-section">
                <div class="section-title">Optical / Physical Parameters</div>
                <div class="form-grid">
                    <label for="lenkm">Length (km)</label>
                    <input id="lenkm" v-model.number="linkLenKm" type="number" step="0.01" min="0" />
                    <div v-if="linkLenKmInvalid" class="field-error">Length must be ≥ 0</div>

                    <label for="pmed">Physical Medium</label>
                    <select id="pmed" v-model.number="linkPhysicalMediumId" :disabled="allowedMediaLoading">
                        <option :value="0">—</option>
                        <option v-for="m in allowedMedia" :key="m.id" :value="m.id">{{ m.name }} ({{ m.code }})</option>
                    </select>
                    <div v-if="allowedMediaError" class="field-error">{{ allowedMediaError }}</div>

                    <div></div>
                    <div>
                        <button class="btn sm" :disabled="!canUpdateLink" @click="commitLinkUpdate">Save</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useLinkProps } from '../../../composables/useLinkProps.js'
import { useLinkMetricsView } from '../../../composables/useLinkMetricsView.js'
import { useLinkOpticalEdit } from '../../../composables/useLinkOpticalEdit.js'
import { type Link as LinkModel } from '../../../stores/linksStore.js'
import { useLinksStore } from '../../../stores/linksStore.js'
import { useToastStore } from '../../../stores/toastStore.js'

const props = defineProps<{ link: LinkModel }>()
const linksStore = useLinksStore()
const toasts = useToastStore()

// Meta properties via existing composable
const { linkProps } = useLinkProps(computed(() => props.link))

// Live metrics view via composable
const { linkUtilText, linkBpsText } = useLinkMetricsView(computed(() => props.link.id))

// Optical/physical edit via composable
const {
    linkLenKm,
    linkPhysicalMediumId,
    allowedMedia,
    allowedMediaLoading,
    allowedMediaError,
    linkLenKmInvalid,
    canUpdateLink,
    commitLinkUpdate,
} = useLinkOpticalEdit(computed(() => props.link))

// Override actions
const overrideWorking = ref(false)
async function forceDown() {
    overrideWorking.value = true
    try {
        await linksStore.setOverride(props.link.id, 'DOWN')
        toasts.push('Link override set: DOWN', 'success')
    } catch (e) {
        const msg = (e as Error)?.message || 'Override failed'
        toasts.push(msg, 'error')
    } finally {
        overrideWorking.value = false
    }
}
async function clearOverride() {
    overrideWorking.value = true
    try {
        await linksStore.setOverride(props.link.id, null)
        toasts.push('Link override cleared', 'success')
    } catch (e) {
        const msg = (e as Error)?.message || 'Override clear failed'
        toasts.push(msg, 'error')
    } finally {
        overrideWorking.value = false
    }
}
</script>

<style scoped>
.link-details {
    display: flex;
    flex-direction: column;
    gap: .9rem;
    min-width: 0;
}

.title-row {
    display: flex;
    align-items: center;
    gap: .5rem;
    flex-wrap: wrap;
    min-width: 0;
}

.name {
    font-weight: 600;
    font-size: .95rem;
}

.badge.status {
    font-size: .6rem;
    padding: .25rem .45rem;
    border-radius: 999px;
    background: #444;
    text-transform: uppercase;
    letter-spacing: .5px;
}

.badge.status[data-status="UP"] {
    background: #1b5e20;
    color: #fff;
}

.badge.status[data-status="DOWN"] {
    background: #b71c1c;
    color: #fff;
}

.badge.status[data-status="DEGRADED"] {
    background: #ef6c00;
    color: #fff;
}

.meta-list {
    display: flex;
    flex-direction: column;
    gap: .25rem;
    font-size: .65rem;
    min-width: 0;
}

.meta-list .row {
    display: grid;
    grid-template-columns: 90px 1fr;
    gap: .35rem;
    min-width: 0;
}

.meta-list label {
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .4px;
    font-size: .55rem;
    color: var(--color-text-dim);
}

.properties {
    border-top: 1px solid var(--color-border);
    padding-top: .6rem;
    font-size: .6rem;
    display: flex;
    flex-direction: column;
    gap: .6rem;
    min-width: 0;
}

.optical-section {
    border-top: 1px solid var(--color-border);
    padding-top: .6rem;
    min-width: 0;
}

.optical-section .section-title {
    font-weight: 600;
    font-size: .7rem;
    color: var(--color-text-dim);
    margin-bottom: .25rem;
}

.form-grid {
    display: grid;
    grid-template-columns: 150px 1fr;
    gap: .35rem .5rem;
    margin-top: .4rem;
    min-width: 0;
}

.form-grid input,
.form-grid select {
    background: #222;
    border: 1px solid #444;
    color: #eee;
    padding: .25rem .4rem;
    font-size: .65rem;
    border-radius: 4px;
    box-sizing: border-box;
    width: 100%;
    max-width: 100%;
}

.field-error {
    grid-column: 2 / span 1;
    color: #ef9a9a;
    font-size: .55rem;
    margin-top: -.2rem;
}

.btn {
    background: #2e2e2e;
    border: 1px solid #555;
    color: #ddd;
    cursor: pointer;
    padding: .3rem .55rem;
    font-size: .6rem;
    border-radius: 4px;
}

.btn.sm {
    font-size: .6rem;
    padding: .25rem .5rem;
}
</style>
