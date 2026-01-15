import * as React from "react"
import {
  ChevronLeft,
  Github,
  Loader2,
  Mail,
  Send,
  Square,
  AlertCircle,
  MessageSquare,
  RefreshCw,
  Plus,
  Wallet,
  Check,
  Edit,
  Trash,
  Eye,
  EyeOff,
} from "lucide-react"

export type IconProps = React.SVGProps<SVGSVGElement>

export const Icons = {
  chevronLeft: ChevronLeft,
  gitHub: Github,
  spinner: Loader2,
  loader2: Loader2,
  mail: Mail,
  send: Send,
  square: Square,
  alertCircle: AlertCircle,
  messageSquare: MessageSquare,
  refresh: RefreshCw,
  plus: Plus,
  wallet: Wallet,
  check: Check,
  edit: Edit,
  trash: Trash,
  eye: Eye,
  eyeOff: EyeOff,
  google: (props: IconProps) => (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      {...props}
    >
      <path d="M12 10.2v3.9h5.4c-.7 2.2-2.7 3.9-5.4 3.9a6 6 0 1 1 0-12c1.5 0 2.8.5 3.9 1.4l2.7-2.7A9.7 9.7 0 0 0 12 2.3 9.7 9.7 0 0 0 2.3 12 9.7 9.7 0 0 0 12 21.7c5.5 0 9.2-3.9 9.2-9.4 0-.6-.1-1.1-.2-1.6H12z" />
    </svg>
  ),
}

