import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { mediaApi, subtitlesApi } from '../../api/client'
import { FileItem, Track } from '../../types/api'
import {
  Film, Music, Subtitles, Clock, HardDrive,
  Download, Wand2, Loader2, CheckCircle, AlertCircle
} from 'lucide-react'

interface MediaInfoProps {
  file: FileItem
}

export function MediaInfo({ file }: MediaInfoProps) {
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['mediaInfo', file.path],
    queryFn: () => mediaApi.getInfo(file.path),
  })

  const extractMutation = useMutation({
    mutationFn: subtitlesApi.extract,
    onSuccess: (data) => {
      setMessage({ type: 'success', text: `Extracted: ${data.output_path}` })
    },
    onError: (error: Error) => {
      setMessage({ type: 'error', text: error.message })
    },
  })

  const ocrMutation = useMutation({
    mutationFn: subtitlesApi.ocr,
    onSuccess: (data) => {
      setMessage({
        type: 'success',
        text: `OCR completed: ${data.subtitle_count} subtitles → ${data.output_path}`,
      })
    },
    onError: (error: Error) => {
      setMessage({ type: 'error', text: error.message })
    },
  })

  const handleExtract = (track: Track) => {
    setMessage(null)
    extractMutation.mutate({
      media_path: file.path,
      track_index: track.index,
    })
  }

  const handleOCR = (track: Track) => {
    setMessage(null)
    ocrMutation.mutate({
      media_path: file.path,
      track_index: track.index,
      language: track.language === 'nor' ? 'nor' : 'eng',
    })
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'Unknown'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = Math.floor(seconds % 60)
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  const formatSize = (bytes: number) => {
    const gb = bytes / (1024 * 1024 * 1024)
    if (gb >= 1) return `${gb.toFixed(2)} GB`
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(0)} MB`
  }

  const formatBitrate = (bitsPerSecond?: number) => {
    if (!bitsPerSecond) return null
    const mbps = bitsPerSecond / 1_000_000
    if (mbps >= 1) return `${mbps.toFixed(1)} Mbps`
    const kbps = bitsPerSecond / 1_000
    return `${kbps.toFixed(0)} kbps`
  }

  const getCodecLabel = (codec: string) => {
    const labels: Record<string, string> = {
      'hevc': 'HEVC/H.265',
      'h264': 'H.264',
      'avc': 'H.264',
      'subrip': 'SRT',
      'ass': 'ASS',
      'hdmv_pgs_subtitle': 'PGS',
      'dvd_subtitle': 'VobSub',
      'aac': 'AAC',
      'ac3': 'AC3',
      'eac3': 'E-AC3',
      'dts': 'DTS',
      'truehd': 'TrueHD',
    }
    return labels[codec.toLowerCase()] || codec.toUpperCase()
  }

  const isPGS = (track: Track) => track.codec === 'hdmv_pgs_subtitle'

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
          Error loading media info: {error.message}
        </div>
      </div>
    )
  }

  if (!data) return null

  const videoTracks = data.tracks.filter((t) => t.type === 'video')
  const audioTracks = data.tracks.filter((t) => t.type === 'audio')
  const subtitleTracks = data.tracks.filter((t) => t.type === 'subtitle')

  return (
    <div className="h-full overflow-auto p-6 bg-matrix-bg">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-matrix-green mb-2">{data.filename}</h2>
        <div className="flex items-center gap-4 text-sm text-matrix-dim">
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            {formatDuration(data.duration)}
          </span>
          <span className="flex items-center gap-1">
            <HardDrive className="w-4 h-4" />
            {formatSize(data.size)}
          </span>
        </div>
      </div>

      {/* Status message */}
      {message && (
        <div
          className={`mb-6 p-4 rounded-lg flex items-start gap-3 ${
            message.type === 'success'
              ? 'bg-matrix-dim/20 border border-matrix-darkgreen text-matrix-green'
              : 'bg-red-900/20 border border-red-800 text-red-500'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* Video tracks */}
      {videoTracks.length > 0 && (
        <div className="mb-6">
          <h3 className="flex items-center gap-2 text-lg font-medium text-matrix-green mb-3">
            <Film className="w-5 h-5 text-matrix-glow" />
            Video
          </h3>
          <div className="space-y-2">
            {videoTracks.map((track) => (
              <div
                key={track.index}
                className="bg-matrix-bg border border-matrix-dim rounded-lg p-3 flex items-center gap-4"
              >
                <span className="text-sm text-matrix-dim">#{track.index}</span>
                <span className="font-medium text-matrix-green">{getCodecLabel(track.codec)}</span>
                {track.width && track.height && (
                  <span className="text-sm text-matrix-dim">
                    {track.width}x{track.height}
                  </span>
                )}
                {track.frame_rate && (
                  <span className="text-sm text-matrix-dim">
                    {track.frame_rate} fps
                  </span>
                )}
                {formatBitrate(track.bitrate) && (
                  <span className="text-sm text-matrix-dim">
                    {formatBitrate(track.bitrate)}
                  </span>
                )}
                {track.title && (
                  <span className="text-sm text-matrix-darkgreen">{track.title}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Audio tracks */}
      {audioTracks.length > 0 && (
        <div className="mb-6">
          <h3 className="flex items-center gap-2 text-lg font-medium text-matrix-green mb-3">
            <Music className="w-5 h-5 text-matrix-glow" />
            Audio
          </h3>
          <div className="space-y-2">
            {audioTracks.map((track) => (
              <div
                key={track.index}
                className="bg-matrix-bg border border-matrix-dim rounded-lg p-3 flex items-center gap-4"
              >
                <span className="text-sm text-matrix-dim">#{track.index}</span>
                <span className="font-medium text-matrix-green">{getCodecLabel(track.codec)}</span>
                {track.language && (
                  <span className="px-2 py-0.5 bg-matrix-dim/30 text-matrix-darkgreen rounded text-xs uppercase">
                    {track.language}
                  </span>
                )}
                {track.channels && (
                  <span className="text-sm text-matrix-dim">
                    {track.channels === 6 ? '5.1' : track.channels === 8 ? '7.1' : `${track.channels}ch`}
                  </span>
                )}
                {formatBitrate(track.bitrate) && (
                  <span className="text-sm text-matrix-dim">
                    {formatBitrate(track.bitrate)}
                  </span>
                )}
                {track.title && (
                  <span className="text-sm text-matrix-darkgreen">{track.title}</span>
                )}
                {track.default && (
                  <span className="px-2 py-0.5 bg-matrix-dim/50 text-matrix-green rounded text-xs">
                    Default
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Subtitle tracks */}
      {subtitleTracks.length > 0 && (
        <div className="mb-6">
          <h3 className="flex items-center gap-2 text-lg font-medium text-matrix-green mb-3">
            <Subtitles className="w-5 h-5 text-matrix-glow" />
            Subtitles
          </h3>
          <div className="space-y-2">
            {subtitleTracks.map((track) => (
              <div
                key={track.index}
                className="bg-matrix-bg border border-matrix-dim rounded-lg p-3 flex items-center gap-4"
              >
                <span className="text-sm text-matrix-dim">#{track.index}</span>
                <span
                  className={`font-medium ${
                    isPGS(track) ? 'text-yellow-500' : 'text-matrix-green'
                  }`}
                >
                  {getCodecLabel(track.codec)}
                </span>
                {track.language && (
                  <span className="px-2 py-0.5 bg-matrix-dim/30 text-matrix-darkgreen rounded text-xs uppercase">
                    {track.language}
                  </span>
                )}
                {track.title && (
                  <span className="text-sm text-matrix-darkgreen flex-1">{track.title}</span>
                )}
                {track.forced && (
                  <span className="px-2 py-0.5 bg-purple-900/50 text-purple-400 rounded text-xs">
                    Forced
                  </span>
                )}
                {track.default && (
                  <span className="px-2 py-0.5 bg-matrix-dim/50 text-matrix-green rounded text-xs">
                    Default
                  </span>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2 ml-auto">
                  <button
                    onClick={() => handleExtract(track)}
                    disabled={extractMutation.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-matrix-dim/30 hover:bg-matrix-dim/50 text-matrix-green rounded text-sm disabled:opacity-50"
                    title="Extract subtitle"
                  >
                    {extractMutation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Download className="w-4 h-4" />
                    )}
                    Extract
                  </button>

                  {isPGS(track) && (
                    <button
                      onClick={() => handleOCR(track)}
                      disabled={ocrMutation.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-matrix-darkgreen hover:bg-matrix-green hover:text-black text-matrix-green rounded text-sm disabled:opacity-50 transition-colors"
                      title="OCR to SRT"
                    >
                      {ocrMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Wand2 className="w-4 h-4" />
                      )}
                      OCR to SRT
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
