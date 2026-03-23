import { createRootRoute, Outlet, useRouter } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'

export const Route = createRootRoute({
  component: RootLayout,
  pendingComponent: RootPending,
  errorComponent: RootError,
})

function RootLayout() {
  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex h-screen overflow-hidden bg-background text-foreground">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-auto p-6">
            <Outlet />
          </main>
        </div>
        <Toaster richColors position="top-right" />
        {import.meta.env.DEV && <TanStackRouterDevtools position="bottom-right" />}
      </div>
    </TooltipProvider>
  )
}

function RootPending() {
  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <LoadingSkeleton />
    </div>
  )
}

function RootError({ error }: { error: Error }) {
  const router = useRouter()
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 bg-background text-foreground">
      <AlertTriangle className="h-12 w-12 text-loss" />
      <h1 className="text-xl font-semibold">出错了</h1>
      <p className="max-w-md text-center text-sm text-muted-foreground">
        {error.message || '发生了未知错误'}
      </p>
      <Button variant="outline" onClick={() => router.invalidate()}>
        重试
      </Button>
    </div>
  )
}
