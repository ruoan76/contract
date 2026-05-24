import { client } from './client'

export const archivesApi = {
  archive: (contractId: number, location = '/archive/demo') =>
    client.post<unknown>(`/api/v1/archives/${contractId}/archive`, {
      archive_location: location,
    }),

  ledger: () => client.get<{ items?: unknown[] }>('/api/v1/archives/ledger'),
}
