/* API服务 - Axios封装 */
import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'

// API配置 - 指向后端服务器
const apiConfig = {
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8004/api/v1',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
}

// 创建axios实例
const axiosInstance: AxiosInstance = axios.create(apiConfig)

// 请求拦截器
axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 添加请求ID
    config.headers = config.headers || {}
    config.headers['X-Request-ID'] = crypto.randomUUID()

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 返回数据部分
axiosInstance.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error) => {
    // API错误已被各组件的错误处理捕获，无需重复输出
    return Promise.reject(error)
  }
)

// 封装常用方法
const api = {
  // 任务相关
  createTask: (data: any) => axiosInstance.post('/tasks', data) as Promise<any>,
  getTask: (taskId: string) => axiosInstance.get(`/tasks/${taskId}`) as Promise<any>,
  getTaskStatus: (taskId: string) => axiosInstance.get(`/tasks/${taskId}`) as Promise<any>,
  getTaskHealth: (taskId: string) => axiosInstance.get(`/tasks/${taskId}/health`) as Promise<any>,
  getTaskLogs: (taskId: string, page: number = 1, pageSize: number = 50) =>
    axiosInstance.get(`/tasks/${taskId}/logs`, { params: { page, page_size: pageSize } }) as Promise<any>,
  cancelTask: (taskId: string, data: any) => axiosInstance.post(`/tasks/${taskId}/cancel`, data) as Promise<any>,
  listTasks: (params: any = {}) => axiosInstance.get('/tasks', { params }) as Promise<any>,

  // 章节相关
  getChapters: (taskId: string) => axiosInstance.get(`/tasks/${taskId}/chapters`) as Promise<any>,
  getChapterContent: (taskId: string, chapterNum: number) => axiosInstance.get(`/tasks/${taskId}/chapters/${chapterNum}`) as Promise<any>,

  // 配置相关
  getConfig: (key: string) => axiosInstance.get(`/config/${key}`) as Promise<any>,
  updateConfig: (data: any) => axiosInstance.post(`/config/update`, data) as Promise<any>,

  // 系统相关
  getStats: () => axiosInstance.get('/stats') as Promise<any>,
  listAgents: () => axiosInstance.get('/agents') as Promise<any>,

  // 健康检查相关
  getSystemHealth: (deepCheck: boolean = false) =>
    axiosInstance.get('/health', { params: { deep_check: deepCheck } }) as Promise<any>,
  getSystemHealthFull: (deepCheck: boolean = false) =>
    axiosInstance.get('/system-health', { params: { deep_check: deepCheck } }) as Promise<any>,
  getComponentHealth: (componentName: string) =>
    axiosInstance.get(`/health/component/${componentName}`) as Promise<any>,
  immediateHealthCheck: () => axiosInstance.get('/health/check') as Promise<any>,

  // 健康检查相关
  checkComponent: (componentName: string) =>
    axiosInstance.get(`/health/component/${componentName}`) as Promise<any>,
}

export default api
