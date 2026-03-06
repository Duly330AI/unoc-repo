export function injectUtilizationBuckets(buckets: number[]) {
  ;(
    globalThis as unknown as {
      __unocConfigStore__?: { metrics?: { UTILIZATION_BUCKETS?: number[] } }
    }
  ).__unocConfigStore__ = {
    metrics: { UTILIZATION_BUCKETS: buckets }
  }
}
