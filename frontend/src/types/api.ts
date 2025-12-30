// API response types

export type FileType = 'directory' | 'mkv' | 'other'

export interface FileItem {
  name: string
  path: string
  type: FileType
  size?: number
  modified?: string
}

export interface BrowseResponse {
  path: string
  parent: string | null
  items: FileItem[]
}

export type TrackType = 'video' | 'audio' | 'subtitle'

export interface Track {
  index: number
  type: TrackType
  codec: string
  language?: string
  title?: string
  default: boolean
  forced: boolean
  // Video specific
  width?: number
  height?: number
  frame_rate?: number
  // Video/Audio
  bitrate?: number
  // Audio specific
  channels?: number
  sample_rate?: number
}

export interface MediaInfoResponse {
  path: string
  filename: string
  size: number
  duration?: number
  format: string
  tracks: Track[]
}

export interface ExtractRequest {
  media_path: string
  track_index: number
  output_format?: string
}

export interface ExtractResponse {
  success: boolean
  output_path?: string
  message: string
}

export interface OCRRequest {
  media_path: string
  track_index: number
  language?: string
}

export interface OCRResponse {
  success: boolean
  output_path?: string
  message: string
  subtitle_count?: number
}

export interface HealthResponse {
  status: string
  version: string
  media_path: string
  output_path: string
}

export interface SubtitleInfoResponse {
  path: string
  filename: string
  size: number
  line_count: number
  duration?: string
  preview?: string
}

export type IssueType = 'invalid_character' | 'spelling'

export interface SpellCheckIssue {
  type: IssueType
  index: number
  text: string
  position: number
  // For invalid character issues
  character?: string
  // For spelling issues
  word?: string
  suggestions: string[]
}

export interface SpellCheckRequest {
  path: string
  replacements_enabled: boolean
  replacements: string  // Format: "key=value,key=value" e.g., "|=I,'=',/=I"
  ignore_enabled: boolean
  ignore_list: string  // Comma-separated words/characters to ignore
  language: string
}

export interface SpellCheckResponse {
  path: string
  replacements_made: number
  issues: SpellCheckIssue[]
  invalid_char_count: number
  spelling_count: number
  has_pgs_source: boolean
}

export interface PgsImageResponse {
  index: number
  image: string  // Base64-encoded BMP image
}

export interface PgsPreviewResponse {
  index: number
  total_count: number
  image: string  // Base64-encoded BMP image
}

export interface SubtitleEditRequest {
  path: string
  index: number
  new_text: string
}

export interface SubtitleEditResponse {
  success: boolean
  message: string
}

export interface AddStampRequest {
  path: string
  start_time: string  // "HH:MM:SS,mmm" format
  end_time: string
  text: string
}

export interface AddStampResponse {
  success: boolean
  message: string
  collision: boolean
  colliding_subtitles: number[]
}

export interface RemoveStampResponse {
  success: boolean
  message: string
}

export interface CheckStampCollisionResponse {
  collision: boolean
  colliding_subtitles: number[]
  has_stamp: boolean
}

export interface DeleteSubtitleResponse {
  success: boolean
  message: string
}

export type SDHFormat = 'brackets'

export interface SDHRemovalRequest {
  path: string
  sdh_format: SDHFormat
  remove_dangling_dashes: boolean
}

export interface SDHRemovalResponse {
  success: boolean
  message: string
  entries_removed: number
  entries_modified: number
  total_removals: number
}
