"use client"

import { Toaster } from "sonner"

export function SonnerToaster() {
  return (
    <Toaster
      richColors
      closeButton
      expand
      duration={3500}
    />
  )
}
