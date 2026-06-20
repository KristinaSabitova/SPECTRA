import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserResponse, TokenResponse } from '@/types'

const STORAGE_KEY = 'spectra-auth'

interface AuthState {
  user: UserResponse | null
  accessToken: string | null
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
      isAuthenticated: false,
      mustChangePassword: false,

      setAuth: (user, tokens) =>
        set({
          user,
          accessToken: tokens.access_token,
          isAuthenticated: true,
        }),

      updateUser: (user) => set({ user }),

      setMustChangePassword: (v) => set({ mustChangePassword: v }),

      clearAuth: () =>
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
          mustChangePassword: false,
        }),
    }),
    {
      name: STORAGE_KEY,
      // accessToken intentionally excluded — lives in memory only, never in localStorage
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        mustChangePassword: state.mustChangePassword,
      }),
    }
  )
)
