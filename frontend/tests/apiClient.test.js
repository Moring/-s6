import { request } from '../src/api/client'

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('throws a friendly error on failed response', async () => {
    const response = new Response(JSON.stringify({ error: 'Invalid credentials' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))

    await expect(request('POST', '/auth/login/', { username: 'a', password: 'b' })).rejects.toThrow(
      'Invalid credentials'
    )
  })

  it('handles etag not modified responses', async () => {
    const response = {
      status: 304,
      headers: new Headers({ ETag: 'test-etag' }),
      text: () => Promise.resolve(''),
      ok: false,
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))

    const result = await request('GET', '/status/bar/', null, { etag: 'test-etag' })
    expect(result.notModified).toBe(true)
    expect(result.etag).toBe('test-etag')
  })
})
