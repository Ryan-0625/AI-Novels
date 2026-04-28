<template>
  <div id="app">
    <!-- Aurora Background -->
    <div class="aurora-bg"></div>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

// 全局错误处理
onMounted(() => {
  window.addEventListener('error', (event) => {
    console.error('Global Error:', event.error)
  })
})
</script>

<style>
/* Import Glassmorphism Theme */
@import '@/styles/glassmorphism.css';

/* Global Reset */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  font-size: 16px;
  scroll-behavior: smooth;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0f172a;
  color: #f8fafc;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;
}

#app {
  width: 100%;
  min-height: 100vh;
  position: relative;
}

/* Aurora Background */
.aurora-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  background: 
    radial-gradient(ellipse at 20% 20%, rgba(6, 182, 212, 0.12) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 80%, rgba(139, 92, 246, 0.12) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 50%, rgba(236, 72, 153, 0.08) 0%, transparent 60%),
    #0f172a;
  animation: aurora-flow 20s ease-in-out infinite;
}

@keyframes aurora-flow {
  0%, 100% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
}

/* Element Plus Theme Overrides */
:root {
  --el-color-primary: #06b6d4;
  --el-color-primary-light-3: #22d3ee;
  --el-color-primary-light-5: #67e8f9;
  --el-color-primary-light-7: #a5f3fc;
  --el-color-primary-light-8: #cffafe;
  --el-color-primary-light-9: #ecfeff;
  --el-color-primary-dark-2: #0891b2;
  
  --el-bg-color: transparent;
  --el-bg-color-page: transparent;
  --el-bg-color-overlay: rgba(30, 41, 59, 0.9);
  
  --el-text-color-primary: #f8fafc;
  --el-text-color-regular: #e2e8f0;
  --el-text-color-secondary: #94a3b8;
  --el-text-color-placeholder: #64748b;
  --el-text-color-disabled: #475569;
  
  --el-border-color: rgba(255, 255, 255, 0.1);
  --el-border-color-light: rgba(255, 255, 255, 0.05);
  --el-border-color-lighter: rgba(255, 255, 255, 0.03);
  --el-border-color-extra-light: rgba(255, 255, 255, 0.02);
  --el-border-color-dark: rgba(255, 255, 255, 0.15);
  --el-border-color-darker: rgba(255, 255, 255, 0.2);
  
  --el-fill-color: rgba(255, 255, 255, 0.05);
  --el-fill-color-light: rgba(255, 255, 255, 0.08);
  --el-fill-color-lighter: rgba(255, 255, 255, 0.1);
  --el-fill-color-extra-light: rgba(255, 255, 255, 0.15);
  --el-fill-color-dark: rgba(0, 0, 0, 0.2);
  --el-fill-color-darker: rgba(0, 0, 0, 0.3);
  --el-fill-color-blank: transparent;
  
  --el-box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  --el-box-shadow-light: 0 4px 16px rgba(0, 0, 0, 0.2);
  --el-box-shadow-lighter: 0 2px 8px rgba(0, 0, 0, 0.15);
  --el-box-shadow-dark: 0 12px 48px rgba(0, 0, 0, 0.4);
}

/* Element Plus Component Overrides */
.el-button {
  border-radius: 10px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.el-button--primary {
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
  border: none;
}

.el-button--primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(6, 182, 212, 0.4);
}

.el-input__wrapper {
  background: rgba(15, 23, 42, 0.6) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
}

.el-input__wrapper:hover {
  border-color: rgba(6, 182, 212, 0.3) !important;
}

.el-input__wrapper.is-focus {
  border-color: rgba(6, 182, 212, 0.5) !important;
  box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1) !important;
}

.el-textarea__inner {
  background: rgba(15, 23, 42, 0.6) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 12px !important;
  color: #f8fafc !important;
}

.el-select .el-input__wrapper {
  background: rgba(15, 23, 42, 0.6) !important;
}

.el-slider__runway {
  background: rgba(255, 255, 255, 0.1);
  height: 6px;
  border-radius: 3px;
}

.el-slider__bar {
  background: linear-gradient(90deg, #06b6d4 0%, #3b82f6 100%);
  height: 6px;
  border-radius: 3px;
}

.el-slider__button {
  width: 18px;
  height: 18px;
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
  border: 2px solid #0f172a;
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.4);
}

.el-tag {
  border-radius: 6px;
  font-weight: 500;
}

.el-tag--primary {
  background: rgba(6, 182, 212, 0.15);
  border-color: rgba(6, 182, 212, 0.3);
  color: #06b6d4;
}

.el-tag--success {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.3);
  color: #10b981;
}

.el-tag--warning {
  background: rgba(245, 158, 11, 0.15);
  border-color: rgba(245, 158, 11, 0.3);
  color: #f59e0b;
}

.el-tag--danger {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.el-tag--info {
  background: rgba(100, 116, 139, 0.15);
  border-color: rgba(100, 116, 139, 0.3);
  color: #64748b;
}

.el-progress-bar__outer {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.el-progress-bar__inner {
  border-radius: 4px;
}

.el-table {
  background: transparent !important;
  color: #e2e8f0;
}

.el-table th.el-table__cell {
  background: transparent !important;
  color: #94a3b8;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.el-table td.el-table__cell {
  background: transparent !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.el-table--enable-row-hover .el-table__body tr:hover > td.el-table__cell {
  background: rgba(255, 255, 255, 0.03) !important;
}

.el-menu {
  background: transparent !important;
  border: none !important;
}

.el-menu-item {
  color: #94a3b8 !important;
  border-radius: 12px;
  margin: 4px 8px;
  transition: all 0.3s ease;
}

.el-menu-item:hover {
  background: rgba(255, 255, 255, 0.05) !important;
  color: #e2e8f0 !important;
}

.el-menu-item.is-active {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.2) 0%, rgba(59, 130, 246, 0.2) 100%) !important;
  color: #06b6d4 !important;
}

.el-loading-mask {
  background: rgba(15, 23, 42, 0.8) !important;
  backdrop-filter: blur(4px);
}

/* Scrollbar Styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.5);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.5);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.5);
}

/* Selection Styling */
::selection {
  background: rgba(6, 182, 212, 0.3);
  color: #f8fafc;
}

/* Focus Visible */
:focus-visible {
  outline: 2px solid rgba(6, 182, 212, 0.5);
  outline-offset: 2px;
}

/* Reduced Motion */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
