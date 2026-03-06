import type { Link } from './types.js'

type LinksStoreApi = {
  links: Link[]
}

export async function confirmCreateLink(
  store: LinksStoreApi,
  finalA: string,
  finalB: string
): Promise<void> {
  const derive = (iid: string) => (iid.endsWith('-if0') ? iid.slice(0, -4) : iid)
  const da = derive(finalA)
  const db = derive(finalB)
  const id = da <= db ? `${da}__${db}` : `${db}__${da}`
  const payload = {
    id,
    a_interface_id: finalA,
    b_interface_id: finalB,
    kind: 'FIBER',
    status: 'UP'
  }
  console.debug('[linksStore] creating link (confirm)', payload)

  const resp = await fetch('/api/links', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  console.debug('[linksStore] POST /api/links status', resp.status)
  if (!resp.ok) {
    if (resp.status === 409) {
      console.debug('[linksStore] duplicate link (409)')
      return
    }
    let bodyText = ''
    try {
      bodyText = await resp.text()
    } catch {
      /* no-op */
    }
    console.debug('[linksStore] error body', bodyText)
    if (resp.status === 500) {
      try {
        const direct = await fetch(`http://127.0.0.1:5001/api/links`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        if (direct.ok) {
          const linkRaw2 = (await direct.json()) as Link
          console.debug('[linksStore] recovered via direct retry', linkRaw2)
          store.links.push(linkRaw2)
          return
        }
        console.debug('[linksStore] direct retry status', direct.status)
      } catch {
        /* ignore */
      }
      for (let attempt = 1; attempt <= 3; attempt++) {
        await new Promise((r) => setTimeout(r, 150 * attempt))
        try {
          const check = await fetch('/api/links')
          if (check.ok) {
            const all = (await check.json()) as Link[]
            const found = all.find((l) => l.id === id)
            if (found) {
              console.debug('[linksStore] recovered link after 500 via poll', found)
              store.links.push(found)
              return
            }
          }
        } catch {
          /* ignore */
        }
      }
    }
    throw new Error(`Create link failed ${resp.status}`)
  }
  interface LinkMaybe extends Partial<Link> {
    [k: string]: unknown
  }
  const linkRaw = (await resp.json()) as LinkMaybe
  console.debug('[linksStore] link response body', linkRaw)
  if (!linkRaw.a_device_id || !linkRaw.b_device_id) {
    const derive2 = (iid: string) => (iid && iid.endsWith('-if0') ? iid.slice(0, -4) : iid)
    linkRaw.a_device_id = derive2(linkRaw.a_interface_id!)
    linkRaw.b_device_id = derive2(linkRaw.b_interface_id!)
  }
  store.links.push(linkRaw as Link)
  console.debug('[linksStore] link stored, total links', store.links.length)
}
