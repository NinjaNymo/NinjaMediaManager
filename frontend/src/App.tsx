import { useState } from 'react'
import { FileBrowser, BrowserTab } from './components/FileBrowser/FileBrowser'
import { MediaInfo } from './components/MediaInfo/MediaInfo'
import { SubtitleInfo } from './components/SubtitleInfo/SubtitleInfo'
import { LogPanel } from './components/LogPanel/LogPanel'
import { FileItem } from './types/api'
import { Film, FileText } from 'lucide-react'

function App() {
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null)
  const [activeTab, setActiveTab] = useState<BrowserTab>('input')
  const [isLogPanelOpen, setIsLogPanelOpen] = useState(true)

  return (
    <div className="min-h-screen bg-matrix-bg flex flex-col font-mono">
      {/* Header */}
      <header className="bg-matrix-bg border-b border-matrix-dim px-6 py-4">
        <div className="flex items-center gap-3">
          <Film className="w-8 h-8 text-matrix-green" />
          <h1 className="text-xl font-bold text-matrix-green">NinjaMediaManager</h1>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex">
        {/* File browser panel */}
        <div className="w-1/3 min-w-[300px] max-w-[500px] border-r border-matrix-dim overflow-hidden flex flex-col">
          <FileBrowser
            onFileSelect={setSelectedFile}
            selectedFile={selectedFile}
            onTabChange={setActiveTab}
          />
        </div>

        {/* Info panel - shows MediaInfo or SubtitleInfo based on active tab */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'input' ? (
            // Input tab - show media info
            selectedFile ? (
              <MediaInfo file={selectedFile} />
            ) : (
              <div className="h-full flex items-center justify-center text-matrix-dim">
                <div className="text-center">
                  <Film className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>Select a media file to view details</p>
                </div>
              </div>
            )
          ) : (
            // Output tab - show subtitle info
            selectedFile ? (
              <SubtitleInfo file={selectedFile} onDeleted={() => setSelectedFile(null)} />
            ) : (
              <div className="h-full flex items-center justify-center text-matrix-dim">
                <div className="text-center">
                  <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>Select a subtitle file to view details</p>
                </div>
              </div>
            )
          )}
        </div>
      </main>

      {/* Log Panel */}
      <LogPanel
        isOpen={isLogPanelOpen}
        onToggle={() => setIsLogPanelOpen(!isLogPanelOpen)}
      />
    </div>
  )
}

export default App
