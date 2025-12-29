import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { filesApi } from '../../api/client'
import { FileItem } from '../../types/api'
import { Folder, Film, FileText, ChevronRight, ArrowUp, RefreshCw, Loader2 } from 'lucide-react'

export type BrowserTab = 'input' | 'output'

interface FileBrowserProps {
  onFileSelect: (file: FileItem | null) => void
  selectedFile: FileItem | null
  onTabChange?: (tab: BrowserTab) => void
}

export function FileBrowser({ onFileSelect, selectedFile, onTabChange }: FileBrowserProps) {
  const [activeTab, setActiveTab] = useState<BrowserTab>('input')
  const [inputPath, setInputPath] = useState('')
  const [outputPath, setOutputPath] = useState('')

  const currentPath = activeTab === 'input' ? inputPath : outputPath
  const setCurrentPath = activeTab === 'input' ? setInputPath : setOutputPath

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [activeTab === 'input' ? 'files' : 'outputFiles', currentPath],
    queryFn: () => activeTab === 'input'
      ? filesApi.browse(currentPath)
      : filesApi.browseOutput(currentPath),
  })

  const handleTabChange = (tab: BrowserTab) => {
    setActiveTab(tab)
    onFileSelect(null)
    onTabChange?.(tab)
  }

  const handleItemClick = (item: FileItem) => {
    if (item.type === 'directory') {
      setCurrentPath(item.path)
      onFileSelect(null)
    } else {
      onFileSelect(item)
    }
  }

  const handleGoUp = () => {
    if (data?.parent !== null && data?.parent !== undefined) {
      setCurrentPath(data.parent)
      onFileSelect(null)
    }
  }

  const formatSize = (bytes?: number) => {
    if (!bytes) return ''
    const gb = bytes / (1024 * 1024 * 1024)
    if (gb >= 1) return `${gb.toFixed(1)} GB`
    const mb = bytes / (1024 * 1024)
    if (mb >= 1) return `${mb.toFixed(1)} MB`
    const kb = bytes / 1024
    return `${kb.toFixed(0)} KB`
  }

  const getFileIcon = (item: FileItem) => {
    if (item.type === 'directory') {
      return <Folder className="w-5 h-5 text-matrix-darkgreen flex-shrink-0" />
    }
    if (item.type === 'mkv') {
      return <Film className="w-5 h-5 text-matrix-green flex-shrink-0" />
    }
    // Subtitle files
    return <FileText className="w-5 h-5 text-matrix-glow flex-shrink-0" />
  }

  return (
    <div className="flex flex-col h-full bg-matrix-bg">
      {/* Tabs */}
      <div className="flex border-b border-matrix-dim">
        <button
          onClick={() => handleTabChange('input')}
          className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'input'
              ? 'text-matrix-green border-b-2 border-matrix-green bg-matrix-bg'
              : 'text-matrix-dim hover:text-matrix-darkgreen hover:bg-matrix-dim/20'
          }`}
        >
          Input
        </button>
        <button
          onClick={() => handleTabChange('output')}
          className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'output'
              ? 'text-matrix-green border-b-2 border-matrix-green bg-matrix-bg'
              : 'text-matrix-dim hover:text-matrix-darkgreen hover:bg-matrix-dim/20'
          }`}
        >
          Output
        </button>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 p-3 bg-matrix-bg border-b border-matrix-dim">
        <button
          onClick={handleGoUp}
          disabled={data?.parent === null || data?.parent === undefined}
          className="p-2 rounded hover:bg-matrix-dim/30 text-matrix-green disabled:opacity-50 disabled:cursor-not-allowed"
          title="Go up"
        >
          <ArrowUp className="w-4 h-4" />
        </button>
        <div className="flex-1 px-3 py-1.5 bg-matrix-bg border border-matrix-dim rounded text-sm text-matrix-darkgreen truncate">
          /{currentPath || ''}
        </div>
        <button
          onClick={() => refetch()}
          className="p-2 rounded hover:bg-matrix-dim/30 text-matrix-green"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* File list */}
      <div className="flex-1 overflow-auto bg-matrix-bg">
        {isLoading && (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 animate-spin text-matrix-dim" />
          </div>
        )}

        {error && (
          <div className="p-4 text-red-500 text-sm">
            Error: {error.message}
          </div>
        )}

        {data && data.items.length === 0 && (
          <div className="p-4 text-matrix-dim text-sm text-center">
            {activeTab === 'input' ? 'No media files found' : 'No output files yet'}
          </div>
        )}

        {data && data.items.map((item) => (
          <div
            key={item.path}
            onClick={() => handleItemClick(item)}
            className={`
              flex items-start gap-3 px-4 py-2.5 cursor-pointer
              hover:bg-matrix-dim/20 border-b border-matrix-dim/50
              ${selectedFile?.path === item.path ? 'bg-matrix-dim/30 border-l-2 border-l-matrix-green' : ''}
            `}
          >
            <div className="pt-0.5">
              {getFileIcon(item)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="text-sm text-matrix-green break-all">{item.name}</div>
              {item.size && (
                <div className="text-xs text-matrix-dim">{formatSize(item.size)}</div>
              )}
            </div>

            {item.type === 'directory' && (
              <ChevronRight className="w-4 h-4 text-matrix-dim" />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
