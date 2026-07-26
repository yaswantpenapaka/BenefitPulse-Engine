import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { CreditCard, LayoutDashboard, LogOut, Shield, User } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/lib/utils'
import { AssistantChat } from '@/components/AssistantChat'
import { Button } from '@/components/ui/button'

const nav = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/cards', label: 'Cards', icon: CreditCard },
  { to: '/profile', label: 'Profile', icon: User },
]

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-40 glass border-b border-border/60" role="banner">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link to="/dashboard" className="flex items-center gap-3 group" aria-label="BenefitPulse home">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/40 bg-navy shadow-inner">
              <Shield className="h-5 w-5 text-primary" aria-hidden />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold tracking-wide text-foreground group-hover:text-primary transition-colors">
                BenefitPulse
              </div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-primary/80">
                Engine
              </div>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-1" aria-label="Main">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-primary/15 text-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-accent',
                  )
                }
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <div className="hidden sm:block text-right">
              <div className="text-sm font-medium">{user?.full_name || 'Member'}</div>
              <div className="text-xs text-muted-foreground">{user?.email}</div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => {
                logout()
                navigate('/login')
              }}
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 py-8" id="main-content">
        <Outlet />
      </main>

      <footer className="border-t border-border/40 py-4 text-center text-xs text-muted-foreground" role="contentinfo">
        BenefitPulse Engine · open prototype · free-tier stack
      </footer>

      <AssistantChat />
    </div>
  )
}
