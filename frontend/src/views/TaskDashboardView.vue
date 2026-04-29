<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import { useAgentStore } from '@/stores/agentStore'
import DagVisualizer from '@/components/DagVisualizer.vue'
import type { DagNode, DagEdge } from '@/components/DagVisualizer.vue'

const taskStore = useTaskStore()
const agentStore = useAgentStore()

const dagNodes = ref<DagNode[]>([
  { id: 'analysis', label: '需求分析', status: 'completed' },
  { id: 'outline', label: '大纲规划', status: 'completed' },
  { id: 'character', label: '角色生成', status: 'running' },
  { id: 'world', label: '世界构建', status: 'pending' },
  { id: 'content', label: '内容生成', status: 'pending' },
  { id: 'qa', label: '质量检查', status: 'pending' },
  { id: 'polish', label: '文本润色', status: 'pending' },
])

const dagEdges = ref<DagEdge[]>([
  { source: 'analysis', target: 'outline' },
  { source: 'outline', target: 'character' },
  { source: 'outline', target: 'world' },
  { source: 'character', target: 'content' },
  { source: 'world', target: 'content' },
  { source: 'content', target: 'qa' },
  { source: 'qa', target: 'polish' },
])

let interval: number | undefined

onMounted(() => {
  taskStore.fetchTasks()
  agentStore.fetchAgents()
  taskStore.connectWS()
  agentStore.connectWS()
  interval = window.setInterval(() => {
    taskStore.fetchTasks()
    agentStore.fetchAgents()
  }, 5000)
})

onUnmounted(() => {
  taskStore.disconnectWS()
  agentStore.disconnectWS()
  if (interval) clearInterval(interval)
})

const statusBadge = (status: string) => {
  const map: Record<string, string> = {
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    idle: 'info',
    pending: 'warning',
  }
  return map[status] || 'info'
}
</script>

<template>
  <div class="task-dashboard p-4">
    <h2 class="text-2xl font-bold text-white mb-4">任务调度监控中心</h2>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <el-card class="stat-card" shadow="hover">
        <div class="text-3xl font-bold text-cyan-400">{{ taskStore.taskCount }}</div>
        <div class="text-sm text-slate-400">总任务数</div>
      </el-card>
      <el-card class="stat-card" shadow="hover">
        <div class="text-3xl font-bold text-emerald-400">{{ taskStore.runningCount }}</div>
        <div class="text-sm text-slate-400">运行中</div>
      </el-card>
      <el-card class="stat-card" shadow="hover">
        <div class="text-3xl font-bold text-blue-400">{{ agentStore.idleCount }}</div>
        <div class="text-sm text-slate-400">空闲 Agent</div>
      </el-card>
      <el-card class="stat-card" shadow="hover">
        <div class="text-3xl font-bold text-amber-400">{{ agentStore.activeCount }}</div>
        <div class="text-sm text-slate-400">忙碌 Agent</div>
      </el-card>
    </div>

    <!-- DAG 可视化 -->
    <el-card class="mb-6" shadow="never">
      <template #header>
        <span class="font-bold text-white">工作流 DAG</span>
      </template>
      <DagVisualizer :nodes="dagNodes" :edges="dagEdges" :width="900" :height="300" />
    </el-card>

    <!-- 任务列表 -->
    <el-card shadow="never">
      <template #header>
        <span class="font-bold text-white">活跃任务</span>
        <el-tag v-if="taskStore.wsConnected" type="success" size="small" class="ml-2">WS 实时</el-tag>
        <el-tag v-else type="info" size="small" class="ml-2">轮询模式</el-tag>
      </template>
      <el-table :data="taskStore.tasks" v-loading="taskStore.loading">
        <el-table-column prop="task_id" label="任务ID" width="180" />
        <el-table-column prop="agent_name" label="Agent" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusBadge(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="100" />
        <el-table-column prop="created_at" label="创建时间" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.task-dashboard {
  background: #0b1120;
  min-height: 100vh;
}
.stat-card {
  background: #1e293b;
  border: none;
}
</style>
