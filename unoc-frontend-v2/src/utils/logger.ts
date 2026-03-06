/**
 * Professional Console Logger with Environment-based Filtering
 *
 * Usage:
 *   import { logger } from '@/utils/logger'
 *   logger.debug('[MyComponent]', 'Some debug info')
 *   logger.info('[MyComponent]', 'Important info')
 *   logger.warn('[MyComponent]', 'Warning!')
 *   logger.error('[MyComponent]', 'Error!', error)
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'off'

class Logger {
  private level: LogLevel = 'info'
  private mutedPrefixes: Set<string> = new Set()

  constructor() {
    this.configure()
  }

  private configure() {
    // Check environment variables from Vite
    const devMode = import.meta.env.DEV
    const logLevel = import.meta.env.VITE_LOG_LEVEL as LogLevel | undefined
    const mutedLogs = import.meta.env.VITE_MUTED_LOGS as string | undefined

    // In production: Only warnings and errors
    // In development: Info level (unless overridden)
    this.level = logLevel || (devMode ? 'info' : 'warn')

    // Parse muted log prefixes
    if (mutedLogs) {
      mutedLogs.split(',').forEach((prefix) => this.mutedPrefixes.add(prefix.trim()))
    }

    // Default muted prefixes in dev mode (reduce noise)
    if (devMode && !logLevel) {
      this.mutedPrefixes.add('[PortSummaryManager]')
      this.mutedPrefixes.add('[wsClient]')
      this.mutedPrefixes.add('[metricsStore]')
      this.mutedPrefixes.add('[linkMetricsStore]')
      this.mutedPrefixes.add('[OLTCockpit]')
      this.mutedPrefixes.add('[LAYOUT]') // Mute routine layout logs
      this.mutedPrefixes.add('[LAYOUT DEBUG]')
    }
  }

  private shouldLog(level: LogLevel, prefix?: string): boolean {
    const levels: LogLevel[] = ['debug', 'info', 'warn', 'error', 'off']
    const currentLevelIndex = levels.indexOf(this.level)
    const messageLevelIndex = levels.indexOf(level)

    if (messageLevelIndex < currentLevelIndex) return false

    // Check if prefix is muted
    if (prefix && this.mutedPrefixes.has(prefix)) return false

    return true
  }

  debug(prefix: string, ...args: unknown[]) {
    if (this.shouldLog('debug', prefix)) {
      console.debug(prefix, ...args)
    }
  }

  info(prefix: string, ...args: unknown[]) {
    if (this.shouldLog('info', prefix)) {
      console.info(prefix, ...args)
    }
  }

  warn(prefix: string, ...args: unknown[]) {
    if (this.shouldLog('warn', prefix)) {
      console.warn(prefix, ...args)
    }
  }

  error(prefix: string, ...args: unknown[]) {
    if (this.shouldLog('error', prefix)) {
      console.error(prefix, ...args)
    }
  }

  // Special: Always log (even if muted)
  force(prefix: string, ...args: unknown[]) {
    console.log(prefix, ...args)
  }
}

export const logger = new Logger()
