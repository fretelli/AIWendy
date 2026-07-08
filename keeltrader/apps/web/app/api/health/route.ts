import { NextResponse } from 'next/server'
import { getWebBuildInfo } from '@/lib/server/build-info'

export const dynamic = 'force-dynamic'

export function GET() {
  return NextResponse.json(getWebBuildInfo())
}
