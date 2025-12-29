import { useEffect, useRef, useState } from 'react'
import { Terminal, X, Minimize2, Maximize2, Trash2 } from 'lucide-react'

interface LogEntry {
  timestamp: string
  message: string
  level: string
}

interface Task {
  id: string
  name: string
  status: string
  progress: number
  logs: LogEntry[]
}

interface LogPanelProps {
  isOpen: boolean
  onToggle: () => void
}

export function LogPanel({ isOpen, onToggle }: LogPanelProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [isMinimized, setIsMinimized] = useState(false)
  const logEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    // Connect to SSE endpoint
    const connect = () => {
      const eventSource = new EventSource('/api/tasks/stream')
      eventSourceRef.current = eventSource

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleEvent(data)
        } catch (e) {
          console.error('Failed to parse SSE event:', e)
        }
      }

      eventSource.onerror = () => {
        eventSource.close()
        // Reconnect after 2 seconds
        setTimeout(connect, 2000)
      }
    }

    connect()

    return () => {
      eventSourceRef.current?.close()
    }
  }, [])

  const handleEvent = (event: any) => {
    switch (event.type) {
      case 'task_state':
      case 'task_created':
      case 'task_started':
        setTasks((prev) => {
          const existing = prev.find((t) => t.id === event.task.id)
          if (existing) {
            return prev.map((t) => (t.id === event.task.id ? event.task : t))
          }
          return [...prev, event.task].slice(-10) // Keep last 10 tasks
        })
        break

      case 'task_completed':
      case 'task_failed':
        setTasks((prev) =>
          prev.map((t) => (t.id === event.task.id ? event.task : t))
        )
        break

      case 'log':
        setTasks((prev) =>
          prev.map((t) =>
            t.id === event.task_id
              ? { ...t, logs: [...t.logs, event.entry] }
              : t
          )
        )
        break

      case 'progress':
        setTasks((prev) =>
          prev.map((t) =>
            t.id === event.task_id ? { ...t, progress: event.progress } : t
          )
        )
        break
    }
  }

  // Auto-scroll to bottom
  useEffect(() => {
    if (!isMinimized) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [tasks, isMinimized])

  const clearLogs = () => {
    setTasks([])
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-matrix-glow'
      case 'completed':
        return 'text-matrix-green'
      case 'failed':
        return 'text-red-500'
      default:
        return 'text-matrix-dim'
    }
  }

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'error':
        return 'text-red-500'
      case 'warning':
        return 'text-yellow-500'
      case 'progress':
        return 'text-matrix-glow'
      default:
        return 'text-matrix-darkgreen'
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed bottom-4 right-4 p-3 bg-matrix-bg hover:bg-matrix-dim/30 rounded-full shadow-matrix border border-matrix-dim z-50 text-matrix-green"
        title="Open log panel"
      >
        <Terminal className="w-5 h-5" />
        {tasks.some((t) => t.status === 'running') && (
          <span className="absolute top-0 right-0 w-3 h-3 bg-matrix-glow rounded-full animate-pulse" />
        )}
      </button>
    )
  }

  return (
    <div
      className={`fixed bottom-0 right-0 bg-matrix-bg border-l border-t border-matrix-dim shadow-matrix-lg z-50 flex flex-col ${
        isMinimized ? 'w-80 h-12' : 'w-96 h-80'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-matrix-bg border-b border-matrix-dim">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-matrix-green" />
          <span className="text-sm font-medium text-matrix-green">Task Log</span>
          {tasks.some((t) => t.status === 'running') && (
            <span className="w-2 h-2 bg-matrix-glow rounded-full animate-pulse" />
          )}
        </div>
        <div className="flex items-center gap-1 text-matrix-green">
          <button
            onClick={clearLogs}
            className="p-1 hover:bg-matrix-dim/30 rounded"
            title="Clear logs"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-1 hover:bg-matrix-dim/30 rounded"
            title={isMinimized ? 'Expand' : 'Minimize'}
          >
            {isMinimized ? (
              <Maximize2 className="w-4 h-4" />
            ) : (
              <Minimize2 className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={onToggle}
            className="p-1 hover:bg-matrix-dim/30 rounded"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      {!isMinimized && (
        <div className="flex-1 overflow-auto p-2 font-mono text-xs">
          {tasks.length === 0 ? (
            <div className="text-matrix-dim text-center py-4">
              No tasks yet. Extract or OCR a subtitle to see activity.
            </div>
          ) : (
            tasks.map((task) => (
              <div key={task.id} className="mb-3">
                {/* Task header */}
                <div className="flex items-center gap-2 mb-1">
                  <span className={`font-semibold ${getStatusColor(task.status)}`}>
                    [{task.status.toUpperCase()}]
                  </span>
                  <span className="text-matrix-darkgreen">{task.name}</span>
                </div>

                {/* Progress bar */}
                {task.status === 'running' && (
                  <div className="h-1 bg-matrix-dim/30 rounded mb-1">
                    <div
                      className="h-full bg-matrix-green rounded transition-all duration-300"
                      style={{ width: `${task.progress}%` }}
                    />
                  </div>
                )}

                {/* Logs */}
                {task.logs.map((log, i) => (
                  <div key={i} className={`pl-2 ${getLevelColor(log.level)}`}>
                    <span className="text-matrix-dim">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>{' '}
                    {log.message}
                  </div>
                ))}
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      )}
    </div>
  )
}
