const DEVICE_ID_KEY = 'edunavigator_device_id'

/** Stable per-browser id — conversations stay on this device only. */
export function getDeviceId(): string {
  if (typeof window === 'undefined') return 'server'

  let id = window.localStorage.getItem(DEVICE_ID_KEY)
  if (!id) {
    id =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `dev-${Date.now()}-${Math.random().toString(36).slice(2)}`
    window.localStorage.setItem(DEVICE_ID_KEY, id)
  }
  return id
}
