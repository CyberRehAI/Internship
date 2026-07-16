import { NavLink } from 'react-router-dom'
import { Database, History, LayoutDashboard, Radar, Search } from 'lucide-react'
import { cn } from '../lib/cn'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/search', label: 'Global Search', icon: Search },
  { to: '/pulses', label: 'Pulse Viewer', icon: Radar },
  { to: '/dumper', label: 'IOC Dumper', icon: Database },
  { to: '/export-history', label: 'Export History', icon: History },
]

type SidebarProps = {
  onNavigate?: () => void
}

export function Sidebar({ onNavigate }: SidebarProps) {
  return (
    <nav aria-label="Primary" className="flex h-full flex-col">
      <div className="border-b border-line px-4 py-4">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-neutral-500">Workbench</p>
        <p className="mt-1 text-lg font-bold tracking-tight text-accent">OTX</p>
        <p className="text-sm font-semibold text-[#F5F5F5]">Threat Intel Console</p>
      </div>
      <ul className="flex-1 space-y-1 p-2">
        {navItems.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === '/'}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 border-l-2 px-3 py-2.5 text-sm transition-colors',
                  isActive
                    ? 'border-accent bg-accent/5 text-accent shadow-[inset_0_0_12px_rgba(255,122,0,0.04)]'
                    : 'border-transparent text-neutral-500 hover:text-neutral-200 hover:bg-surface-2',
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span className="relative">
                    <item.icon className="h-4 w-4" aria-hidden="true" />
                    {isActive && (
                      <span className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-accent" />
                    )}
                  </span>
                  <span>{item.label}</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
