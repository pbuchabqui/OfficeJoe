import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiClient } = vi.hoisted(() => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('./api', () => ({ apiClient }))

import { authService } from './auth'

describe('authService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiClient.post.mockResolvedValue({ data: { id: 'user-1' } })
  })

  it('mapeia criação de usuário do backend', async () => {
    await authService.createUser({
      email: 'novo@example.com',
      password: 'secret123',
      full_name: 'Novo Usuário',
      role: 'assistente',
    })

    expect(apiClient.post).toHaveBeenCalledWith('/auth/users', {
      email: 'novo@example.com',
      password: 'secret123',
      full_name: 'Novo Usuário',
      role: 'assistente',
    })
  })
})
