import { useEffect, type ReactNode } from 'react'
import { useDataStore } from '@/store/data'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function AppLayout({ children }: { children: ReactNode }) {
  const load = useDataStore(s => s.load)

  useEffect(() => { load() }, [load])

  return (
    <div className="app">
      <Sidebar />
      <div className="app-right">
        <Topbar />
        <main className="app-main">{children}</main>
      </div>
    </div>
  )
}
