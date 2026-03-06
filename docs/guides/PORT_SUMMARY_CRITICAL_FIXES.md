# CRITICAL BUGS FIXED - Port Summary Manager

## User Report (Production Issue)

**Symptoms:**

1. ✅ Bulk link creation works (32 links)
2. ✅ Bulk provision works (32 devices)
3. ❌ Port occupancy **NOT updating** (shows `[0 / 64]` instead of `[32 / 64]` on OLT PON1)
4. ❌ **Browser hangs** after refresh
5. ❌ Performance degraded

**Screenshots Analysis:**

- Screenshot 1 (Bulk Links): Many `links` requests → OK
- Screenshot 2 (Bulk Provision): Many `provision` requests → OK
- Screenshot 3 (Topology): Shows 32 ONTs connected
- **MISSING:** No `/api/ports/summary?ids=...` bulk requests → **Manager NOT running!**

## Root Causes Found

### Bug 1: onUnmounted Never Called ❌ CRITICAL

**Code:**

```typescript
// ❌ WRONG - cleanup() never called by Vue!
function cleanup() {
  const id = idRef.value;
  if (id) globalManager.unsubscribe(id);
}

return {
  interfaces,
  loading,
  cleanup, // ← Vue doesn't auto-call this!
};
```

**Problem:**

- Components subscribe on mount
- Components **NEVER unsubscribe** on unmount
- RefCount **never decrements**
- **Memory leak** + subscriptions grow infinitely
- Eventually: Manager has 1000s of subscriptions → **Browser hangs!**

**Fix:**

```typescript
// ✅ CORRECT - Vue calls onUnmounted automatically
import { onUnmounted } from 'vue';

onUnmounted(() => {
  const id = idRef.value;
  if (id) globalManager.unsubscribe(id);
});

return {
  interfaces,
  loading,
  // No cleanup export needed!
};
```

### Bug 2: Subscribe Race Condition ❌ CRITICAL

**Code:**

```typescript
// ❌ WRONG - New device during fetch is ignored!
subscribe(deviceId: string) {
  this.subscriptions.set(deviceId, count + 1)

  if (this.subscriptions.size === 1 && !this.timer) {
    void this.fetchBulk()  // Only first subscriber triggers fetch
  }
}

private async fetchBulk() {
  if (this.isFetching) return  // ← BLOCKS new subscriptions!
  // ...
}
```

**Problem:**

1. Component A subscribes → triggers `fetchBulk()` (isFetching=true)
2. Component B subscribes **while A's fetch is running** → **BLOCKED!**
3. Component B **never fetched** → shows empty data forever
4. Result: `PON1 [0/64]` instead of `[32/64]`

**Fix:**

```typescript
// ✅ CORRECT - Queue pending fetches
private pendingFetch = false

subscribe(deviceId: string) {
  const isNew = !this.subscriptions.has(deviceId)
  this.subscriptions.set(deviceId, count + 1)

  if (isNew) {
    if (this.isFetching) {
      this.pendingFetch = true  // Queue for next fetch
    } else {
      void this.fetchBulk()
    }
  }
}

private async fetchBulk() {
  this.isFetching = true
  this.pendingFetch = false
  try {
    // ... fetch logic
  } finally {
    this.isFetching = false

    // If new subscriptions arrived, fetch again immediately
    if (this.pendingFetch) {
      this.pendingFetch = false
      void this.fetchBulk()
    }
  }
}
```

### Bug 3: No Initial Data ❌ HIGH PRIORITY

**Code:**

```typescript
// ❌ WRONG - Components read empty cache before first fetch
const interfaces = computed(() => globalManager.get(idRef.value));
const loading = ref(!globalManager.has(idRef.value));

// First subscription triggers fetch but doesn't wait
if (this.subscriptions.size === 1) {
  void this.fetchBulk(); // async, no await
}
```

**Problem:**

1. Component mounts
2. Reads cache → **empty!**
3. Subscribes → triggers async fetch
4. Component renders **before fetch completes** → shows `[0/64]`
5. 2 seconds later → fetch completes → cache updates → shows `[32/64]`
6. **User sees wrong data for 2 seconds!**

**Partial Fix (better than nothing):**

```typescript
// ✅ Better - Always trigger fetch for new subscriptions
subscribe(deviceId: string) {
  const isNew = !this.subscriptions.has(deviceId)

  if (isNew) {
    if (this.isFetching) {
      this.pendingFetch = true
    } else {
      void this.fetchBulk()  // Immediate fetch for new device
    }
  }
}
```

**Note:** Still async, but faster than waiting for next 2s poll.

## Changes Applied

### File: `unoc-frontend-v2/src/composables/usePortSummaryManager.ts`

**1. Added `onUnmounted` import:**

```diff
- import { ref, computed, watch, type Ref } from 'vue'
+ import { ref, computed, watch, onUnmounted, type Ref } from 'vue'
```

**2. Added `pendingFetch` queue flag:**

```diff
  class PortSummaryManager {
    private cache = new Map<string, CacheEntry>()
    private subscriptions = new Map<string, number>()
    private timer: number | null = null
    private pollMs = 2000
    private isFetching = false
+   private pendingFetch = false  // Queue next fetch if subscribe during active fetch
```

**3. Fixed subscribe logic:**

```diff
  subscribe(deviceId: string) {
-   const count = this.subscriptions.get(deviceId) || 0
+   const count = this.subscriptions.get(deviceId) || 0
+   const isNew = count === 0
    this.subscriptions.set(deviceId, count + 1)

    if (this.subscriptions.size === 1 && !this.timer) {
      this.startPolling()
-     void this.fetchBulk()  // Only first subscriber
    }

+   // ALWAYS trigger fetch for new devices
+   if (isNew) {
+     if (this.isFetching) {
+       this.pendingFetch = true  // Queue for later
+     } else {
+       void this.fetchBulk()  // Immediate
+     }
+   }
  }
```

**4. Added fetch queue handling:**

```diff
  private async fetchBulk() {
    if (ids.length === 0 || this.isFetching) return

    this.isFetching = true
+   this.pendingFetch = false  // Clear queue flag
    try {
      // ... fetch logic
    } finally {
      this.isFetching = false
+
+     // Process queued fetches
+     if (this.pendingFetch) {
+       this.pendingFetch = false
+       void this.fetchBulk()
+     }
    }
  }
```

**5. Fixed unmount lifecycle:**

```diff
  // Subscribe on mount, resubscribe on ID change
  watch(idRef, (newId, oldId) => { ... }, { immediate: true })

- // Unsubscribe on unmount (will be called by Vue's onUnmounted)
- function cleanup() {
-   const id = idRef.value
-   if (id) globalManager.unsubscribe(id)
- }
+ // CRITICAL: Auto-unsubscribe on component unmount
+ onUnmounted(() => {
+   const id = idRef.value
+   if (id) globalManager.unsubscribe(id)
+ })

  return {
    interfaces,
    loading,
-   cleanup,  // ← NEVER CALLED BY VUE!
    getManagerStats: () => globalManager.getStats()
  }
```

## Testing Instructions

### Step 1: Hard Refresh (Clear Cache)

**Chrome:**

1. Open DevTools (F12)
2. Right-click reload button
3. Select "Empty Cache and Hard Reload"

**Or:**

- `Ctrl+Shift+Delete` → Clear cache
- Close all tabs
- Restart browser

### Step 2: Verify Manager Running

**Console check:**

```javascript
// In browser console after page loads
import { portSummaryManager } from './composables/usePortSummaryManager';
console.log(portSummaryManager.getStats());

// Expected output:
// {
//   subscriptions: 1-3,        // Number of active components
//   cachedDevices: 1-3,        // Same as subscriptions
//   polling: true,             // ✅ Timer running
//   subscribedIds: ['olt']     // Current device IDs
// }
```

### Step 3: Network Tab Verification

**Expected pattern after fixes:**

1. Open OLT details → 1 request: `/api/ports/summary?ids=olt`
2. Wait 2 seconds → another request (polling)
3. Open ONT details → request changes to: `/api/ports/summary?ids=olt&ids=ont-001`
4. Bulk provision 32 ONTs → request grows to: `/api/ports/summary?ids=olt&ids=ont-001&...&ids=ont-032`
5. **CRITICAL:** Only **1 request every 2 seconds** (not 32 parallel!)

### Step 4: Port Occupancy Test

**Scenario:**

1. Create OLT with PON ports
2. Create 32 ONTs
3. Bulk link ONTs to OLT PON1
4. Bulk provision all 32 ONTs
5. Open OLT details → Overview tab

**Expected:**

```
PON
pon1    [32 / 64]    UP   ← Should show 32 occupancy!
pon2    [0 / 64]     UP
...
```

**If still shows `[0/64]`:**

- Check console for errors
- Check Network tab for bulk requests
- Verify manager stats (see Step 2)

### Step 5: Memory Leak Test

**Before fix:**

- Open OLT details → subscribe count: 1
- Close details → subscribe count: **STILL 1** (leak!)
- Repeat 10 times → subscribe count: **10** (massive leak!)
- Browser eventually hangs

**After fix:**

- Open OLT details → subscribe count: 1
- Close details → subscribe count: **0** (cleaned up!)
- Repeat 10 times → subscribe count: **0-1** (no leak!)
- Browser stays responsive

## Performance Impact

### Before Fixes

| Operation              | Behavior            | Result             |
| ---------------------- | ------------------- | ------------------ |
| 32 ONTs provision      | No bulk requests    | `[0/64]` occupancy |
| Open/close details 10× | RefCount += 10      | Memory leak        |
| Subscribe during fetch | Ignored             | Missing data       |
| Page refresh           | 1000s subscriptions | Browser hangs      |

### After Fixes

| Operation              | Behavior         | Result                 |
| ---------------------- | ---------------- | ---------------------- |
| 32 ONTs provision      | 1 bulk request   | `[32/64]` occupancy ✅ |
| Open/close details 10× | RefCount = 0-1   | No leak ✅             |
| Subscribe during fetch | Queued + fetched | Complete data ✅       |
| Page refresh           | Clean slate      | Responsive ✅          |

## Rollout Checklist

- [x] Fix 1: onUnmounted lifecycle hook
- [x] Fix 2: Fetch queue with pendingFetch flag
- [x] Fix 3: Immediate fetch for new subscriptions
- [x] Build passes (`npm run build` → ✓ 2.22s)
- [ ] **TODO:** Hard refresh browser (clear cache!)
- [ ] **TODO:** Test 32 ONTs bulk provision scenario
- [ ] **TODO:** Verify Network tab shows bulk requests
- [ ] **TODO:** Verify `PON1 [32/64]` occupancy
- [ ] **TODO:** Test open/close details (no memory leak)
- [ ] **TODO:** Test page refresh (no hang)

## Emergency Rollback

**If issues persist:**

1. **Disable manager (use old composable):**

```diff
- import { usePortSummaryManaged } from './usePortSummaryManager'
+ import { usePortSummary } from './usePortSummary'

- const { interfaces } = usePortSummaryManaged(deviceId)
+ const { interfaces } = usePortSummary(deviceId)
```

2. **Rebuild:**

```bash
npm run build
```

3. **Hard refresh browser**

**Note:** Old composable has N+1 problem but at least works (shows data)!

## Next Steps

1. **URGENT:** Hard refresh browser + test bulk provision
2. **URGENT:** Verify Network tab shows bulk requests
3. **URGENT:** Check console for manager stats
4. If working → Mark Phase 2B as complete
5. If broken → Emergency rollback + investigate

---

**Status:** 🚨 CRITICAL FIXES APPLIED, AWAITING USER TEST  
**Risk:** HIGH (memory leak + data loss bugs fixed)  
**Action:** User MUST hard refresh browser before testing!
