/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_SKIP_AUTH?: string
  readonly VITE_E2E?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
