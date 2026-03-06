# Port Summary Bulk Optimization - Implementation Guide

## Problem

Nach Bulk-Provisioning von 64 ONTs entstehen **64 parallele HTTP requests** zu `/api/ports/summary/{id}`, was zu:

- Rate-Limit exhaustion (10/min → 54 blocked requests)
- Browser queue explosion (~40 pending requests)
- 3-5 Sekunden Ladezeit
- 186 DB queries (3 per device)

## Solution Status

### ✅ Phase A - Backend (COMPLETE)

**Files:** `backend/api/endpoints/ports.py`

**Changes:**

1. Rate limits increased:

   - Single endpoint: 10/min → 100/min (Line 149)
   - Bulk endpoint: 10/min → 50/min (Line 334)

2. Bulk endpoint rewritten (Lines 336-492):
   - **Before:** Loop calling single endpoint (N×3 queries)
   - **After:** Batch-fetch pattern (3 total queries)
   - **Optimization:** Batch ALL devices, ALL interfaces, ALL links
   - **Performance:** 33ms for 2 devices, 0 SQL queries (cache proof)

### ⏳ Phase B - Frontend (IN PROGRESS)

**Created:** `unoc-frontend-v2/src/composables/useBulkPortSummary.ts`

## How to Use Bulk Composable

### Example 1: Replace Single Calls with Bulk

**Before (inefficient - 64 HTTP requests):**

```vue
<script setup>
import { usePortSummary } from '@/composables/usePortSummary'

// Component renders 64 device widgets
const devices = ref(['dev1', 'dev2', ..., 'dev64'])

// Each widget calls usePortSummary independently
const widgets = devices.value.map(id => usePortSummary(id))
// → 64 parallel HTTP requests!
</script>
```

**After (efficient - 1 HTTP request):**

```vue
<script setup>
import { useBulkPortSummary } from '@/composables/useBulkPortSummary'

const devices = ref(['dev1', 'dev2', ..., 'dev64'])

// ONE bulk fetch for all devices
const { summaries, loading, error } = useBulkPortSummary(devices)

// summaries.value = {
//   'dev1': [{ id: 'if1', name: 'eth0', occupancy: 0.8, ... }],
//   'dev2': [{ id: 'if2', name: 'eth0', occupancy: 0.3, ... }],
//   ...
// }
</script>

<template>
  <div v-for="deviceId in devices" :key="deviceId">
    <DeviceWidget :device-id="deviceId" :interfaces="summaries[deviceId] || []" />
  </div>
</template>
```

### Example 2: Provisioning Completion Handler

**Scenario:** User bulk-provisions 64 ONTs, UI needs to reload Port Summaries

**File:** `unoc-frontend-v2/src/stores/devicesStore.ts`

```typescript
// Add to devicesStore
import { useBulkPortSummary } from '@/composables/useBulkPortSummary';

export const useDevicesStore = defineStore('devices', () => {
  const devices = ref<Device[]>([]);

  // Track IDs of recently provisioned devices
  const recentlyProvisioned = ref<string[]>([]);

  // Bulk composable for provisioned devices
  const { summaries: provisionedSummaries, refetch: refetchProvisioned } = useBulkPortSummary(
    recentlyProvisioned,
    0
  ); // pollMs=0 (manual refetch only)

  async function bulkProvision(deviceIds: string[]) {
    // Call backend bulk provision
    await fetch('/api/devices/bulk-provision', {
      method: 'POST',
      body: JSON.stringify({ ids: deviceIds }),
    });

    // Refresh Port Summaries in bulk (not 64 singles!)
    recentlyProvisioned.value = deviceIds;
    await refetchProvisioned();

    // Show toast
    toast.show(`${deviceIds.length} devices provisioned`, 'success');
  }

  return { devices, bulkProvision, provisionedSummaries };
});
```

### Example 3: Large-Scale (1000+ Devices)

**Batching for scale:**

```typescript
export function useBulkPortSummary(deviceIds: Ref<string[]>, pollMs = 2000) {
  const BATCH_SIZE = 100; // Chunk into 100-device batches

  async function fetchBatched() {
    const ids = deviceIds.value;
    const results: Record<string, InterfaceSummary[]> = {};

    // Split into batches of 100
    for (let i = 0; i < ids.length; i += BATCH_SIZE) {
      const batch = ids.slice(i, i + BATCH_SIZE);
      const params = batch.map((id) => `ids=${encodeURIComponent(id)}`).join('&');
      const resp = await fetch(`/api/ports/summary?${params}`);
      const data = await resp.json();
      Object.assign(results, data);
    }

    summaries.value = results;
  }
}
```

**Performance:**

- 1000 devices → 10 HTTP requests (vs 1000 singles)
- 10 requests × ~100ms = 1 second total (vs impossible with singles)
- Rate limit: 50/minute supports 10 requests easily

## Finding the Bottleneck Source

### Where to Look

**1. Check for v-for loops rendering Port Summaries:**

```bash
# Search for patterns like:
grep -r "v-for.*usePortSummary" unoc-frontend-v2/src/
grep -r "devices.map.*usePortSummary" unoc-frontend-v2/src/
```

**2. Check provisioning completion handlers:**

```bash
# Look for where provisioning triggers reloads:
grep -r "after.*provision\|provision.*complete" unoc-frontend-v2/src/
```

**3. Check dashboard/overview pages:**

```bash
# Look for pages showing many devices:
find unoc-frontend-v2/src/views -name "*Dashboard*" -o -name "*Overview*"
```

**4. Check for reactive device list watchers:**

```typescript
// Pattern: watch devices list and fetch Port Summaries
watch(
  () => devicesStore.devices,
  (newDevices) => {
    newDevices.forEach((d) => {
      // BUG: Creates 64 parallel requests!
      usePortSummary(d.id);
    });
  }
);
```

### Debug Strategy

**1. Add console.log to usePortSummary:**

```typescript
// unoc-frontend-v2/src/composables/usePortSummary.ts
export function usePortSummary(deviceId: Ref<string> | string, pollMs = 2000) {
  console.trace('[usePortSummary] Called for device:', deviceId); // Shows call stack
  // ...rest of code
}
```

**2. Reproduce scenario:**

- Generate 64 ONTs
- Bulk provision all 64
- Watch Network tab
- Check console for 64 trace logs → see where calls originate

**3. Replace with bulk:**

- Find parent component causing 64 calls
- Replace individual `usePortSummary` with single `useBulkPortSummary`

## Migration Checklist

- [x] Backend bulk endpoint optimized (3 queries total)
- [x] Backend rate limits increased (100/min single, 50/min bulk)
- [x] Backend tested (33ms, 0 SQL queries proof)
- [x] Frontend bulk composable created
- [ ] **TODO:** Find where 64 parallel calls originate
- [ ] **TODO:** Replace with bulk composable
- [ ] **TODO:** Test with 64 ONTs scenario
- [ ] **TODO:** Verify Network tab shows 1 request (not 64)
- [ ] **TODO:** Test with 1000+ devices (batching)

## Performance Targets

| Metric            | Before     | After     | Improvement |
| ----------------- | ---------- | --------- | ----------- |
| HTTP Requests     | 64         | 1         | 64×         |
| DB Queries        | 192 (3×64) | 3         | 64×         |
| Response Time     | 3-5s       | <100ms    | 30-50×      |
| Rate Limit Blocks | 54/64      | 0/64      | ∞           |
| Browser Queue     | 40 pending | 0 pending | ∞           |

## Next Steps

1. **Find bottleneck source** (add console.trace to usePortSummary)
2. **Replace with bulk** (parent component level)
3. **Test with user scenario** (64 ONTs bulk provisioning)
4. **Validate scale** (1000+ devices with batching)
5. **Document usage** (update component docs)

## Contact

If you find the bottleneck source, update this document with:

- File path
- Component name
- Line number
- Migration example

Then the bulk optimization can be completed!
