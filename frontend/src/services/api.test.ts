import { describe, expect, it } from 'vitest'
import { parseSseStream } from './api'

const encoder = new TextEncoder()

describe('parseSseStream', () => {
  it('preserva evento dividido entre pacotes e encerra em done', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"chunk":"Olá, ","done":fal'))
        controller.enqueue(encoder.encode('se}\n\ndata: {"chunk":"viajante!","done":false}\r\n\r\n'))
        controller.enqueue(encoder.encode('data: {"chunk":"","done":true}\n\n'))
        controller.enqueue(encoder.encode('data: {"chunk":"duplicado","done":false}\n\n'))
        controller.close()
      },
    })

    const events = []
    for await (const event of parseSseStream(stream)) events.push(event)

    expect(events).toEqual([
      { chunk: 'Olá, ', done: false },
      { chunk: 'viajante!', done: false },
      { chunk: '', done: true },
    ])
  })

  it('combina múltiplas linhas data do mesmo evento', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"chunk":"linha",\ndata: "done":false}\n\n'))
        controller.close()
      },
    })
    const events = []
    for await (const event of parseSseStream(stream)) events.push(event)
    expect(events[0]).toEqual({ chunk: 'linha', done: false })
  })
})
