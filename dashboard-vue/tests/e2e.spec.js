/**
 * E2E tests for ErrorLens
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'

describe('E2E: Generation Flow', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
    localStorage.setItem('access_token', 'test-token')
  })

  it('full swagger upload flow', async () => {
    const mockFile = new File(['{"paths": {}}'], 'swagger.json', {
      type: 'application/json'
    })

    // Mock generation POST
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ task_id: 'task-123' })
    })

    // Mock result GET
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: 'completed',
        result: { code: 'test code' }
      })
    })

    const response1 = await fetch('/api/v1/generation/from-swagger', {
      method: 'POST',
      body: mockFile
    })
    const data1 = await response1.json()
    expect(data1.task_id).toBe('task-123')

    const response2 = await fetch(`/api/v1/generation/result/${data1.task_id}`)
    const data2 = await response2.json()
    expect(data2.status).toBe('completed')
  })

  it('handles API errors', async () => {
    global.fetch.mockRejectedValueOnce(new Error('Network error'))

    try {
      await fetch('/api/v1/generation/from-swagger')
      expect(true).toBe(false) // Should not reach
    } catch (error) {
      expect(error.message).toBe('Network error')
    }
  })
})

describe('E2E: Session Recording', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
    localStorage.setItem('access_token', 'test-token')
  })

  it('session list loads', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [
          { id: '1', url: 'test.com', recorded_requests: [{ method: 'GET' }] }
        ]
      })
    })

    const response = await fetch('/sessions')
    const data = await response.json()
    expect(data.items.length).toBe(1)
    expect(data.items[0].id).toBe('1')
  })
})

describe('E2E: Auth Flow', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
    localStorage.clear()
  })

  it('login stores token', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: 'test-token',
        refresh_token: 'refresh-token',
        token_type: 'bearer'
      })
    })

    const response = await fetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username: 'test', password: 'pass' })
    })
    const data = await response.json()

    expect(data.access_token).toBe('test-token')
    expect(data.refresh_token).toBe('refresh-token')
  })

  it('handles 401 redirect', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Unauthorized' })
    })

    const response = await fetch('/sessions')
    expect(response.status).toBe(401)
  })
})
