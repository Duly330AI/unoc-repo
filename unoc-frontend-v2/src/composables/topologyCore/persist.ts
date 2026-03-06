/* eslint-disable @typescript-eslint/no-explicit-any */

export function createPersist(getLayoutCache: () => Record<string, any>) {
  const persistQueue: Set<string> = new Set()
  let persistTimer: number | null = null

  function schedulePersist() {
    if (persistTimer) window.clearTimeout(persistTimer)
    persistTimer = window.setTimeout(flushPersist, 220)
  }

  function queuePositions(ids: string[]) {
    ids.forEach((id) => persistQueue.add(id))
    schedulePersist()
  }

  async function flushPersist() {
    if (!persistQueue.size) return
    const layoutCache = getLayoutCache()
    const items = [...persistQueue].map((id) => ({
      id,
      x: layoutCache[id].x,
      y: layoutCache[id].y,
      userPinned: true
    }))
    persistQueue.clear()
    persistTimer = null
    try {
      await fetch('/api/layout/positions', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ positions: items })
      })
      localStorage.removeItem('layoutRetry')
    } catch (e) {
      console.warn('[TopologyPersist] persist failed', e)
      localStorage.setItem('layoutRetry', JSON.stringify(items))
    }
  }

  function attachFocusRetry() {
    window.addEventListener('focus', () => {
      const pending = localStorage.getItem('layoutRetry')
      if (pending) {
        try {
          const list = JSON.parse(pending)
          list.forEach((p: any) => persistQueue.add(p.id))
          flushPersist()
        } catch {
          /* ignore */
        }
      }
    })
  }

  return { queuePositions, flushPersist, attachFocusRetry }
}
