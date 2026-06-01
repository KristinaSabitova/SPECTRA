import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

export interface ShortcutDef {
  key: string
  description: string
  action: () => void
  requiresAuth?: boolean
}

interface Options {
  onNewRun?: () => void
  onReplayLast?: () => void
  onHelp?: () => void
}

let _showHelp: (() => void) | null = null

export function useKeyboardShortcuts({ onNewRun, onReplayLast, onHelp }: Options = {}) {
  const navigate = useNavigate()

  const shortcuts: ShortcutDef[] = [
    { key: 'n', description: 'New run', action: () => onNewRun?.() ?? navigate('/audits') },
    { key: 'r', description: 'Replay last run', action: () => onReplayLast?.() },
    { key: 'd', description: 'Dashboard', action: () => navigate('/dashboard') },
    { key: 'a', description: 'Audits', action: () => navigate('/audits') },
    { key: 'p', description: 'Profile', action: () => navigate('/profile') },
    { key: '?', description: 'Show shortcuts', action: () => onHelp?.() ?? _showHelp?.() },
  ]

  const handler = useCallback((e: KeyboardEvent) => {
    if (
      e.target instanceof HTMLInputElement ||
      e.target instanceof HTMLTextAreaElement ||
      e.target instanceof HTMLSelectElement ||
      (e.target as HTMLElement)?.isContentEditable
    ) return

    if (e.metaKey || e.ctrlKey || e.altKey) return

    if (e.key === 'Escape') {
      // Escape is handled per-modal; no global action
      return
    }

    const shortcut = shortcuts.find(s => s.key === e.key)
    if (shortcut) {
      e.preventDefault()
      shortcut.action()
    }
  }, [onNewRun, onReplayLast, onHelp, navigate])

  useEffect(() => {
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handler])

  return shortcuts
}

export function setGlobalHelpHandler(fn: () => void) {
  _showHelp = fn
}
