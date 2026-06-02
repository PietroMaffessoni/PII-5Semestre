import { createClient } from '@supabase/supabase-js'

const useMockApi = import.meta.env.VITE_USE_MOCK_API === 'true'
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

function createMockSupabaseClient() {
  return {
    auth: {
      async getSession() {
        return {
          data: { session: null },
          error: null,
        }
      },
    },
  }
}

if (!useMockApi && (!supabaseUrl || !supabaseKey)) {
  throw new Error('As variaveis VITE_SUPABASE_URL e VITE_SUPABASE_PUBLISHABLE_KEY nao estao definidas.')
}

export const supabase = useMockApi
  ? createMockSupabaseClient()
  : createClient(supabaseUrl, supabaseKey)
