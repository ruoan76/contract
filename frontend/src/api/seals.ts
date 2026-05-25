import { client } from './client'

export const sealsApi = {
  apply: (contractId: number, sealType = '公章') =>
    client.post<{ id: number }>('/api/v1/seals/apply', {
      contract_id: contractId,
      seal_type: sealType,
    }),

  approve: (sealId: number, approved = true) =>
    client.post<unknown>(`/api/v1/seals/${sealId}/approve`, { approved }),

  list: () =>
    client.get<{
      items?: Array<{
        id: number
        contract_id: number
        status?: string
        seal_type?: string
        seal_image_path?: string
      }>
    }>('/api/v1/seals/'),

  uploadScan: (sealId: number, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post<{ seal_image_path?: string }>(`/api/v1/seals/${sealId}/upload-scan`, fd)
  },
}
