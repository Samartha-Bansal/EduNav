import { NextRequest } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8001'
const PROXY_TIMEOUT_MS = 180_000

export const runtime = 'nodejs'

async function proxyRequest(request: NextRequest, pathSegments: string[]) {
  const path = pathSegments.join('/')
  const search = request.nextUrl.search
  const target = `${BACKEND_URL}/${path}${search}`

  const headers = new Headers()
  const contentType = request.headers.get('content-type')
  if (contentType) headers.set('Content-Type', contentType)

  const init: RequestInit = {
    method: request.method,
    headers,
    signal: AbortSignal.timeout(PROXY_TIMEOUT_MS),
    cache: 'no-store',
  }

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = await request.text()
  }

  const response = await fetch(target, init)
  const body = await response.arrayBuffer()

  return new Response(body, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') || 'application/json',
    },
  })
}

type RouteContext = { params: { path: string[] } }

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context.params.path)
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context.params.path)
}
