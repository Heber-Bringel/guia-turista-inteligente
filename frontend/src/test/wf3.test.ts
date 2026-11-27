import { describe, expect, it } from 'vitest'
import wf3Workflow from '../../../n8n/workflows/wf3-despacho-roteiro.json'

interface N8nNode {
  name: string
  type: string
  parameters?: Record<string, unknown>
}

interface N8nWorkflow {
  name: string
  nodes: N8nNode[]
  connections: Record<string, unknown>
}

describe('Workflow 3 n8n (wf3-despacho-roteiro.json)', () => {
  it('define webhook turismo-despachar-roteiro, roteamento email/whatsapp e zero segredos hardcoded', () => {
    const workflow = wf3Workflow as unknown as N8nWorkflow
    const raw = JSON.stringify(workflow)

    expect(workflow.nodes.length).toBeGreaterThanOrEqual(6)

    const webhookNode = workflow.nodes.find((node) => node.type === 'n8n-nodes-base.webhook')
    expect(webhookNode?.parameters?.path).toBe('turismo-despachar-roteiro')
    expect(webhookNode?.parameters?.httpMethod).toBe('POST')

    const switchNode = workflow.nodes.find((node) => node.type === 'n8n-nodes-base.switch')
    expect(switchNode).toBeDefined()
    expect(JSON.stringify(switchNode?.parameters)).toContain('email')
    expect(JSON.stringify(switchNode?.parameters)).toContain('whatsapp')

    const httpNodes = workflow.nodes.filter((node) => node.type === 'n8n-nodes-base.httpRequest')
    expect(httpNodes.length).toBe(2)

    // Garante uso de variáveis de ambiente sem credenciais hardcoded
    expect(raw).toContain('$env.RESEND_API_KEY')
    expect(raw).toContain('$env.WHATSAPP_API_KEY')
    expect(raw).not.toMatch(/re_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,}/)
  })
})
