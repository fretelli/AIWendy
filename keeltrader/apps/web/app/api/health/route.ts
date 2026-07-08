import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export function GET() {
  return NextResponse.json({
    status: 'ok',
    service: 'keeltrader-web',
    git_sha: process.env.KEELTRADER_GIT_SHA || 'unknown',
    build_time: process.env.KEELTRADER_BUILD_TIME || 'unknown',
    build_type: process.env.KEELTRADER_BUILD_TYPE || 'unknown',
  })
}
