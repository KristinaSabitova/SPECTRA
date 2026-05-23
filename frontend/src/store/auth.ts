import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserResponse, TokenResponse } from '@/types'

const STORAGE_KEY = 'spectra-auth'

interface AuthState {
  user: UserResponse | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  mustChangePassword: boolean
  setAuth: (user: UserResponse, tokens: TokenResponse) => void
  updateUser: (user: UserResponse) => void
  setMustChangePassword: (v: boolean) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      mustChangePassword: false,

      setAuth: (user, tokens) =>
        set({
          user,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isAuthenticated: true,
        }),

      updateUser: (user) => set({ user }),

      setMustChangePassword: (v) => set({ mustChangePassword: v }),

      clearAuth: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          mustChangePassword: false,
        })
        // Remove persisted key so no token remnants survive between sessions.
        // Called after set() because persist middleware writes synchronously on set.
        localStorage.removeItem(STORAGE_KEY)
      },
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        mustChangePassword: state.mustChangePassword,
      }),
    }
  )
)
