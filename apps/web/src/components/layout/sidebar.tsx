import { Link, useRouterState } from '@tanstack/react-router'
import {
  LayoutDashboard,
  Bot,
  GitCompareArrows,
  LineChart,
  ArrowRightLeft,
  Briefcase,
  ShieldAlert,
  ChevronLeft,
  Settings,
} from 'lucide-react'
import { useUIStore } from '@/stores/ui-store'
import { cn } from '@/lib/utils'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

interface NavItem {
  to: string
  label: string
  icon: typeof LayoutDashboard
  children?: { to: string; label: string; icon: typeof LayoutDashboard }[]
}

const navItems: NavItem[] = [
  { to: '/', label: '总览', icon: LayoutDashboard },
  {
    to: '/strategies',
    label: '策略管理',
    icon: Bot,
    children: [
      { to: '/strategies/compare', label: '策略对比', icon: GitCompareArrows },
    ],
  },
  { to: '/market', label: '行情中心', icon: LineChart },
  { to: '/trades', label: '交易记录', icon: ArrowRightLeft },
  { to: '/portfolio', label: '持仓组合', icon: Briefcase },
  { to: '/risk', label: '风控监控', icon: ShieldAlert },
]

export function Sidebar() {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)
  const routerState = useRouterState()
  const currentPath = routerState.location.pathname

  return (
    <aside
      className={cn(
        'flex h-screen flex-col border-r border-sidebar-border bg-sidebar transition-all duration-200',
        sidebarOpen ? 'w-60' : 'w-16',
      )}
    >
      <div className="flex h-14 items-center justify-between border-b border-sidebar-border px-4">
        {sidebarOpen && (
          <span className="text-lg font-bold text-sidebar-foreground">
            Kainex
          </span>
        )}
        <button
          onClick={toggleSidebar}
          className="rounded-md p-1.5 text-sidebar-foreground hover:bg-sidebar-accent"
        >
          <ChevronLeft
            className={cn(
              'h-4 w-4 transition-transform',
              !sidebarOpen && 'rotate-180',
            )}
          />
        </button>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {navItems.map(({ to, label, icon: Icon, children }) => {
          const isActive =
            to === '/' ? currentPath === '/' : currentPath.startsWith(to)

          const linkContent = (
            <Link
              key={to}
              to={to}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-primary'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                !sidebarOpen && 'justify-center px-0',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {sidebarOpen && <span>{label}</span>}
            </Link>
          )

          const childLinks =
            children && sidebarOpen && isActive
              ? children.map((child) => {
                  const childActive = currentPath.startsWith(child.to)
                  return (
                    <Link
                      key={child.to}
                      to={child.to}
                      className={cn(
                        'flex items-center gap-3 rounded-md px-3 py-1.5 pl-10 text-sm transition-colors',
                        childActive
                          ? 'text-sidebar-primary font-medium'
                          : 'text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent',
                      )}
                    >
                      <child.icon className="h-3.5 w-3.5 shrink-0" />
                      <span>{child.label}</span>
                    </Link>
                  )
                })
              : null

          if (!sidebarOpen) {
            return (
              <Tooltip key={to}>
                <TooltipTrigger asChild>
                  {linkContent}
                </TooltipTrigger>
                <TooltipContent side="right">
                  {label}
                </TooltipContent>
              </Tooltip>
            )
          }

          return (
            <div key={to}>
              {linkContent}
              {childLinks}
            </div>
          )
        })}
      </nav>

      {/* Settings link at bottom */}
      <div className="border-t border-sidebar-border p-2">
        {(() => {
          const isActive = currentPath.startsWith('/settings')

          const settingsLink = (
            <Link
              to="/settings"
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-primary'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                !sidebarOpen && 'justify-center px-0',
              )}
            >
              <Settings className="h-4 w-4 shrink-0" />
              {sidebarOpen && <span>{'设置'}</span>}
            </Link>
          )

          if (!sidebarOpen) {
            return (
              <Tooltip>
                <TooltipTrigger asChild>
                  {settingsLink}
                </TooltipTrigger>
                <TooltipContent side="right">
                  {'设置'}
                </TooltipContent>
              </Tooltip>
            )
          }

          return settingsLink
        })()}
      </div>
    </aside>
  )
}
