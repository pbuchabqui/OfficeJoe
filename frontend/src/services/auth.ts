import { apiClient } from './api'
import type { TokenResponse, User } from '@/types'

export const authService = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>('/auth/login', { email, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    return data
  },

  async logout(): Promise<void> {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },

  async getMe(): Promise<User> {
    const { data } = await apiClient.get<User>('/auth/me')
    return data
  },

  async createUser(payload: {
    email: string
    password: string
    full_name: string
    role: User['role']
  }): Promise<User> {
    const { data } = await apiClient.post<User>('/auth/users', payload)
    return data
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token')
  },
}
