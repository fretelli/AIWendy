'use client'

import { useCallback, useEffect, useState } from 'react'
import { BrainCircuit, Check, Database, KeyRound, Loader2, Play, RefreshCw, Server, Timer, X } from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { agentPlatformApi, type AgentApproval, type AgentDefinition, type AgentMemory, type AgentModelProfile, type AgentRun, type AgentSchedule, type MCPServer, type Usage } from '@/lib/api/agent-platform'

const builtinTools = ['query_research_reports', 'query_tushare_data', 'run_daily_brief', 'deep_research', 'run_weekly_review', 'record_fundamental_validation', 'record_investment_decision']

export default function AgentPlatformPage() {
  const [loading, setLoading] = useState(true)
  const [models, setModels] = useState<AgentModelProfile[]>([])
  const [agents, setAgents] = useState<AgentDefinition[]>([])
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [approvals, setApprovals] = useState<AgentApproval[]>([])
  const [memories, setMemories] = useState<AgentMemory[]>([])
  const [mcp, setMcp] = useState<MCPServer[]>([])
  const [schedules, setSchedules] = useState<AgentSchedule[]>([])
  const [usage, setUsage] = useState<Usage | null>(null)
  const [availableTools, setAvailableTools] = useState<Array<{ name: string; label: string }>>(
    builtinTools.map(name => ({ name, label: name })),
  )
  const [prompt, setPrompt] = useState('分析我的关注标的近期基本面变化、主要分歧、风险和可证伪条件。')
  const [selectedAgent, setSelectedAgent] = useState('')
  const [modelForm, setModelForm] = useState({ name: '', provider: 'openai', base_url: '', model: '', api_key: '', context_window: 128000, max_output_tokens: 4096, input_cost_per_million: 0, output_cost_per_million: 0 })
  const [agentForm, setAgentForm] = useState({ name: '', role: 'custom', description: '', system_prompt: 'You are a fundamental investment research agent. Never place trades. Cite evidence and state uncertainty.', model_profile_id: '', tool_names: builtinTools.slice(0, 6), memory_enabled: true, max_steps: 12, max_parallel: 3, task_token_budget: 50000, task_cost_budget_usd: 5 })
  const [mcpForm, setMcpForm] = useState({ name: '', url: '', auth_token: '' })
  const [scheduleForm, setScheduleForm] = useState({ name: '', prompt: '', cron: '0 9 * * *', timezone: 'Asia/Shanghai' })

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [modelData, agentData, runData, approvalData, memoryData, mcpData, scheduleData, usageData] = await Promise.all([
        agentPlatformApi.models(), agentPlatformApi.agents(), agentPlatformApi.runs(), agentPlatformApi.approvals(),
        agentPlatformApi.memories(true), agentPlatformApi.mcpServers(), agentPlatformApi.schedules(), agentPlatformApi.usage(),
      ])
      setModels(modelData.items); setAgents(agentData.items); setRuns(runData.items); setApprovals(approvalData.items)
      setMemories(memoryData.items); setMcp(mcpData.items); setSchedules(scheduleData.items); setUsage(usageData)
      setAvailableTools([
        ...agentData.builtin_tools.map(name => ({ name, label: name })),
        ...agentData.mcp_tools.map(tool => ({ name: tool.name, label: `${tool.server} · ${tool.name.split(':').slice(2).join(':')}` })),
      ])
      if (!selectedAgent && agentData.items[0]) setSelectedAgent(agentData.items[0].id)
    } catch (error) { toast.error(error instanceof Error ? error.message : 'Failed to load Agent Platform') }
    finally { setLoading(false) }
  }, [selectedAgent])

  useEffect(() => { queueMicrotask(() => void refresh()) }, [refresh])

  const submit = async (fn: () => Promise<unknown>, success: string) => {
    try { await fn(); toast.success(success); await refresh() }
    catch (error) { toast.error(error instanceof Error ? error.message : 'Request failed') }
  }

  if (loading && !models.length && !agents.length) return <div className="flex h-full items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>

  return <div className="h-full overflow-y-auto p-4 md:p-6"><div className="mx-auto max-w-7xl space-y-5">
    <div className="flex items-center justify-between"><div><h1 className="flex items-center gap-2 text-2xl font-bold"><BrainCircuit />Agent 工作台</h1><p className="text-sm text-muted-foreground">持久任务、工具审批、BYOK、MCP、记忆与预算。研究模式，不执行交易。</p></div><Button variant="outline" onClick={refresh}><RefreshCw className="mr-2 h-4 w-4" />刷新</Button></div>
    <div className="grid gap-3 md:grid-cols-4"><Metric title="运行中" value={runs.filter(r => !['completed','failed','cancelled'].includes(r.status)).length} /><Metric title="待审批" value={approvals.length} /><Metric title="今日 Tokens" value={(usage?.today.input_tokens || 0) + (usage?.today.output_tokens || 0)} /><Metric title="今日成本" value={`$${(usage?.today.cost_usd || 0).toFixed(4)}`} /></div>
    <Tabs defaultValue="run"><TabsList className="flex h-auto flex-wrap justify-start"><TabsTrigger value="run">任务</TabsTrigger><TabsTrigger value="agents">Agents</TabsTrigger><TabsTrigger value="approvals">审批</TabsTrigger><TabsTrigger value="memory">记忆</TabsTrigger><TabsTrigger value="models">BYOK</TabsTrigger><TabsTrigger value="mcp">MCP</TabsTrigger><TabsTrigger value="schedules">定时</TabsTrigger></TabsList>
      <TabsContent value="run" className="space-y-4"><Card><CardHeader><CardTitle>启动研究任务</CardTitle></CardHeader><CardContent className="space-y-3"><select className="w-full rounded-md border bg-background p-2" value={selectedAgent} onChange={e => setSelectedAgent(e.target.value)}><option value="">选择 Agent</option>{agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select><Textarea value={prompt} onChange={e => setPrompt(e.target.value)} /><Button disabled={!selectedAgent || !prompt.trim()} onClick={() => submit(() => agentPlatformApi.createRun({ agent_definition_id: selectedAgent, prompt }), '任务已进入队列')}><Play className="mr-2 h-4 w-4" />运行</Button></CardContent></Card><div className="space-y-2">{runs.map(run => <Card key={run.id}><CardContent className="flex items-start justify-between p-4"><div><div className="font-medium">{run.prompt}</div><div className="mt-2 flex gap-2"><Badge>{run.status}</Badge><Badge variant="outline">步骤 {run.current_step}</Badge><Badge variant="outline">{run.tokens_used} tokens</Badge></div></div>{!['completed','failed','cancelled'].includes(run.status) && <Button size="sm" variant="outline" onClick={() => submit(() => agentPlatformApi.controlRun(run.id, 'cancel'), '任务已取消')}><X className="h-4 w-4" /></Button>}</CardContent></Card>)}</div></TabsContent>
      <TabsContent value="agents" className="space-y-4"><Card><CardHeader><CardTitle>声明式自定义 Agent</CardTitle></CardHeader><CardContent className="grid gap-3"><Input placeholder="名称" value={agentForm.name} onChange={e => setAgentForm({...agentForm,name:e.target.value})} /><Input placeholder="描述" value={agentForm.description} onChange={e => setAgentForm({...agentForm,description:e.target.value})} /><select className="rounded-md border bg-background p-2" value={agentForm.model_profile_id} onChange={e => setAgentForm({...agentForm,model_profile_id:e.target.value})}><option value="">选择 BYOK 模型</option>{models.map(m => <option key={m.id} value={m.id}>{m.name} · {m.model}</option>)}</select><Textarea value={agentForm.system_prompt} onChange={e => setAgentForm({...agentForm,system_prompt:e.target.value})} /><div className="flex flex-wrap gap-2">{availableTools.map(tool => <label key={tool.name} className="flex items-center gap-1 rounded border px-2 py-1 text-xs"><input type="checkbox" checked={agentForm.tool_names.includes(tool.name)} onChange={e => setAgentForm({...agentForm,tool_names:e.target.checked?[...agentForm.tool_names,tool.name]:agentForm.tool_names.filter(x=>x!==tool.name)})}/>{tool.label}</label>)}</div><Button onClick={() => submit(() => agentPlatformApi.createAgent(agentForm), 'Agent 已创建')}>创建 Agent</Button></CardContent></Card><div className="grid gap-3 md:grid-cols-2">{agents.map(a => <Card key={a.id}><CardContent className="p-4"><div className="font-medium">{a.name}</div><div className="text-sm text-muted-foreground">{a.role} · {a.tool_names.length} tools</div></CardContent></Card>)}</div></TabsContent>
      <TabsContent value="approvals" className="space-y-3">{approvals.length ? approvals.map(item => <Card key={item.id}><CardContent className="space-y-3 p-4"><Badge>{item.kind}</Badge><pre className="overflow-auto rounded bg-muted p-3 text-xs">{JSON.stringify(item.preview,null,2)}</pre><div className="flex flex-wrap gap-2"><Button onClick={() => submit(() => agentPlatformApi.resolveApproval(item.id,'approved','once'),'本次调用已批准')}><Check className="mr-2 h-4 w-4" />仅本次</Button>{item.kind === 'mcp_tool' && <Button variant="secondary" onClick={() => submit(() => agentPlatformApi.resolveApproval(item.id,'approved','always'),'该 Agent 已永久获准使用此工具')}>永久允许</Button>}<Button variant="destructive" onClick={() => submit(() => agentPlatformApi.resolveApproval(item.id,'rejected'),'已拒绝')}><X className="mr-2 h-4 w-4" />拒绝</Button></div></CardContent></Card>) : <Empty text="没有待审批操作" />}</TabsContent>
      <TabsContent value="memory" className="space-y-3">{memories.length ? memories.map(item => <Card key={item.id}><CardContent className="flex items-start justify-between p-4"><div><div className="font-medium">{item.key}</div><pre className="mt-2 max-w-3xl whitespace-pre-wrap text-xs">{JSON.stringify(item.value,null,2)}</pre><div className="text-xs text-muted-foreground">v{item.version} · confidence {item.confidence}</div></div><Button variant="outline" size="sm" onClick={() => submit(() => item.is_deleted ? agentPlatformApi.restoreMemory(item.id) : agentPlatformApi.deleteMemory(item.id), item.is_deleted?'记忆已恢复':'记忆已撤销')}>{item.is_deleted?'恢复':'撤销'}</Button></CardContent></Card>) : <Empty text="尚无长期记忆" />}</TabsContent>
      <TabsContent value="models"><Card><CardHeader><CardTitle><KeyRound className="mr-2 inline h-5 w-5" />用户 BYOK</CardTitle></CardHeader><CardContent className="grid gap-3 md:grid-cols-2"><Input placeholder="配置名称" value={modelForm.name} onChange={e => setModelForm({...modelForm,name:e.target.value})}/><select className="rounded-md border bg-background p-2" value={modelForm.provider} onChange={e => setModelForm({...modelForm,provider:e.target.value})}><option value="openai">OpenAI-compatible</option><option value="anthropic">Anthropic</option></select><Input placeholder="Base URL（官方可留空）" value={modelForm.base_url} onChange={e => setModelForm({...modelForm,base_url:e.target.value})}/><Input placeholder="Model" value={modelForm.model} onChange={e => setModelForm({...modelForm,model:e.target.value})}/><Input type="password" placeholder="API Key" value={modelForm.api_key} onChange={e => setModelForm({...modelForm,api_key:e.target.value})}/><Input type="number" placeholder="Context window" value={modelForm.context_window} onChange={e => setModelForm({...modelForm,context_window:Number(e.target.value)})}/><Input type="number" placeholder="输入 $/1M" value={modelForm.input_cost_per_million} onChange={e => setModelForm({...modelForm,input_cost_per_million:Number(e.target.value)})}/><Input type="number" placeholder="输出 $/1M" value={modelForm.output_cost_per_million} onChange={e => setModelForm({...modelForm,output_cost_per_million:Number(e.target.value)})}/><Button className="md:col-span-2" onClick={() => submit(() => agentPlatformApi.createModel({...modelForm,base_url:modelForm.base_url||null}),'模型凭证已加密保存')}>保存 BYOK</Button></CardContent></Card></TabsContent>
      <TabsContent value="mcp" className="space-y-4"><Card><CardHeader><CardTitle><Server className="mr-2 inline h-5 w-5" />添加公网 HTTPS MCP</CardTitle></CardHeader><CardContent className="grid gap-3"><Input placeholder="名称" value={mcpForm.name} onChange={e => setMcpForm({...mcpForm,name:e.target.value})}/><Input placeholder="https://..." value={mcpForm.url} onChange={e => setMcpForm({...mcpForm,url:e.target.value})}/><Input type="password" placeholder="Bearer Token（可选）" value={mcpForm.auth_token} onChange={e => setMcpForm({...mcpForm,auth_token:e.target.value})}/><Button onClick={() => submit(() => agentPlatformApi.createMcp({...mcpForm,auth_token:mcpForm.auth_token||null}),'MCP 已连接')}>发现工具</Button></CardContent></Card>{mcp.map(server => <Card key={server.id}><CardContent className="p-4"><div className="font-medium">{server.name} <Badge>{server.status}</Badge></div><div className="text-xs text-muted-foreground">{server.url}</div><p className="mt-2 text-xs text-muted-foreground">在 Agent 配置中启用工具；首次携带真实参数调用时会进入审批中心。</p><div className="mt-3 flex flex-wrap gap-2">{server.tools_snapshot.map(tool => <Badge key={tool.name} variant="outline">{tool.name}</Badge>)}</div></CardContent></Card>)}</TabsContent>
      <TabsContent value="schedules" className="space-y-4"><Card><CardHeader><CardTitle><Timer className="mr-2 inline h-5 w-5" />每日研究计划</CardTitle></CardHeader><CardContent className="grid gap-3"><select className="rounded-md border bg-background p-2" value={selectedAgent} onChange={e=>setSelectedAgent(e.target.value)}><option value="">选择 Agent</option>{agents.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select><Input placeholder="计划名称" value={scheduleForm.name} onChange={e=>setScheduleForm({...scheduleForm,name:e.target.value})}/><Textarea placeholder="研究任务" value={scheduleForm.prompt} onChange={e=>setScheduleForm({...scheduleForm,prompt:e.target.value})}/><Input placeholder="0 9 * * *" value={scheduleForm.cron} onChange={e=>setScheduleForm({...scheduleForm,cron:e.target.value})}/><Button onClick={() => submit(() => agentPlatformApi.createSchedule({...scheduleForm,agent_definition_id:selectedAgent}),'定时研究已创建')}>创建计划</Button></CardContent></Card>{schedules.map(item=><Card key={item.id}><CardContent className="p-4"><div className="font-medium">{item.name}</div><div className="text-sm text-muted-foreground">{item.cron} · next {item.next_run_at||'-'}</div></CardContent></Card>)}</TabsContent>
    </Tabs>
  </div></div>
}

function Metric({title,value}:{title:string;value:string|number}) { return <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">{title}</div><div className="text-2xl font-semibold">{value}</div></CardContent></Card> }
function Empty({text}:{text:string}) { return <Card><CardContent className="p-8 text-center text-sm text-muted-foreground"><Database className="mx-auto mb-2 h-5 w-5" />{text}</CardContent></Card> }
