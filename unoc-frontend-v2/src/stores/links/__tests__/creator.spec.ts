import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { confirmCreateLink } from '../creator'

type Link = {
  id: string
  a_interface_id: string
  b_interface_id: string
  a_device_id?: string
  b_device_id?: string
  status: string
  kind: string
}

function makeResp({
  ok,
  status,
  json,
  text
}: {
  ok: boolean
  status: number
  json?: any
  text?: string
}) {
  return {
    ok,
    status,
    async json() {
      return json
    },
    async text() {
      return text ?? ''
    }
  } as any
}

describe('links/creator confirmCreateLink', () => {
  let origFetch: any

  beforeEach(() => {
    origFetch = (globalThis as any).fetch
  })

  afterEach(() => {
    ;(globalThis as any).fetch = origFetch
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('pushes link on success and derives device ids when missing', async () => {
    const store = { links: [] as Link[] }
    const linkBody = {
      id: 'x__y',
      a_interface_id: 'x-if0',
      b_interface_id: 'y-if0',
      status: 'UP',
      kind: 'FIBER'
    }
    ;(globalThis as any).fetch = vi.fn(async (input: any, init?: any) => {
      if (typeof input === 'string' && input.includes('/api/links') && init?.method === 'POST') {
        return makeResp({ ok: true, status: 200, json: linkBody })
      }
      return makeResp({ ok: true, status: 200, json: [] })
    })

    await confirmCreateLink(store as any, 'x-if0', 'y-if0')
    expect(store.links.length).toBe(1)
    const pushed = store.links[0]
    expect(pushed.a_device_id).toBe('x')
    expect(pushed.b_device_id).toBe('y')
  })

  it('handles 409 (duplicate) without throwing or pushing', async () => {
    const store = { links: [] as Link[] }
    ;(globalThis as any).fetch = vi.fn(async (input: any, init?: any) => {
      if (typeof input === 'string' && input.includes('/api/links') && init?.method === 'POST') {
        return makeResp({ ok: false, status: 409, text: 'duplicate' })
      }
      return makeResp({ ok: true, status: 200, json: [] })
    })

    await confirmCreateLink(store as any, 'a-if0', 'b-if0')
    expect(store.links.length).toBe(0)
  })

  it('recovers from 500 via poll when direct retry fails', async () => {
    vi.useFakeTimers()
    const store = { links: [] as Link[] }
    const calls: Array<{ url: string; method: string | undefined }> = []
    const derivedId = 'a__b'
    ;(globalThis as any).fetch = vi.fn(async (input: any, init?: any) => {
      const url = typeof input === 'string' ? input : String(input)
      const method = init?.method
      calls.push({ url, method })
      // First POST to /api/links → 500
      if (url === '/api/links' && method === 'POST') {
        return makeResp({ ok: false, status: 500, text: 'boom' })
      }
      // Direct retry to 127.0.0.1 → not ok
      if (url.startsWith('http://127.0.0.1:5001') && method === 'POST') {
        return makeResp({ ok: false, status: 500, text: 'still down' })
      }
      // Poll GET /api/links → include the desired link
      if (url === '/api/links' && (!method || method === 'GET')) {
        return makeResp({
          ok: true,
          status: 200,
          json: [
            {
              id: derivedId,
              a_interface_id: 'a-if0',
              b_interface_id: 'b-if0',
              a_device_id: 'a',
              b_device_id: 'b',
              status: 'UP',
              kind: 'FIBER'
            }
          ]
        })
      }
      return makeResp({ ok: true, status: 200, json: [] })
    })

    const p = confirmCreateLink(store as any, 'a-if0', 'b-if0')
    // Advance timers to allow poll backoff sequence to proceed
    await vi.advanceTimersByTimeAsync(150 + 300)
    await p
    expect(store.links.length).toBe(1)
    expect(store.links[0].id).toBe(derivedId)
    // Ensure our POST + direct retry + GET poll were attempted
    const urls = calls.map((c) => c.url)
    expect(urls.some((u) => u === '/api/links')).toBe(true)
    expect(urls.some((u) => u.startsWith('http://127.0.0.1:5001'))).toBe(true)
  })
})
