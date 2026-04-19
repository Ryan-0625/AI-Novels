/* 前端统一日志模块 */

// 前端日志级别
type LogLevel = 'info' | 'warn' | 'error' | 'debug'

// 当前日志级别
let logLevel: LogLevel = import.meta.env.PROD ? 'error' : 'debug'

// 日志前缀
const prefix = '[AI-Novels]'

/**
 * 获取当前时间戳
 */
function getTimestamp(): string {
  const now = new Date()
  return now.toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/**
 * 输出日志
 */
function log(level: LogLevel, ...args: any[]) {
  const timestamp = getTimestamp()
  const prefixWithLevel = `${prefix} [${level.toUpperCase()}]`

  const formattedArgs = [`${timestamp} ${prefixWithLevel}`, ...args]

  switch (level) {
    case 'info':
      console.info?.(...formattedArgs)
      break
    case 'warn':
      console.warn?.(...formattedArgs)
      break
    case 'error':
      console.error?.(...formattedArgs)
      break
    case 'debug':
      if (logLevel === 'debug') {
        console.debug?.(...formattedArgs)
      }
      break
  }
}

/**
 * 信息日志
 */
export function logInfo(...args: any[]) {
  log('info', ...args)
}

/**
 * 警告日志
 */
export function logWarn(...args: any[]) {
  log('warn', ...args)
}

/**
 * 错误日志
 */
export function logError(...args: any[]) {
  log('error', ...args)
}

/**
 * 调试日志
 */
export function logDebug(...args: any[]) {
  log('debug', ...args)
}

/**
 * LLM调用日志（规范要求）
 */
export function logLlmCall(
  provider: string,
  model: string,
  promptTokens: number,
  completionTokens: number,
  durationMs: number
) {
  log(
    'info',
    `LLM Call: provider=${provider}, model=${model}, ` +
    `prompt_tokens=${promptTokens}, completion_tokens=${completionTokens}, duration_ms=${durationMs}`
  )
}
