/* eslint-disable @typescript-eslint/no-explicit-any */

export function createUndoRedo(
  getLayoutCache: () => Record<string, any>,
  fastRefreshNodes: (ids: string[]) => void
) {
  const undoStack: Array<Record<string, { x: number; y: number }>> = []
  const redoStack: Array<Record<string, { x: number; y: number }>> = []

  function emitStacks() {
    window.dispatchEvent(
      new CustomEvent('unoc:layoutStacks', {
        detail: { undo: undoStack.length, redo: redoStack.length }
      })
    )
  }

  function pushUndo(ids: string[]) {
    const layoutCache = getLayoutCache()
    const snap: Record<string, { x: number; y: number }> = {}
    ids.forEach((id) => {
      const l = layoutCache[id]
      if (l) snap[id] = { x: l.x, y: l.y }
    })
    undoStack.push(snap)
    if (undoStack.length > 20) undoStack.shift()
    redoStack.length = 0
    emitStacks()
  }

  function applyPositions(pos: Record<string, { x: number; y: number }>) {
    const layoutCache = getLayoutCache()
    Object.entries(pos).forEach(([id, xy]) => {
      if (layoutCache[id]) {
        layoutCache[id].x = xy.x
        layoutCache[id].y = xy.y
        layoutCache[id].pinned = true
      }
    })
    fastRefreshNodes(Object.keys(pos))
  }

  function undoLayout() {
    const last = undoStack.pop()
    if (!last) return
    const layoutCache = getLayoutCache()
    const rev: Record<string, { x: number; y: number }> = {}
    Object.keys(last).forEach((id) => {
      rev[id] = { x: layoutCache[id].x, y: layoutCache[id].y }
    })
    redoStack.push(rev)
    applyPositions(last)
    emitStacks()
  }

  function redoLayout() {
    const next = redoStack.pop()
    if (!next) return
    pushUndo(Object.keys(next))
    applyPositions(next)
    emitStacks()
  }

  return { pushUndo, undoLayout, redoLayout, emitStacks }
}
