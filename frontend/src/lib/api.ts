const API_BASE = import.meta.env.VITE_API_URL || ''

export type Profile = {
  id: string
  full_name?: string
  email?: string
  created_at?: string
}

export type Card = {
  id: string
  card_name: string
  card_type: string
  last_four?: string
  is_active: boolean
}

export type Transaction = {
  id: string
  merchant_raw: string
  merchant_normalized?: string
  amount: number
  currency: string
  transaction_date: string
  mcc?: string
  category?: string
  description?: string
  card_id?: string
}

export type DetectedBenefit = {
  id: string
  transaction_id: string
  benefit_type: string
  confidence_score?: number
  status: string
  explanation?: string
  policy_reference?: string
  coverage_window_days?: number
  max_coverage_amount?: number
  created_at?: string
  merchant?: string
  amount?: number
  transaction_date?: string
  category?: string
  transaction?: Transaction
  claim?: Claim
  prefilled_data?: Record<string, unknown>
  missing_documents?: string[]
  confidence_breakdown?: Record<string, number>
}

export type Claim = {
  id: string
  detected_benefit_id: string
  status: string
  prefilled_data?: Record<string, unknown>
  missing_documents?: string[]
  customer_notes?: string
  submitted_at?: string
  created_at?: string
}

export type DashboardData = {
  profile: Profile
  cards: Card[]
  transactions: Transaction[]
  detected_benefits: DetectedBenefit[]
  stats: {
    cards_count: number
    transactions_count: number
    active_benefits: number
    claim_eligible?: number
    outside_coverage?: number
    reviewed_charges?: number
    submitted_claims: number
    potential_coverage: number
  }
}

export type PipelineResult = {
  pipeline_status?: string
  eligible?: boolean
  confidence_score?: number
  confidence_breakdown?: Record<string, number>
  transaction_intelligence?: {
    merchant_normalized?: string
    category?: string
    product_type?: string
    confidence?: number
  }
  rules_decision?: {
    eligible?: boolean
    benefit?: string | null
    reasons?: string[]
    window_remaining_days?: number
    coverage_window_days?: number
    max_coverage?: number
    policy_reference?: string
  }
  benefit_candidates?: { benefit_type: string; reason: string }[]
  prefilled_claim?: Record<string, unknown>
  missing_documents?: string[]
  explanation?: string
  policy_chunks?: { source?: string; title?: string; score?: number }[]
  transaction?: Transaction
  saved_benefit?: DetectedBenefit | null
  mode?: string
  llm?: {
    gemini_configured?: boolean
    gemini_model?: string | null
    calls_attempted?: number
    calls_succeeded?: number
    used_gemini?: boolean
  }
}

export type InjectPayload = {
  merchant_raw: string
  amount: number
  description?: string
  category?: string
  mcc?: string
  currency?: string
  run_detection?: boolean
}

function getToken(): string | null {
  return localStorage.getItem('access_token')
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem('access_token', token)
  else localStorage.removeItem('access_token')
}

export function setUser(user: Profile | null) {
  if (user) localStorage.setItem('user', JSON.stringify(user))
  else localStorage.removeItem('user')
}

export function getUser(): Profile | null {
  const raw = localStorage.getItem('user')
  if (!raw) return null
  try {
    return JSON.parse(raw) as Profile
  } catch {
    return null
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {})
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    setToken(null)
    setUser(null)
    if (!path.includes('/auth/')) {
      window.location.href = '/login'
    }
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: Profile }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  signup: (email: string, password: string, full_name: string) =>
    request<{ access_token: string; user: Profile }>('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name }),
    }),

  dashboard: () => request<DashboardData>('/api/dashboard'),
  cards: () => request<Card[]>('/api/cards'),
  transactions: () => request<Transaction[]>('/api/transactions'),
  benefits: () => request<DetectedBenefit[]>('/api/benefits'),
  benefit: (id: string) => request<DetectedBenefit>(`/api/benefits/${id}`),
  detect: (transactionId: string) =>
    request<PipelineResult>(`/api/benefits/detect/${transactionId}`, { method: 'POST' }),

  inject: (payload: InjectPayload) =>
    request<PipelineResult>('/api/benefits/inject', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  health: () =>
    request<{
      status: string
      data_backend?: string
      gemini_configured?: boolean
      gemini_model?: string | null
      agents?: string
      rag?: {
        backend?: string
        embedding_mode?: string
        chunk_count?: number
      }
      supabase_configured?: boolean
    }>('/health'),

  systemStatus: () =>
    request<{
      data_backend?: string
      gemini?: { configured?: boolean; model?: string | null }
      rag?: {
        backend?: string
        embedding_mode?: string
        chunk_count?: number
        error?: string | null
      }
      supabase?: {
        configured?: boolean
        reachable?: boolean
        tables_ok?: boolean
        error?: string | null
      }
      architecture?: Record<string, unknown>
    }>('/api/system/status'),

  claimByBenefit: (benefitId: string) =>
    request<Claim>(`/api/claims/by-benefit/${benefitId}`),
  updateClaim: (claimId: string, data: Partial<Claim>) =>
    request<Claim>(`/api/claims/${claimId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  submitClaim: (claimId: string, data: { customer_notes?: string; prefilled_data?: Record<string, unknown> }) =>
    request<Claim>(`/api/claims/${claimId}/submit`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  uploadDocument: async (claimId: string, file: File, documentType = 'receipt') => {
    const form = new FormData()
    form.append('file', file)
    form.append('document_type', documentType)
    return request<{ document: unknown; claim: Claim }>(`/api/claims/${claimId}/documents`, {
      method: 'POST',
      body: form,
    })
  },

  chat: (payload: {
    message: string
    claim_id?: string
    benefit_id?: string
    conversation_history?: { role: string; content: string }[]
  }) =>
    request<{ reply: string; citations: string[]; sources: { source: string; title: string }[] }>(
      '/api/assistant/chat',
      { method: 'POST', body: JSON.stringify(payload) },
    ),
}
