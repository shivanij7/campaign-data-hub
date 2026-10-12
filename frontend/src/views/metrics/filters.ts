import type { Platform } from '../../api/types'

export interface Filters {
  platform: Platform | ''
  dateFrom: string
  dateTo: string
}

export const NO_FILTERS: Filters = { platform: '', dateFrom: '', dateTo: '' }
