import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { subtitlesApi } from '../../api/client'
import { FileItem, SpellCheckIssue } from '../../types/api'
import {
  FileText, Clock, HardDrive, Loader2, CheckCircle, AlertCircle,
  SpellCheck, ChevronDown, ChevronLeft, ChevronRight, Image, Save, X, Stamp, Trash2
} from 'lucide-react'

interface SubtitleInfoProps {
  file: FileItem
  onDeleted?: () => void  // Callback when file is deleted
}

interface SpellCheckOptions {
  replacementsEnabled: boolean
  replacements: string
  ignoreEnabled: boolean
  ignoreList: string
  language: string
}

export function SubtitleInfo({ file, onDeleted }: SubtitleInfoProps) {
  const queryClient = useQueryClient()
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [spellCheckOptions, setSpellCheckOptions] = useState<SpellCheckOptions>({
    replacementsEnabled: true,
    replacements: '|=I,\'=\',/=I,"=","="',
    ignoreEnabled: false,
    ignoreList: '',
    language: 'en',
  })
  const [issues, setIssues] = useState<SpellCheckIssue[]>([])
  const [currentIssueIndex, setCurrentIssueIndex] = useState(0)
  const [invalidCharCount, setInvalidCharCount] = useState(0)
  const [spellingCount, setSpellingCount] = useState(0)
  const [hasPgsSource, setHasPgsSource] = useState(false)
  const [pgsImage, setPgsImage] = useState<string | null>(null)
  const [pgsImageLoading, setPgsImageLoading] = useState(false)
  const [editText, setEditText] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [stampOptions, setStampOptions] = useState({
    startTime: '00:00:05,000',
    endTime: '00:00:15,000',
    text: 'Subtitles by NinjaNymo\nMade with NinjaMediaManager',
  })
  const [stampCollision, setStampCollision] = useState<{
    hasCollision: boolean
    collidingIndices: number[]
    hasStamp: boolean
  } | null>(null)
  const [stampMessage, setStampMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  // PGS preview state for SUP files
  const [pgsPreviewIndex, setPgsPreviewIndex] = useState(0)
  const [pgsPreviewTotal, setPgsPreviewTotal] = useState(0)
  const [pgsPreviewImage, setPgsPreviewImage] = useState<string | null>(null)
  const [pgsPreviewLoading, setPgsPreviewLoading] = useState(false)
  // Track the subtitle index we're editing so we can return to it after spell check refresh
  const editedSubtitleIndexRef = useRef<number | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['subtitleInfo', file.path],
    queryFn: () => subtitlesApi.getInfo(file.path),
  })

  const spellCheckMutation = useMutation({
    mutationFn: () => subtitlesApi.spellCheck(file.path, spellCheckOptions),
    onSuccess: (result) => {
      const newIssues = result.issues || []
      setIssues(newIssues)

      // If we just edited a subtitle, try to find an issue on the same or next subtitle
      if (editedSubtitleIndexRef.current !== null) {
        const editedIndex = editedSubtitleIndexRef.current
        // First try to find an issue on the same subtitle (in case there are more issues)
        let newIssueIndex = newIssues.findIndex(issue => issue.index === editedIndex)
        // If no issue on same subtitle, find the next subtitle with an issue
        if (newIssueIndex === -1) {
          newIssueIndex = newIssues.findIndex(issue => issue.index > editedIndex)
        }
        // If still no issue found, stay at the end or go to 0
        if (newIssueIndex === -1 && newIssues.length > 0) {
          newIssueIndex = Math.min(currentIssueIndex, newIssues.length - 1)
        }
        setCurrentIssueIndex(Math.max(0, newIssueIndex))
        editedSubtitleIndexRef.current = null
      } else {
        setCurrentIssueIndex(0)
      }

      setInvalidCharCount(result.invalid_char_count)
      setSpellingCount(result.spelling_count)
      setHasPgsSource(result.has_pgs_source)
      setPgsImage(null)
      setIsEditing(false)
    },
  })

  const editMutation = useMutation({
    mutationFn: ({ index, newText }: { index: number; newText: string }) =>
      subtitlesApi.editSubtitle(file.path, index, newText),
    onSuccess: (_, variables) => {
      setIsEditing(false)
      // Store the subtitle index we just edited so we can return to it
      editedSubtitleIndexRef.current = variables.index
      // Re-run spell check to refresh issues
      spellCheckMutation.mutate()
      // Invalidate subtitle info to refresh preview
      queryClient.invalidateQueries({ queryKey: ['subtitleInfo', file.path] })
    },
  })

  const checkCollisionMutation = useMutation({
    mutationFn: () => subtitlesApi.checkStampCollision(file.path, stampOptions.startTime, stampOptions.endTime),
    onSuccess: (result) => {
      setStampCollision({
        hasCollision: result.collision,
        collidingIndices: result.colliding_subtitles,
        hasStamp: result.has_stamp,
      })
    },
  })

  const addStampMutation = useMutation({
    mutationFn: () => subtitlesApi.addStamp({
      path: file.path,
      start_time: stampOptions.startTime,
      end_time: stampOptions.endTime,
      text: stampOptions.text,
    }),
    onSuccess: (result) => {
      if (result.success) {
        setStampMessage({ type: 'success', text: result.message })
        setStampCollision({ hasCollision: false, collidingIndices: [], hasStamp: true })
        // Invalidate subtitle info to refresh preview
        queryClient.invalidateQueries({ queryKey: ['subtitleInfo', file.path] })
      } else {
        setStampMessage({ type: 'error', text: result.message })
        if (result.collision) {
          setStampCollision({
            hasCollision: true,
            collidingIndices: result.colliding_subtitles,
            hasStamp: false,
          })
        }
      }
    },
    onError: (error: Error) => {
      setStampMessage({ type: 'error', text: error.message })
    },
  })

  const removeStampMutation = useMutation({
    mutationFn: () => subtitlesApi.removeStamp(file.path),
    onSuccess: (result) => {
      if (result.success) {
        setStampMessage({ type: 'success', text: result.message })
        setStampCollision({ hasCollision: false, collidingIndices: [], hasStamp: false })
        // Invalidate subtitle info to refresh preview
        queryClient.invalidateQueries({ queryKey: ['subtitleInfo', file.path] })
      } else {
        setStampMessage({ type: 'error', text: result.message })
      }
    },
    onError: (error: Error) => {
      setStampMessage({ type: 'error', text: error.message })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => subtitlesApi.deleteSubtitle(file.path),
    onSuccess: (result) => {
      if (result.success) {
        // Invalidate queries and call callback
        queryClient.invalidateQueries({ queryKey: ['outputFiles'] })
        onDeleted?.()
      }
    },
  })

  // Load PGS image when viewing an issue with PGS source
  const loadPgsImage = async (subtitleIndex: number) => {
    if (!hasPgsSource) return
    setPgsImageLoading(true)
    setPgsImage(null)
    try {
      const result = await subtitlesApi.getPgsImage(file.path, subtitleIndex)
      setPgsImage(result.image)
    } catch (err) {
      console.error('Failed to load PGS image:', err)
    } finally {
      setPgsImageLoading(false)
    }
  }

  // Load PGS image when issue changes
  useEffect(() => {
    if (issues.length > 0 && hasPgsSource) {
      const currentIssue = issues[currentIssueIndex]
      if (currentIssue) {
        loadPgsImage(currentIssue.index)
        setEditText(currentIssue.text)
      }
    }
  }, [currentIssueIndex, issues, hasPgsSource])

  // Check stamp collision on initial load for SRT files
  useEffect(() => {
    if (file.name.toLowerCase().endsWith('.srt')) {
      checkCollisionMutation.mutate()
    }
  }, [file.path])

  // Load PGS preview for SUP files
  const loadPgsPreview = async (index: number) => {
    setPgsPreviewLoading(true)
    try {
      const result = await subtitlesApi.getPgsPreview(file.path, index)
      setPgsPreviewImage(result.image)
      setPgsPreviewIndex(result.index)
      setPgsPreviewTotal(result.total_count)
    } catch (err) {
      console.error('Failed to load PGS preview:', err)
      setPgsPreviewImage(null)
    } finally {
      setPgsPreviewLoading(false)
    }
  }

  // Load initial PGS preview for SUP files
  useEffect(() => {
    if (file.name.toLowerCase().endsWith('.sup')) {
      loadPgsPreview(0)
    }
  }, [file.path])

  const handleSaveEdit = () => {
    const currentIssue = issues[currentIssueIndex]
    if (currentIssue && editText !== currentIssue.text) {
      editMutation.mutate({ index: currentIssue.index, newText: editText })
    } else {
      setIsEditing(false)
    }
  }

  const formatSize = (bytes?: number) => {
    if (!bytes) return 'Unknown'
    const kb = bytes / 1024
    if (kb >= 1024) {
      const mb = kb / 1024
      return `${mb.toFixed(1)} MB`
    }
    return `${kb.toFixed(1)} KB`
  }

  const currentIssue = issues[currentIssueIndex]

  // Get highlight length based on issue type
  const getHighlightLength = (issue: SpellCheckIssue) => {
    if (issue.type === 'invalid_character') {
      return 1
    }
    return issue.word?.length || 1
  }

  // Get the highlighted text to display
  const getHighlightedText = (issue: SpellCheckIssue) => {
    if (issue.type === 'invalid_character') {
      return issue.character || '?'
    }
    return issue.word || '?'
  }

  const isSRT = file.name.toLowerCase().endsWith('.srt')
  const isSUP = file.name.toLowerCase().endsWith('.sup')

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-matrix-bg">
        <Loader2 className="w-8 h-8 animate-spin text-matrix-dim" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 bg-matrix-bg">
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-500">
          Error loading subtitle info: {(error as Error).message}
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto p-6 bg-matrix-bg">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold text-matrix-green mb-2">{file.name}</h2>
            <div className="flex items-center gap-4 text-sm text-matrix-dim">
              <span className="flex items-center gap-1">
                <HardDrive className="w-4 h-4" />
                {formatSize(file.size)}
              </span>
              {data?.line_count && (
                <span className="flex items-center gap-1">
                  <FileText className="w-4 h-4" />
                  {data.line_count} subtitles
                </span>
              )}
              {data?.duration && (
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {data.duration}
                </span>
              )}
            </div>
          </div>
          {/* Delete button */}
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="flex items-center gap-1 px-3 py-1.5 bg-red-900/30 hover:bg-red-900/50 border border-red-800 rounded text-sm text-red-400 transition-colors"
            title="Delete file"
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
        </div>
      </div>

      {/* Delete confirmation dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-matrix-bg border border-matrix-dim rounded-lg p-6 max-w-md mx-4">
            <h3 className="text-lg font-semibold text-matrix-green mb-3">Delete File?</h3>
            <p className="text-matrix-darkgreen mb-4">
              Are you sure you want to delete <span className="text-matrix-green font-medium">{file.name}</span>?
              This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 bg-matrix-dim/30 hover:bg-matrix-dim/50 text-matrix-green rounded text-sm transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  deleteMutation.mutate()
                  setShowDeleteConfirm(false)
                }}
                disabled={deleteMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-red-900/50 hover:bg-red-700 border border-red-800 rounded text-sm text-red-300 transition-colors disabled:opacity-50"
              >
                {deleteMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4" />
                )}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Spell Check Section - only for SRT files */}
      {isSRT && (
        <div className="mb-6">
          <h3 className="flex items-center gap-2 text-lg font-medium text-matrix-green mb-3">
            <SpellCheck className="w-5 h-5 text-matrix-glow" />
            Spell Check
          </h3>

          <div className="bg-matrix-bg border border-matrix-dim rounded-lg p-4 space-y-4">
            {/* Options */}
            <div className="space-y-4">
              {/* Replace option */}
              <div className="space-y-2">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={spellCheckOptions.replacementsEnabled}
                    onChange={(e) => setSpellCheckOptions({
                      ...spellCheckOptions,
                      replacementsEnabled: e.target.checked,
                    })}
                    className="w-4 h-4 rounded border-matrix-dim bg-matrix-bg text-matrix-green focus:ring-matrix-green"
                  />
                  <span className="text-sm text-matrix-darkgreen">
                    Replace
                  </span>
                </label>
                {spellCheckOptions.replacementsEnabled && (
                  <input
                    type="text"
                    value={spellCheckOptions.replacements}
                    onChange={(e) => setSpellCheckOptions({
                      ...spellCheckOptions,
                      replacements: e.target.value,
                    })}
                    placeholder="|=I,/=I"
                    className="w-full bg-matrix-bg border border-matrix-dim rounded px-3 py-2 text-sm text-matrix-green font-mono focus:outline-none focus:border-matrix-green"
                  />
                )}
                <div className="text-xs text-matrix-dim">
                  Format: old=new, comma-separated (e.g., |=I,/=I)
                </div>
              </div>

              {/* Ignore option */}
              <div className="space-y-2">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={spellCheckOptions.ignoreEnabled}
                    onChange={(e) => setSpellCheckOptions({
                      ...spellCheckOptions,
                      ignoreEnabled: e.target.checked,
                    })}
                    className="w-4 h-4 rounded border-matrix-dim bg-matrix-bg text-matrix-green focus:ring-matrix-green"
                  />
                  <span className="text-sm text-matrix-darkgreen">
                    Ignore
                  </span>
                </label>
                {spellCheckOptions.ignoreEnabled && (
                  <input
                    type="text"
                    value={spellCheckOptions.ignoreList}
                    onChange={(e) => setSpellCheckOptions({
                      ...spellCheckOptions,
                      ignoreList: e.target.value,
                    })}
                    placeholder="Gandalf,Frodo,™"
                    className="w-full bg-matrix-bg border border-matrix-dim rounded px-3 py-2 text-sm text-matrix-green font-mono focus:outline-none focus:border-matrix-green"
                  />
                )}
                <div className="text-xs text-matrix-dim">
                  Words/characters to skip (comma-separated)
                </div>
              </div>

              <div className="flex items-center gap-3">
                <label className="text-sm text-matrix-darkgreen">Language:</label>
                <div className="relative">
                  <select
                    value={spellCheckOptions.language}
                    onChange={(e) => setSpellCheckOptions({
                      ...spellCheckOptions,
                      language: e.target.value,
                    })}
                    className="appearance-none bg-matrix-bg border border-matrix-dim rounded px-3 py-1.5 pr-8 text-sm text-matrix-green focus:outline-none focus:border-matrix-green"
                  >
                    <option value="en">English</option>
                    <option value="no">Norwegian</option>
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-matrix-dim pointer-events-none" />
                </div>
              </div>
            </div>

            {/* Run button */}
            <button
              onClick={() => spellCheckMutation.mutate()}
              disabled={spellCheckMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-matrix-darkgreen hover:bg-matrix-green hover:text-black rounded text-sm font-medium disabled:opacity-50 text-matrix-green transition-colors"
            >
              {spellCheckMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <SpellCheck className="w-4 h-4" />
              )}
              Run Spell Check
            </button>

            {/* Results */}
            {spellCheckMutation.isSuccess && (
              <div className="mt-4">
                {spellCheckMutation.data.replacements_made > 0 && (
                  <div className="flex items-center gap-2 text-matrix-glow mb-3">
                    <CheckCircle className="w-5 h-5" />
                    <span>Made {spellCheckMutation.data.replacements_made} character replacement{spellCheckMutation.data.replacements_made > 1 ? 's' : ''}</span>
                  </div>
                )}
                {issues.length === 0 ? (
                  <div className="flex items-center gap-2 text-matrix-green">
                    <CheckCircle className="w-5 h-5" />
                    <span>No issues found!</span>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center gap-4 text-yellow-500">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="w-5 h-5" />
                        <span>{issues.length} issue{issues.length > 1 ? 's' : ''} found</span>
                      </div>
                      <div className="text-sm text-matrix-dim">
                        ({invalidCharCount} invalid char{invalidCharCount !== 1 ? 's' : ''}, {spellingCount} spelling)
                      </div>
                    </div>

                    {/* Issue navigation */}
                    <div className="bg-matrix-bg border border-matrix-dim rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <span className="text-sm text-matrix-dim">
                            Issue {currentIssueIndex + 1} of {issues.length}
                          </span>
                          {currentIssue && (
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              currentIssue.type === 'invalid_character'
                                ? 'bg-red-500/20 text-red-400'
                                : 'bg-yellow-500/20 text-yellow-400'
                            }`}>
                              {currentIssue.type === 'invalid_character' ? 'Invalid Char' : 'Spelling'}
                            </span>
                          )}
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => setCurrentIssueIndex(Math.max(0, currentIssueIndex - 1))}
                            disabled={currentIssueIndex === 0}
                            className="px-3 py-1 bg-matrix-dim/30 hover:bg-matrix-dim/50 text-matrix-green rounded text-sm disabled:opacity-50"
                          >
                            Previous
                          </button>
                          <button
                            onClick={() => setCurrentIssueIndex(Math.min(issues.length - 1, currentIssueIndex + 1))}
                            disabled={currentIssueIndex === issues.length - 1}
                            className="px-3 py-1 bg-matrix-dim/30 hover:bg-matrix-dim/50 text-matrix-green rounded text-sm disabled:opacity-50"
                          >
                            Next
                          </button>
                        </div>
                      </div>

                      {currentIssue && (
                        <div className="space-y-3">
                          <div className="text-sm">
                            <span className="text-matrix-dim">Subtitle #{currentIssue.index}:</span>
                          </div>

                          {/* PGS Image Preview */}
                          {hasPgsSource && (
                            <div className="bg-matrix-bg border border-matrix-dim/50 rounded p-3">
                              <div className="flex items-center gap-2 text-xs text-matrix-dim mb-2">
                                <Image className="w-3 h-3" />
                                Original PGS Image
                              </div>
                              {pgsImageLoading ? (
                                <div className="flex items-center justify-center py-4">
                                  <Loader2 className="w-5 h-5 animate-spin text-matrix-dim" />
                                </div>
                              ) : pgsImage ? (
                                <img
                                  src={`data:image/bmp;base64,${pgsImage}`}
                                  alt={`Subtitle ${currentIssue.index}`}
                                  className="max-w-full rounded border border-matrix-dim bg-matrix-bg"
                                />
                              ) : (
                                <div className="text-xs text-matrix-dim py-2">
                                  No image available
                                </div>
                              )}
                            </div>
                          )}

                          {/* OCR Result / Edit */}
                          <div className="bg-matrix-bg border border-matrix-dim/50 rounded p-3">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs text-matrix-dim">OCR Result</span>
                              {!isEditing && (
                                <button
                                  onClick={() => {
                                    setEditText(currentIssue.text)
                                    setIsEditing(true)
                                  }}
                                  className="text-xs text-matrix-green hover:text-matrix-glow"
                                >
                                  Edit
                                </button>
                              )}
                            </div>
                            {isEditing ? (
                              <div className="space-y-2">
                                <textarea
                                  value={editText}
                                  onChange={(e) => setEditText(e.target.value)}
                                  className="w-full bg-matrix-bg border border-matrix-dim rounded p-2 font-mono text-sm text-matrix-green focus:outline-none focus:border-matrix-green"
                                  rows={3}
                                />
                                <div className="flex gap-2">
                                  <button
                                    onClick={handleSaveEdit}
                                    disabled={editMutation.isPending}
                                    className="flex items-center gap-1 px-3 py-1 bg-matrix-darkgreen hover:bg-matrix-green hover:text-black rounded text-xs font-medium disabled:opacity-50 text-matrix-green transition-colors"
                                  >
                                    {editMutation.isPending ? (
                                      <Loader2 className="w-3 h-3 animate-spin" />
                                    ) : (
                                      <Save className="w-3 h-3" />
                                    )}
                                    Save
                                  </button>
                                  <button
                                    onClick={() => setIsEditing(false)}
                                    className="flex items-center gap-1 px-3 py-1 bg-matrix-dim/30 hover:bg-matrix-dim/50 text-matrix-green rounded text-xs"
                                  >
                                    <X className="w-3 h-3" />
                                    Cancel
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <div className="font-mono text-sm">
                                <span className="text-matrix-darkgreen">
                                  {currentIssue.text.substring(0, currentIssue.position)}
                                </span>
                                <span className={`px-0.5 ${
                                  currentIssue.type === 'invalid_character'
                                    ? 'bg-red-500/30 text-red-300'
                                    : 'bg-yellow-500/30 text-yellow-300'
                                }`}>
                                  {getHighlightedText(currentIssue)}
                                </span>
                                <span className="text-matrix-darkgreen">
                                  {currentIssue.text.substring(currentIssue.position + getHighlightLength(currentIssue))}
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Issue details */}
                          {currentIssue.type === 'invalid_character' ? (
                            <div className="text-xs text-matrix-dim">
                              Invalid character: "{currentIssue.character}" (position {currentIssue.position})
                            </div>
                          ) : (
                            <>
                              <div className="text-sm">
                                <span className="text-matrix-dim">Suggestions: </span>
                                {currentIssue.suggestions.length > 0 ? (
                                  <span className="text-matrix-glow">
                                    {currentIssue.suggestions.join(', ')}
                                  </span>
                                ) : (
                                  <span className="text-matrix-dim italic">No suggestions available</span>
                                )}
                              </div>

                              {/* Quick fix buttons for spelling issues */}
                              {currentIssue.suggestions.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                  {currentIssue.suggestions.map((suggestion, i) => (
                                    <button
                                      key={i}
                                      onClick={() => {
                                        const newText = currentIssue.text.substring(0, currentIssue.position) +
                                          suggestion +
                                          currentIssue.text.substring(currentIssue.position + (currentIssue.word?.length || 0))
                                        editMutation.mutate({ index: currentIssue.index, newText })
                                      }}
                                      disabled={editMutation.isPending}
                                      className="px-3 py-1 bg-matrix-darkgreen hover:bg-matrix-green hover:text-black text-matrix-green rounded text-xs font-medium disabled:opacity-50 transition-colors"
                                    >
                                      Replace with "{suggestion}"
                                    </button>
                                  ))}
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Creator Stamp Section - only for SRT files */}
      {isSRT && (
        <div className="mb-6">
          <h3 className="flex items-center gap-2 text-lg font-medium text-matrix-green mb-3">
            <Stamp className="w-5 h-5 text-matrix-glow" />
            Creator Stamp
          </h3>

          <div className="bg-matrix-bg border border-matrix-dim rounded-lg p-4 space-y-4">
            {/* Check if stamp already exists */}
            {stampCollision?.hasStamp ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-matrix-glow">
                  <CheckCircle className="w-5 h-5" />
                  <span>Creator stamp already exists in this file</span>
                </div>

                {/* Status message */}
                {stampMessage && (
                  <div
                    className={`flex items-start gap-2 p-3 rounded-lg ${
                      stampMessage.type === 'success'
                        ? 'bg-matrix-dim/20 border border-matrix-darkgreen text-matrix-green'
                        : 'bg-red-900/20 border border-red-800 text-red-500'
                    }`}
                  >
                    {stampMessage.type === 'success' ? (
                      <CheckCircle className="w-5 h-5 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    )}
                    <span className="text-sm">{stampMessage.text}</span>
                  </div>
                )}

                {/* Remove stamp button */}
                <button
                  onClick={() => {
                    setStampMessage(null)
                    removeStampMutation.mutate()
                  }}
                  disabled={removeStampMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-red-900/30 hover:bg-red-900/50 border border-red-800 rounded text-sm font-medium disabled:opacity-50 text-red-400 transition-colors"
                >
                  {removeStampMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                  Remove Creator Stamp
                </button>
              </div>
            ) : (
              <>
                {/* Time inputs */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-matrix-darkgreen mb-1">Start Time</label>
                    <input
                      type="text"
                      value={stampOptions.startTime}
                      onChange={(e) => {
                        setStampOptions({ ...stampOptions, startTime: e.target.value })
                        setStampMessage(null)
                      }}
                      onBlur={() => checkCollisionMutation.mutate()}
                      placeholder="00:00:05,000"
                      className="w-full bg-matrix-bg border border-matrix-dim rounded px-3 py-2 text-sm text-matrix-green font-mono focus:outline-none focus:border-matrix-green"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-matrix-darkgreen mb-1">End Time</label>
                    <input
                      type="text"
                      value={stampOptions.endTime}
                      onChange={(e) => {
                        setStampOptions({ ...stampOptions, endTime: e.target.value })
                        setStampMessage(null)
                      }}
                      onBlur={() => checkCollisionMutation.mutate()}
                      placeholder="00:00:15,000"
                      className="w-full bg-matrix-bg border border-matrix-dim rounded px-3 py-2 text-sm text-matrix-green font-mono focus:outline-none focus:border-matrix-green"
                    />
                  </div>
                </div>

                {/* Stamp text */}
                <div>
                  <label className="block text-sm text-matrix-darkgreen mb-1">Stamp Text</label>
                  <textarea
                    value={stampOptions.text}
                    onChange={(e) => {
                      setStampOptions({ ...stampOptions, text: e.target.value })
                      setStampMessage(null)
                    }}
                    placeholder="Subtitles by..."
                    rows={3}
                    className="w-full bg-matrix-bg border border-matrix-dim rounded px-3 py-2 text-sm text-matrix-green focus:outline-none focus:border-matrix-green resize-none"
                  />
                </div>

                {/* Collision warning */}
                {stampCollision?.hasCollision && (
                  <div className="flex items-start gap-2 text-yellow-500 bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
                    <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <div className="text-sm">
                      <div className="font-medium">Cannot add stamp</div>
                      <div className="text-yellow-400">
                        Conflicts with existing subtitle(s): #{stampCollision.collidingIndices.join(', #')}
                      </div>
                    </div>
                  </div>
                )}

                {/* Status message */}
                {stampMessage && (
                  <div
                    className={`flex items-start gap-2 p-3 rounded-lg ${
                      stampMessage.type === 'success'
                        ? 'bg-matrix-dim/20 border border-matrix-darkgreen text-matrix-green'
                        : 'bg-red-900/20 border border-red-800 text-red-500'
                    }`}
                  >
                    {stampMessage.type === 'success' ? (
                      <CheckCircle className="w-5 h-5 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    )}
                    <span className="text-sm">{stampMessage.text}</span>
                  </div>
                )}

                {/* Add Stamp button */}
                <button
                  onClick={() => {
                    setStampMessage(null)
                    addStampMutation.mutate()
                  }}
                  disabled={addStampMutation.isPending || stampCollision?.hasCollision || !stampOptions.text.trim()}
                  className="flex items-center gap-2 px-4 py-2 bg-matrix-darkgreen hover:bg-matrix-green hover:text-black rounded text-sm font-medium disabled:opacity-50 text-matrix-green transition-colors"
                >
                  {addStampMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Stamp className="w-4 h-4" />
                  )}
                  Add Creator Stamp
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Preview section - Text preview for non-SUP files */}
      {data?.preview && !isSUP && (
        <div className="mb-6">
          <h3 className="text-lg font-medium text-matrix-green mb-3">Preview</h3>
          <div className="bg-matrix-bg border border-matrix-dim rounded-lg p-4 font-mono text-sm text-matrix-darkgreen whitespace-pre-wrap max-h-96 overflow-auto">
            {data.preview}
          </div>
        </div>
      )}

      {/* PGS Preview section - for SUP files */}
      {isSUP && (
        <div className="mb-6">
          <h3 className="flex items-center gap-2 text-lg font-medium text-matrix-green mb-3">
            <Image className="w-5 h-5 text-matrix-glow" />
            PGS Preview
          </h3>

          <div className="bg-matrix-bg border border-matrix-dim rounded-lg p-4 space-y-4">
            {/* Navigation */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => loadPgsPreview(pgsPreviewIndex - 1)}
                disabled={pgsPreviewLoading || pgsPreviewIndex <= 0}
                className="flex items-center gap-1 px-3 py-2 bg-matrix-dim/30 hover:bg-matrix-dim/50 text-matrix-green rounded text-sm disabled:opacity-50 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>

              <div className="text-sm text-matrix-dim">
                {pgsPreviewImage ? (
                  <span>Subtitle {pgsPreviewIndex + 1}{pgsPreviewTotal > pgsPreviewIndex + 1 ? '+' : ''}</span>
                ) : pgsPreviewLoading ? (
                  <span>Loading...</span>
                ) : (
                  <span>No subtitles</span>
                )}
              </div>

              <button
                onClick={() => loadPgsPreview(pgsPreviewIndex + 1)}
                disabled={pgsPreviewLoading || pgsPreviewIndex >= pgsPreviewTotal - 1}
                className="flex items-center gap-1 px-3 py-2 bg-matrix-dim/30 hover:bg-matrix-dim/50 text-matrix-green rounded text-sm disabled:opacity-50 transition-colors"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* Image display */}
            <div className="flex items-center justify-center min-h-32 bg-black/30 rounded-lg p-4">
              {pgsPreviewLoading ? (
                <div className="flex flex-col items-center gap-2">
                  <Loader2 className="w-8 h-8 animate-spin text-matrix-dim" />
                  <span className="text-sm text-matrix-dim">Loading subtitle image...</span>
                </div>
              ) : pgsPreviewImage ? (
                <img
                  src={`data:image/bmp;base64,${pgsPreviewImage}`}
                  alt={`Subtitle ${pgsPreviewIndex + 1}`}
                  className="max-w-full rounded border border-matrix-dim"
                />
              ) : (
                <div className="text-sm text-matrix-dim">
                  No image available
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
