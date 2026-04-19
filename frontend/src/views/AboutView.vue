<script setup lang="ts">
import { ref } from 'vue'
import {
  InfoFilled,
  StarFilled,
  Grid,
  User,
  Connection,
  DataLine,
  ChatDotRound,
  CircleCheck,
  Monitor,
  Cpu,
  Collection,
  Share,
  MagicStick,
  Document,
  ArrowRightBold
} from '@element-plus/icons-vue'

// 版本信息
const version = ref('1.0.0')
const lastUpdated = ref('2026-03-12')

// 项目信息
const projectInfo = {
  name: 'AI Novel Generation System',
  description: '基于多智能体协同工作的AI小说生成系统，通过12个专业智能体分工协作，实现从规划到生成的全流程自动化',
  version: version.value,
  lastUpdated: lastUpdated.value,
}

// 功能特性 - 使用存在的图标
const features = [
  {
    title: '多智能体协同',
    description: '12个专业智能体分工协作，分别负责规划、生成、检查等各个环节',
    icon: Connection,
    color: '#409eff',
    bg: 'rgba(64, 158, 255, 0.1)',
  },
  {
    title: 'DAG工作流',
    description: '基于有向无环图的任务编排，确保生成流程的正确性和可追溯性',
    icon: Share,
    color: '#67c23a',
    bg: 'rgba(103, 194, 58, 0.1)',
  },
  {
    title: '智能体通信',
    description: '基于RocketMQ的智能体间消息通信，支持异步任务处理',
    icon: ChatDotRound,
    color: '#e6a23c',
    bg: 'rgba(230, 162, 60, 0.1)',
  },
  {
    title: '质量保证',
    description: '内置质量检查智能体，确保生成内容的连贯性和一致性',
    icon: CircleCheck,
    color: '#f56c6c',
    bg: 'rgba(245, 108, 108, 0.1)',
  },
]

// 技术栈 - 优化展示
const techStack = [
  { name: 'Vue 3', desc: '前端框架', icon: Monitor, color: '#409eff' },
  { name: 'TypeScript', desc: '类型系统', icon: Document, color: '#3178c6' },
  { name: 'FastAPI', desc: '后端框架', icon: Cpu, color: '#009688' },
  { name: 'Python', desc: '编程语言', icon: MagicStick, color: '#3572a5' },
  { name: 'Neo4j', desc: '图数据库', icon: Share, color: '#008cc1' },
  { name: 'MongoDB', desc: '文档数据库', icon: Collection, color: '#47A248' },
  { name: 'ChromaDB', desc: '向量数据库', icon: DataLine, color: '#424242' },
  { name: 'RocketMQ', desc: '消息队列', icon: ChatDotRound, color: '#9254de' },
]

// 架构层级
const archLayers = [
  { title: '用户界面', content: 'Vue3 + Element Plus', icon: Monitor, color: '#409eff', gradient: 'linear-gradient(135deg, #409eff 0%, #79bbff 100%)' },
  { title: 'API 网关层', content: 'FastAPI + WebSocket', icon: Cpu, color: '#67c23a', gradient: 'linear-gradient(135deg, #67c23a 0%, #95d475 100%)' },
  { title: '智能体编排', content: 'Coordinator + 12 Agents', icon: Connection, color: '#e6a23c', gradient: 'linear-gradient(135deg, #e6a23c 0%, #eebe77 100%)' },
  { title: '数据存储层', content: 'MySQL + Neo4j + MongoDB + ChromaDB', icon: Collection, color: '#f56c6c', gradient: 'linear-gradient(135deg, #f56c6c 0%, #f89898 100%)' },
]
</script>

<template>
  <div class="about-view">
    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="hero-badge">
          <el-icon><MagicStick /></el-icon>
          <span>AI 驱动的小说创作</span>
        </div>
        <h1 class="hero-title">AI Novel Generation System</h1>
        <p class="hero-description">基于多智能体协同工作的小说生成系统，让创作更高效、更智能</p>
        <div class="hero-stats">
          <div class="stat-item">
            <span class="stat-value">12</span>
            <span class="stat-label">智能体</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">v{{ projectInfo.version }}</span>
            <span class="stat-label">当前版本</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">{{ projectInfo.lastUpdated }}</span>
            <span class="stat-label">最后更新</span>
          </div>
        </div>
      </div>
      <div class="hero-glow"></div>
    </div>

    <!-- 功能特性 -->
    <div class="section">
      <div class="section-header">
        <div class="section-icon">
          <el-icon><StarFilled /></el-icon>
        </div>
        <div class="section-title-group">
          <h2 class="section-title">功能特性</h2>
          <p class="section-subtitle">强大的功能支撑，让小说创作变得简单</p>
        </div>
      </div>
      <div class="features-grid">
        <div
          v-for="(feature, index) in features"
          :key="feature.title"
          class="feature-card"
          :style="{ '--delay': `${index * 0.1}s` }"
        >
          <div class="feature-icon-wrapper" :style="{ background: feature.bg, color: feature.color }">
            <el-icon :size="28">
              <component :is="feature.icon" />
            </el-icon>
          </div>
          <div class="feature-content">
            <h3 class="feature-title">{{ feature.title }}</h3>
            <p class="feature-desc">{{ feature.description }}</p>
          </div>
          <div class="feature-arrow">
            <el-icon><ArrowRightBold /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- 技术栈 -->
    <div class="section">
      <div class="section-header">
        <div class="section-icon">
          <el-icon><Grid /></el-icon>
        </div>
        <div class="section-title-group">
          <h2 class="section-title">技术栈</h2>
          <p class="section-subtitle">现代化的技术选型，确保系统稳定高效</p>
        </div>
      </div>
      <div class="tech-grid">
        <div
          v-for="(tech, index) in techStack"
          :key="tech.name"
          class="tech-card"
          :style="{ '--delay': `${index * 0.05}s`, '--tech-color': tech.color }"
        >
          <div class="tech-icon" :style="{ background: `linear-gradient(135deg, ${tech.color}20 0%, ${tech.color}10 100%)`, color: tech.color }">
            <el-icon :size="24">
              <component :is="tech.icon" />
            </el-icon>
          </div>
          <div class="tech-info">
            <span class="tech-name">{{ tech.name }}</span>
            <span class="tech-desc">{{ tech.desc }}</span>
          </div>
          <div class="tech-glow" :style="{ background: tech.color }"></div>
        </div>
      </div>
    </div>

    <!-- 系统架构 -->
    <div class="section">
      <div class="section-header">
        <div class="section-icon">
          <el-icon><Connection /></el-icon>
        </div>
        <div class="section-title-group">
          <h2 class="section-title">系统架构</h2>
          <p class="section-subtitle">分层架构设计，清晰的数据流向</p>
        </div>
      </div>
      <div class="arch-container">
        <div class="arch-flow">
          <div
            v-for="(layer, index) in archLayers"
            :key="layer.title"
            class="arch-layer"
            :style="{ '--delay': `${index * 0.15}s` }"
          >
            <div class="layer-number">0{{ index + 1 }}</div>
            <div class="layer-card" :style="{ '--layer-gradient': layer.gradient }">
              <div class="layer-icon" :style="{ background: layer.gradient }">
                <el-icon :size="20"><component :is="layer.icon" /></el-icon>
              </div>
              <div class="layer-info">
                <span class="layer-title">{{ layer.title }}</span>
                <span class="layer-content">{{ layer.content }}</span>
              </div>
            </div>
            <div v-if="index < archLayers.length - 1" class="layer-connector">
              <div class="connector-line"></div>
              <el-icon class="connector-arrow"><ArrowRightBold /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 开发信息 -->
    <div class="section">
      <div class="dev-card">
        <div class="dev-icon">
          <el-icon :size="32"><User /></el-icon>
        </div>
        <div class="dev-content">
          <h3 class="dev-title">开发信息</h3>
          <p class="dev-text">
            本项目是基于AI技术的小说生成系统实现，用于演示多智能体协同工作和分布式系统架构。
            如有任何问题或建议，欢迎联系开发团队。
          </p>
        </div>
        <div class="dev-decoration"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.about-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
  color: #e2e8f0;
}

/* Hero Section */
.hero-section {
  position: relative;
  padding: 48px 40px;
  margin-bottom: 48px;
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
  border: 1px solid rgba(148, 163, 184, 0.1);
  overflow: hidden;
}

.hero-glow {
  position: absolute;
  top: -50%;
  right: -20%;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(56, 189, 248, 0.15) 0%, transparent 70%);
  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 1;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(6, 182, 212, 0.15);
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 20px;
  font-size: 13px;
  color: #22d3ee;
  margin-bottom: 20px;
}

.hero-title {
  font-size: 42px;
  font-weight: 700;
  background: linear-gradient(135deg, #f8fafc 0%, #94a3b8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 16px 0;
  letter-spacing: -0.02em;
}

.hero-description {
  font-size: 16px;
  color: #94a3b8;
  line-height: 1.6;
  margin: 0 0 32px 0;
  max-width: 600px;
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: 24px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #f8fafc;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: rgba(148, 163, 184, 0.2);
}

/* Section */
.section {
  margin-bottom: 48px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.section-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.2) 0%, rgba(6, 182, 212, 0.1) 100%);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 12px;
  color: #38bdf8;
}

.section-title-group {
  flex: 1;
}

.section-title {
  font-size: 22px;
  font-weight: 600;
  color: #f8fafc;
  margin: 0 0 4px 0;
}

.section-subtitle {
  font-size: 14px;
  color: #64748b;
  margin: 0;
}

/* Features Grid */
.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.feature-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 16px;
  transition: all 0.3s ease;
  cursor: pointer;
  animation: fadeInUp 0.6s ease forwards;
  animation-delay: var(--delay);
  opacity: 0;
}

.feature-card:hover {
  background: rgba(30, 41, 59, 0.8);
  border-color: rgba(56, 189, 248, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.feature-icon-wrapper {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  flex-shrink: 0;
}

.feature-content {
  flex: 1;
}

.feature-title {
  font-size: 16px;
  font-weight: 600;
  color: #f8fafc;
  margin: 0 0 6px 0;
}

.feature-desc {
  font-size: 13px;
  color: #94a3b8;
  line-height: 1.5;
  margin: 0;
}

.feature-arrow {
  color: #475569;
  transition: all 0.3s ease;
}

.feature-card:hover .feature-arrow {
  color: #38bdf8;
  transform: translateX(4px);
}

/* Tech Grid */
.tech-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.tech-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
  animation: fadeInUp 0.5s ease forwards;
  animation-delay: var(--delay);
  opacity: 0;
}

.tech-card:hover {
  background: rgba(30, 41, 59, 0.8);
  border-color: rgba(148, 163, 184, 0.2);
  transform: translateY(-2px);
}

.tech-card:hover .tech-glow {
  opacity: 0.15;
}

.tech-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  flex-shrink: 0;
}

.tech-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tech-name {
  font-size: 14px;
  font-weight: 600;
  color: #f8fafc;
}

.tech-desc {
  font-size: 12px;
  color: #64748b;
}

.tech-glow {
  position: absolute;
  top: -50%;
  right: -50%;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  filter: blur(40px);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

/* Architecture */
.arch-container {
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 20px;
  padding: 32px;
}

.arch-flow {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.arch-layer {
  display: flex;
  align-items: center;
  gap: 16px;
  animation: fadeInLeft 0.6s ease forwards;
  animation-delay: var(--delay);
  opacity: 0;
}

.layer-number {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  color: #38bdf8;
  flex-shrink: 0;
}

.layer-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 14px;
  transition: all 0.3s ease;
}

.layer-card:hover {
  background: rgba(30, 41, 59, 0.8);
  border-color: rgba(148, 163, 184, 0.2);
  transform: translateX(8px);
}

.layer-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  color: white;
  flex-shrink: 0;
}

.layer-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.layer-title {
  font-size: 15px;
  font-weight: 600;
  color: #f8fafc;
}

.layer-content {
  font-size: 13px;
  color: #94a3b8;
}

.layer-connector {
  display: flex;
  align-items: center;
  padding: 8px 0 8px 52px;
  gap: 8px;
}

.connector-line {
  width: 2px;
  height: 24px;
  background: linear-gradient(180deg, rgba(56, 189, 248, 0.3) 0%, rgba(56, 189, 248, 0.1) 100%);
}

.connector-arrow {
  color: rgba(56, 189, 248, 0.5);
  transform: rotate(90deg);
  font-size: 12px;
}

/* Dev Card */
.dev-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 20px;
  padding: 28px;
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 20px;
  overflow: hidden;
}

.dev-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(139, 92, 246, 0.15);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 14px;
  color: #a78bfa;
  flex-shrink: 0;
}

.dev-content {
  flex: 1;
}

.dev-title {
  font-size: 17px;
  font-weight: 600;
  color: #f8fafc;
  margin: 0 0 10px 0;
}

.dev-text {
  font-size: 14px;
  color: #94a3b8;
  line-height: 1.7;
  margin: 0;
}

.dev-decoration {
  position: absolute;
  top: -50%;
  right: -10%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.1) 0%, transparent 70%);
  pointer-events: none;
}

/* Animations */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInLeft {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* Responsive */
@media (max-width: 1024px) {
  .tech-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .about-view {
    padding: 16px;
  }

  .hero-section {
    padding: 32px 24px;
  }

  .hero-title {
    font-size: 28px;
  }

  .hero-stats {
    flex-wrap: wrap;
    gap: 16px;
  }

  .stat-divider {
    display: none;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .tech-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .arch-container {
    padding: 20px;
  }

  .layer-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>
