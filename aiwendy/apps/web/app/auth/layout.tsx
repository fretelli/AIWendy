import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Authentication',
  description: 'Login or create an account to access AI Wendy',
}

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-secondary/20">
      {children}
    </div>
  )
}