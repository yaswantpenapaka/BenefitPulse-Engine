import { useEffect, type ReactNode } from 'react'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import { Layout } from '@/components/Layout'
import { LoginPage } from '@/pages/LoginPage'
import { SignupPage } from '@/pages/SignupPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { BenefitsPage } from '@/pages/BenefitsPage'
import { TransactionsPage } from '@/pages/TransactionsPage'
import { SimulatePage } from '@/pages/SimulatePage'
import { ClaimReviewPage } from '@/pages/ClaimReviewPage'
import { CardsPage } from '@/pages/CardsPage'
import { ProfilePage } from '@/pages/ProfilePage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

const PAGE_TITLES: Record<string, string> = {
  '/login': 'Sign in | BenefitPulse',
  '/signup': 'Create account | BenefitPulse',
  '/dashboard': 'Overview | BenefitPulse',
  '/benefits': 'Benefits | BenefitPulse',
  '/transactions': 'Transactions | BenefitPulse',
  '/simulate': 'Simulate | BenefitPulse',
  '/cards': 'Your cards | BenefitPulse',
  '/profile': 'Profile | BenefitPulse',
}

function DocumentTitle() {
  const { pathname } = useLocation()
  useEffect(() => {
    if (pathname.startsWith('/claims/')) {
      document.title = 'Claim review | BenefitPulse'
      return
    }
    document.title =
      PAGE_TITLES[pathname] ||
      'BenefitPulse Engine | Card Benefit Detection & Claim Prefill'
  }, [pathname])
  return null
}

function Protected({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <DocumentTitle />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route
              element={
                <Protected>
                  <Layout />
                </Protected>
              }
            >
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/benefits" element={<BenefitsPage />} />
              <Route path="/transactions" element={<TransactionsPage />} />
              <Route path="/simulate" element={<SimulatePage />} />
              <Route path="/claims/:benefitId" element={<ClaimReviewPage />} />
              <Route path="/cards" element={<CardsPage />} />
              <Route path="/profile" element={<ProfilePage />} />
            </Route>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
