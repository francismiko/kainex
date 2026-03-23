import { create } from 'zustand'

type ColorScheme = 'international' | 'chinese'

interface UIState {
  theme: 'dark' | 'light'
  sidebarOpen: boolean
  colorScheme: ColorScheme
  toggleTheme: () => void
  toggleSidebar: () => void
  toggleColorScheme: () => void
}

// Default colors (international: green=profit, red=loss)
const COLOR_SCHEMES = {
  international: {
    light: { profit: '#16a34a', loss: '#dc2626' },
    dark: { profit: '#22c55e', loss: '#ef4444' },
  },
  chinese: {
    light: { profit: '#dc2626', loss: '#16a34a' },
    dark: { profit: '#ef4444', loss: '#22c55e' },
  },
} as const

function applyColorScheme(scheme: ColorScheme, theme: 'dark' | 'light'): void {
  const colors = COLOR_SCHEMES[scheme][theme]
  document.documentElement.style.setProperty('--profit', colors.profit)
  document.documentElement.style.setProperty('--loss', colors.loss)
}

export const useUIStore = create<UIState>((set, get) => ({
  theme: 'dark',
  sidebarOpen: true,
  colorScheme: 'international',
  toggleTheme: () =>
    set((state) => {
      const next = state.theme === 'dark' ? 'light' : 'dark'
      document.documentElement.classList.toggle('dark', next === 'dark')
      applyColorScheme(state.colorScheme, next)
      return { theme: next }
    }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  toggleColorScheme: () =>
    set((state) => {
      const next: ColorScheme =
        state.colorScheme === 'international' ? 'chinese' : 'international'
      applyColorScheme(next, get().theme)
      return { colorScheme: next }
    }),
}))
