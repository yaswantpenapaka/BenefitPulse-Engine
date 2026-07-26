import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, getUser, setToken, setUser, type Profile } from '@/lib/api'

type AuthContextValue = {
  user: Profile | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<Profile | null>(() => getUser())

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password)
    setToken(res.access_token)
    setUser(res.user)
    setUserState(res.user)
  }, [])

  const signup = useCallback(async (email: string, password: string, fullName: string) => {
    const res = await api.signup(email, password, fullName)
    setToken(res.access_token)
    setUser(res.user)
    setUserState(res.user)
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    setUserState(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      login,
      signup,
      logout,
    }),
    [user, login, signup, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
