import { Metadata } from 'next'

export const metadata: Metadata = {
  title: '账户',
  description: '登录或创建 KeelTrader 私人基本面研究账户',
}

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <>{children}</>
  )
}
