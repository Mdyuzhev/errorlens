/**
 * Tests for EL015: Test Plans feature.
 * Store logic tests using vitest.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTestPlansStore } from '@/stores/testPlans'

// Mock api module
vi.mock('@/services/api', () => ({
  testPlansApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    addCases: vi.fn(),
    removeCase: vi.fn(),
    getRuns: vi.fn(),
    getRun: vi.fn(),
    startRun: vi.fn(),
    recordResult: vi.fn(),
    finishRun: vi.fn(),
  }
}))

import { testPlansApi } from '@/services/api'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('TestPlans Store', () => {
  describe('plans_list_renders', () => {
    it('fetchPlans loads plans into state', async () => {
      const plans = [
        { id: '1', name: 'Plan A', status: 'active', cases_count: 5, runs_count: 2 },
        { id: '2', name: 'Plan B', status: 'draft', cases_count: 0, runs_count: 0 },
      ]
      testPlansApi.list.mockResolvedValue({ data: plans })

      const store = useTestPlansStore()
      await store.fetchPlans()

      expect(store.plans).toHaveLength(2)
      expect(store.plans[0].name).toBe('Plan A')
      expect(store.loading).toBe(false)
    })
  })

  describe('plan_detail_shows_cases', () => {
    it('fetchPlan loads plan with cases', async () => {
      const plan = {
        id: '1',
        name: 'Plan A',
        cases: [
          { testcase_id: 'tc-1', title: 'Login test', priority: 'High' },
          { testcase_id: 'tc-2', title: 'Logout test', priority: 'Medium' },
        ],
        cases_count: 2,
      }
      testPlansApi.get.mockResolvedValue({ data: plan })

      const store = useTestPlansStore()
      await store.fetchPlan('1')

      expect(store.currentPlan).not.toBeNull()
      expect(store.currentPlan.cases).toHaveLength(2)
    })
  })

  describe('run_view_counters', () => {
    it('recordResult updates counters from server response', async () => {
      const store = useTestPlansStore()
      store.currentRun = {
        id: 'run-1',
        total: 5,
        passed: 0,
        failed: 0,
        blocked: 0,
        skipped: 0,
        results: [
          { testcase_id: 'tc-1', status: null },
        ],
      }

      testPlansApi.recordResult.mockResolvedValue({
        data: {
          testcase_id: 'tc-1',
          status: 'passed',
          comment: null,
          error_details: null,
          executed_at: '2026-03-09T10:00:00',
          counters: { passed: 1, failed: 0, blocked: 0, skipped: 0 },
        },
      })

      await store.recordResult('run-1', 'tc-1', { status: 'passed' })

      expect(store.currentRun.passed).toBe(1)
      expect(store.currentRun.results[0].status).toBe('passed')
    })
  })

  describe('cannot_finish_empty', () => {
    it('finishRun calls API and updates status', async () => {
      const store = useTestPlansStore()
      store.currentRun = {
        id: 'run-1',
        status: 'in_progress',
        passed: 3,
        failed: 1,
        blocked: 0,
        skipped: 0,
      }

      testPlansApi.finishRun.mockResolvedValue({
        data: {
          status: 'completed',
          finished_at: '2026-03-09T12:00:00',
          passed: 3,
          failed: 1,
          blocked: 0,
          skipped: 0,
        },
      })

      await store.finishRun('run-1')

      expect(store.currentRun.status).toBe('completed')
      expect(store.currentRun.finished_at).toBeTruthy()
    })
  })

  describe('case_picker_add_cases', () => {
    it('addCases calls API and refreshes plan', async () => {
      testPlansApi.addCases.mockResolvedValue({})
      testPlansApi.get.mockResolvedValue({
        data: { id: '1', cases: [{ testcase_id: 'tc-1' }, { testcase_id: 'tc-2' }], cases_count: 2 },
      })

      const store = useTestPlansStore()
      const result = await store.addCases('1', ['tc-1', 'tc-2'])

      expect(result).toBe(true)
      expect(testPlansApi.addCases).toHaveBeenCalledWith('1', ['tc-1', 'tc-2'])
    })
  })

  describe('removeCase', () => {
    it('removes case from local state', async () => {
      testPlansApi.removeCase.mockResolvedValue({})

      const store = useTestPlansStore()
      store.currentPlan = {
        id: '1',
        cases: [
          { testcase_id: 'tc-1' },
          { testcase_id: 'tc-2' },
        ],
        cases_count: 2,
      }

      await store.removeCase('1', 'tc-1')

      expect(store.currentPlan.cases).toHaveLength(1)
      expect(store.currentPlan.cases[0].testcase_id).toBe('tc-2')
    })
  })

  describe('deletePlan', () => {
    it('removes plan from list', async () => {
      testPlansApi.remove.mockResolvedValue({})

      const store = useTestPlansStore()
      store.plans = [
        { id: '1', name: 'A' },
        { id: '2', name: 'B' },
      ]

      await store.deletePlan('1')

      expect(store.plans).toHaveLength(1)
      expect(store.plans[0].id).toBe('2')
    })
  })
})
