import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import SystemPanel from './panels/SystemPanel.jsx'
import HardwarePanel from './panels/HardwarePanel.jsx'
import ModelsPanel from './panels/ModelsPanel.jsx'
import ModelStore from './panels/ModelStore.jsx'
import GhostEnginePanel from './panels/GhostEnginePanel.jsx'
import SkillsPanel from './panels/SkillsPanel.jsx'
import HealthPanel from './panels/HealthPanel.jsx'
import GovernancePanel from './panels/GovernancePanel.jsx'
import SchedulerPanel from './panels/SchedulerPanel.jsx'
import PluginsPanel from './panels/PluginsPanel.jsx'
import StatsPanel from './panels/StatsPanel.jsx'
import MemoryPanel from './panels/MemoryPanel.jsx'
import WorkspacePanel from './panels/WorkspacePanel.jsx'
import ChatHistoryPanel from './panels/ChatHistoryPanel.jsx'

const TITLES = {
  activity: 'Agent Activity', chats: 'Chats',
  system: 'System & Health', models: 'Models & Ghost Engine',
  skills: 'Agents', governance: 'Approvals',
  scheduler: 'Scheduler', plugins: 'Tools', stats: 'Usage & Stats',
  memory: 'Memory', workspace: 'Projects',
}

function PanelSection({ title, desc, children }) {
  return (
    <div className="panel-section">
      <div className="panel-section-title">{title}</div>
      {desc && <p className="panel-section-desc">{desc}</p>}
      {children}
    </div>
  )
}

// Merged: system status + live hardware + health bars were three separate
// tabs showing overlapping CPU/RAM/GPU numbers. One "System & Health" tab.
function SystemAndHealthPanel({ systemStatus, hardwareStatus, hwLive, healthData, onSwitchModel }) {
  return (
    <div>
      <PanelSection title="System" desc="Which model's running, is memory connected, how long ILLIP's been up.">
        <SystemPanel data={systemStatus} />
      </PanelSection>
      <PanelSection title="Hardware" desc="Your machine's specs, and how hot/busy it's running right now.">
        <HardwarePanel data={hardwareStatus} live={hwLive} onSwitchModel={onSwitchModel} />
      </PanelSection>
      <PanelSection title="Health" desc="Quick health check — CPU, RAM, GPU load and disk space.">
        <HealthPanel data={healthData} />
      </PanelSection>
    </div>
  )
}

// Merged: model list (switch) + Ghost Engine (per-model GPU/VRAM plan) were
// two separate tabs about the same models. One "Models & Ghost Engine" tab.
function ModelsAndGhostPanel({ modelsData, onSwitchModel, pinnedModel, onDeleteModel, onModelsChanged }) {
  return (
    <div>
      <PanelSection title="Installed Models" desc="Every AI model on your machine — click one to switch ILLIP's brain.">
        <ModelsPanel data={modelsData} onSwitch={onSwitchModel} onDelete={onDeleteModel} />
      </PanelSection>
      <PanelSection title="Get Models" desc="Curated picks sized for your hardware — download with one click.">
        <ModelStore onInstalled={onModelsChanged} />
      </PanelSection>
      <PanelSection title="Ghost Engine Plan" desc="Maps each model to an optimal GPU/CPU split for your hardware.">
        <GhostEnginePanel models={modelsData} activeModel={modelsData?.active || pinnedModel} />
      </PanelSection>
    </div>
  )
}

function ActivityPanel({ agentTask, connected, statusText, modelsData, hwLive, activeProject, onNewChat, onNavigate, onOpenBrowser, onOpenImage, onOpenVideo }) {
  const [tab, setTab] = useState('activity')
  const [recentFiles, setRecentFiles] = useState([])
  useEffect(() => {
    let alive = true
    api.wsFiles().then(d => { if (alive) setRecentFiles((d.files || []).slice(0, 4)) }).catch(() => {})
    return () => { alive = false }
  }, [activeProject])
  const task = agentTask?.goal || (typeof agentTask === 'string' ? agentTask : '')
  const ram = hwLive?.ram_percent
  const gpu = hwLive?.gpu_util_pct ?? hwLive?.gpu_pct
  return (
    <div className="activity-dashboard">
      <div className="activity-tabs">
        <button className={tab === 'activity' ? 'active' : ''} onClick={() => setTab('activity')}>Agent Activity</button>
        <button className={tab === 'tools' ? 'active' : ''} onClick={() => setTab('tools')}>Tools</button>
        <button className={tab === 'plan' ? 'active' : ''} onClick={() => setTab('plan')}>Plan</button>
      </div>
      {tab === 'activity' && <>
        <section className="activity-card current-agent-card">
          <div className="activity-card-heading"><strong>Current Agent</strong><span className={`activity-state ${task ? 'running' : 'ready'}`}><i />{task ? 'Running' : 'Ready'}</span></div>
          <div className="agent-identity"><span className="agent-avatar">⌘</span><div><strong>{task ? 'Task Agent' : 'ILLIP Assistant'}</strong><small>{task ? 'Working on your requested task' : 'Ready for your next instruction'}</small></div></div>
          <div className="agent-task-line">{task || 'No active task. Start a chat or launch an agent task.'}</div>
          <div className="activity-progress-track"><span className={task ? 'active' : ''} /></div>
          <div className="activity-subnote">{task ? (agentTask?.loop ? 'Agent loop active' : 'Task submitted') : 'Waiting for a task'}</div>
        </section>
        <section className="activity-card">
          <div className="activity-card-heading"><strong>Quick Tools</strong><button className="activity-link" onClick={() => onNavigate('plugins')}>View all</button></div>
          <div className="quick-tool-grid">
            <button onClick={onOpenBrowser}><span>◎</span>Browser</button>
            <button onClick={onOpenImage}><span>▧</span>Image</button>
            <button onClick={onOpenVideo}><span>▷</span>Video</button>
            <button onClick={() => onNavigate('workspace')}><span>▱</span>Workspace</button>
          </div>
        </section>
        <section className="activity-card">
          <div className="activity-card-heading"><strong>Recent Files</strong><button className="activity-link" onClick={() => onNavigate('workspace')}>View all</button></div>
          {recentFiles.length ? <div className="activity-file-list">{recentFiles.map((f, i) => <div className="activity-file" key={`${f.name || f.filename || 'file'}-${i}`}><span>▤</span><div><strong>{f.name || f.filename || 'Workspace file'}</strong><small>{f.path || 'Project workspace'}</small></div></div>)}</div> : <p className="activity-empty">No recent files in this workspace.</p>}
        </section>
        <section className="activity-card status-card">
          <div className="activity-card-heading"><strong>System Status</strong><span className={`activity-state ${connected ? 'running' : 'ready'}`}><i />{connected ? 'Online' : 'Connecting'}</span></div>
          <div className="status-line"><span>Ollama</span><b>{connected ? 'Connected' : 'Checking'}</b></div>
          <div className="status-line"><span>Model</span><b>{modelsData?.active || 'Auto'}</b></div>
          {ram != null && <div className="status-line"><span>RAM</span><b>{Math.round(ram)}%</b></div>}
          {gpu != null && <div className="status-line"><span>GPU</span><b>{Math.round(gpu)}%</b></div>}
          <small className="status-footnote">{statusText || 'Local system connection status'}</small>
        </section>
      </>}
      {tab === 'tools' && <section className="activity-card activity-tools-list">
        <strong>Available tools</strong>
        <button onClick={onOpenBrowser}><span>◎</span><div><b>Browser</b><small>Open the integrated browser workspace</small></div><em>›</em></button>
        <button onClick={onOpenImage}><span>▧</span><div><b>Image generation</b><small>Create images from a prompt</small></div><em>›</em></button>
        <button onClick={onOpenVideo}><span>▷</span><div><b>Video generation</b><small>Open the video workspace</small></div><em>›</em></button>
        <button onClick={() => onNavigate('plugins')}><span>⌘</span><div><b>Connected tools</b><small>Manage plugins and integrations</small></div><em>›</em></button>
        <button onClick={() => onNavigate('skills')}><span>♧</span><div><b>Agent skills</b><small>Browse installed skills</small></div><em>›</em></button>
      </section>}
      {tab === 'plan' && <section className="activity-card activity-plan-card">
        <strong>Workspace overview</strong>
        <div className="status-line"><span>Active project</span><b>{activeProject || 'Default'}</b></div>
        <div className="status-line"><span>Selected model</span><b>{modelsData?.active || 'Auto'}</b></div>
        <div className="plan-current-task"><small>Current task</small><p>{task || 'No task is currently running.'}</p></div>
        <button className="activity-primary-btn" onClick={onNewChat}>Start a new task</button>
      </section>}
    </div>
  )
}

export default function SlidePanel({
  activePanel, onClose, pinned = false,
  systemStatus, hardwareStatus, hwLive, modelsData, skills,
  plugins, healthData, govPending, schedulerJobs, stats, pinnedModel,
  onSwitchModel, onDeleteModel, onModelsChanged, onGovApprove, onGovDeny, onSchedRun, onSchedToggle,
  onAddPlugin, onDeletePlugin, onInstallSkill, onShowMarketplace, onCreateJob,
  activeProject, projects, onSwitchProject, onDeleteProject, onNewChat,
  agentTask, connected, statusText, onOpenBrowser, onOpenImage, onOpenVideo,
  onNavigate = () => {},
}) {
  const panelProps = {
    activity:   { component: ActivityPanel, props: { agentTask, connected, statusText, modelsData, hwLive, activeProject, onNewChat, onNavigate, onOpenBrowser, onOpenImage, onOpenVideo } },
    chats:      { component: ChatHistoryPanel,     props: { projects, activeProject, onSwitchProject, onDeleteProject, onNewChat, onClose } },
    system:     { component: SystemAndHealthPanel, props: { systemStatus, hardwareStatus, hwLive, healthData, onSwitchModel } },
    models:     { component: ModelsAndGhostPanel,  props: { modelsData, onSwitchModel, pinnedModel, onDeleteModel, onModelsChanged } },
    skills:     { component: SkillsPanel,          props: { skills, onInstall: onInstallSkill } },
    governance: { component: GovernancePanel,      props: { pending: govPending, onApprove: onGovApprove, onDeny: onGovDeny } },
    scheduler:  { component: SchedulerPanel,       props: { jobs: schedulerJobs, onRun: onSchedRun, onToggle: onSchedToggle, onCreate: onCreateJob } },
    plugins:    { component: PluginsPanel,         props: { plugins, onAdd: onAddPlugin, onDelete: onDeletePlugin, onMarketplace: onShowMarketplace } },
    stats:      { component: StatsPanel,           props: { data: stats } },
    memory:     { component: MemoryPanel,          props: { projectId: activeProject || 'default' } },
    workspace:  { component: WorkspacePanel,       props: { projectId: activeProject || 'default' } },
  }

  const current = activePanel ? panelProps[activePanel] : null
  const PanelComponent = current?.component

  return (
    <div className={`slide-panel ${activePanel ? 'open' : ''} ${pinned ? 'pinned' : ''}`}>
      <div className="slide-panel-header">
        <span className="slide-panel-title">{TITLES[activePanel] || ''}</span>
        <button className="slide-close-btn" onClick={onClose}>✕</button>
      </div>
      <div className="slide-panel-body">
        {PanelComponent && (
          <div className="tab-content">
            <PanelComponent {...(current.props || {})} />
          </div>
        )}
      </div>
    </div>
  )
}
