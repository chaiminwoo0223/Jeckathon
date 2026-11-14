// CHEER 101 — mock data layer (명세 2장 데이터 모델 기반)
// 백엔드 연동 전 UI 전용. 실제 API 붙이면 이 파일만 교체하면 됨.

export type MatchResult = "PENDING" | "WIN" | "DRAW" | "LOSE"
export type FairyType = "VICTORY" | "DEFEAT" | "NEUTRAL"

export interface Team {
  id: number
  name: string
  short: string // 로고 대체 약어
  color: string // 팀 컬러
  league: string
}

export interface Match {
  id: number
  home: Team
  away: Team
  league: string
  kickoffAt: string // ISO
  status: "SCHEDULED" | "LIVE" | "FINISHED"
  homeScore?: number
  awayScore?: number
}

export interface CheerRecord {
  id: number
  match: Match
  cheeredTeamId: number
  result: MatchResult
  pointsEarned: number
}

export interface Badge {
  code: string
  name: string
  desc: string
  emoji: string
  acquired: boolean
}

export interface RankingEntry {
  rank: number
  nickname: string
  rate: number // 승률 or 패배율 (0~1)
  played: number
  wins: number
  emoji: string
}

export interface BattlePlayer {
  userId: number
  nickname: string
  peakDb: number
  emoji: string
  me?: boolean
}

export interface Fortune {
  teamId: number
  fortuneText: string
  cheerTip: string
  luckScore: number
}

// ---------- Teams ----------
export const TEAMS: Record<string, Team> = {
  arsenal: { id: 3, name: "아스널", short: "ARS", color: "#ef3340", league: "프리미어리그" },
  tottenham: { id: 4, name: "토트넘", short: "TOT", color: "#132257", league: "프리미어리그" },
  mancity: { id: 5, name: "맨시티", short: "MCI", color: "#6cabdd", league: "프리미어리그" },
  liverpool: { id: 6, name: "리버풀", short: "LIV", color: "#c8102e", league: "프리미어리그" },
  chelsea: { id: 7, name: "첼시", short: "CHE", color: "#034694", league: "프리미어리그" },
  realmadrid: { id: 8, name: "레알 마드리드", short: "RMA", color: "#1d3a8a", league: "라리가" },
  barcelona: { id: 9, name: "바르셀로나", short: "BAR", color: "#a50044", league: "라리가" },
}

export const ALL_TEAMS = Object.values(TEAMS)

// ---------- Current user ----------
export const ME = {
  id: 1,
  nickname: "뚜비응원단",
  bio: "아스널이 이기는 날이 제일 행복해요 💜",
  level: 12,
  levelTitle: "열정 응원러",
  totalPoints: 3820,
  teams: [TEAMS.arsenal, TEAMS.tottenham],
  favoriteTeam: TEAMS.arsenal,
  style: [
    { label: "열혈팬", value: 92, emoji: "🔥" },
    { label: "분석왕", value: 64, emoji: "📊" },
    { label: "데시벨러", value: 87, emoji: "📢" },
  ],
}

// ---------- Matches ----------
const d = (iso: string) => iso
export const TODAY = "2026-11-14"

export const MATCHES: Match[] = [
  {
    id: 100,
    home: TEAMS.tottenham,
    away: TEAMS.arsenal,
    league: "프리미어리그",
    kickoffAt: d("2026-11-14T20:30:00"),
    status: "SCHEDULED",
  },
  {
    id: 101,
    home: TEAMS.realmadrid,
    away: TEAMS.barcelona,
    league: "라리가",
    kickoffAt: d("2026-11-14T23:00:00"),
    status: "SCHEDULED",
  },
  {
    id: 102,
    home: TEAMS.mancity,
    away: TEAMS.liverpool,
    league: "프리미어리그",
    kickoffAt: d("2026-11-14T23:30:00"),
    status: "SCHEDULED",
  },
  {
    id: 103,
    home: TEAMS.chelsea,
    away: TEAMS.arsenal,
    league: "프리미어리그",
    kickoffAt: d("2026-11-20T04:00:00"),
    status: "SCHEDULED",
  },
  {
    id: 104,
    home: TEAMS.tottenham,
    away: TEAMS.liverpool,
    league: "프리미어리그",
    kickoffAt: d("2026-11-21T22:00:00"),
    status: "SCHEDULED",
  },
]

// 캘린더 점 찍을 날짜 (YYYY-MM-DD → 경기 수)
export const MATCH_DAYS: Record<string, number> = {
  "2026-11-08": 1,
  "2026-11-13": 1,
  "2026-11-14": 3,
  "2026-11-20": 1,
  "2026-11-21": 2,
}

export const TODAY_MATCH = MATCHES[0] // 토트넘 vs 아스널

// ---------- 관람 신청 (초대장) ----------
// 유저가 "이 경기를 보러 가겠다"고 신청한 내역. 경기 1시간 전부터 입장 초대장이 활성화된다.
export interface AppliedMatch {
  id: number // 신청 식별자 = matchId 재사용
  match: Match
  cheeredTeam: Team
}

export const ENTRY_WINDOW_MIN = 60 // 경기 시작 N분 전부터 입장 가능
const MATCH_DURATION_MIN = 150 // 킥오프 후 이 시간까지는 입장 유지(대략 경기 길이)

// 데모 안정성용 시드. 킥오프를 "현재 시각 기준 상대값"으로 만들어
// 언제 시연하든 "활성 초대장 / 잠긴 초대장" 상태를 모두 재현한다.
export function seedAppliedMatches(now: Date = new Date()): AppliedMatch[] {
  const at = (minFromNow: number) => new Date(now.getTime() + minFromNow * 60_000).toISOString()
  return [
    // 40분 뒤 → 1시간 이내 → 입장 가능
    { id: 9001, cheeredTeam: TEAMS.arsenal, match: { id: 9001, home: TEAMS.tottenham, away: TEAMS.arsenal, league: "프리미어리그", kickoffAt: at(40), status: "SCHEDULED" } },
    // 4시간 뒤 → 아직 잠김
    { id: 9002, cheeredTeam: TEAMS.liverpool, match: { id: 9002, home: TEAMS.mancity, away: TEAMS.liverpool, league: "프리미어리그", kickoffAt: at(260), status: "SCHEDULED" } },
    // 내일 → 잠김
    { id: 9003, cheeredTeam: TEAMS.barcelona, match: { id: 9003, home: TEAMS.realmadrid, away: TEAMS.barcelona, league: "라리가", kickoffAt: at(1500), status: "SCHEDULED" } },
  ]
}

export interface InvitationState {
  canEnter: boolean // 입장 버튼 활성화 여부 (경기 1시간 전 ~ 경기 종료)
  started: boolean // 킥오프가 지났는지
  minutesUntil: number // 킥오프까지 남은 분 (음수면 이미 시작)
}

export function invitationState(kickoffAt: string, now: Date = new Date()): InvitationState {
  const diffMs = new Date(kickoffAt).getTime() - now.getTime()
  const minutesUntil = Math.ceil(diffMs / 60_000)
  const started = diffMs <= 0
  const canEnter = minutesUntil <= ENTRY_WINDOW_MIN && diffMs > -MATCH_DURATION_MIN * 60_000
  return { canEnter, started, minutesUntil }
}

// 킥오프까지 남은 시간을 사람이 읽는 문구로. (양수 분 기준)
export function formatCountdown(minutesUntil: number): string {
  if (minutesUntil <= 0) return "곧 시작"
  if (minutesUntil < 60) return `${minutesUntil}분 후`
  const h = Math.floor(minutesUntil / 60)
  const m = minutesUntil % 60
  if (h < 24) return m === 0 ? `${h}시간 후` : `${h}시간 ${m}분 후`
  const days = Math.floor(h / 24)
  return `${days}일 후`
}

// 경기 중계 스트림 (데모용 샘플 소스).
// 실제 중계로 교체하려면 이 URL만 바꾸면 됨. HLS는 지원 브라우저(Safari)에서 네이티브 재생, 그 외는 mp4 프로그레시브.
export const STREAM = {
  hlsUrl: "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
  mp4Url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
  viewers: 1284,
}

// ---------- My cheer records ----------
export const MY_RECORDS: CheerRecord[] = [
  {
    id: 1,
    match: {
      id: 90, home: TEAMS.tottenham, away: TEAMS.arsenal, league: "프리미어리그",
      kickoffAt: "2026-11-14T20:30:00", status: "FINISHED", homeScore: 2, awayScore: 1,
    },
    cheeredTeamId: TEAMS.tottenham.id, result: "WIN", pointsEarned: 100,
  },
  {
    id: 2,
    match: {
      id: 91, home: TEAMS.mancity, away: TEAMS.liverpool, league: "프리미어리그",
      kickoffAt: "2026-11-07T23:30:00", status: "FINISHED", homeScore: 0, awayScore: 2,
    },
    cheeredTeamId: TEAMS.mancity.id, result: "LOSE", pointsEarned: 30,
  },
  {
    id: 3,
    match: {
      id: 92, home: TEAMS.tottenham, away: TEAMS.chelsea, league: "프리미어리그",
      kickoffAt: "2026-10-31T20:30:00", status: "FINISHED", homeScore: 1, awayScore: 1,
    },
    cheeredTeamId: TEAMS.tottenham.id, result: "DRAW", pointsEarned: 50,
  },
  {
    id: 4,
    match: {
      id: 93, home: TEAMS.arsenal, away: TEAMS.barcelona, league: "친선경기",
      kickoffAt: "2026-10-25T04:00:00", status: "FINISHED", homeScore: 3, awayScore: 1,
    },
    cheeredTeamId: TEAMS.arsenal.id, result: "WIN", pointsEarned: 100,
  },
  {
    id: 5,
    match: {
      id: 94, home: TEAMS.arsenal, away: TEAMS.mancity, league: "프리미어리그",
      kickoffAt: "2026-10-18T20:30:00", status: "FINISHED", homeScore: 2, awayScore: 0,
    },
    cheeredTeamId: TEAMS.arsenal.id, result: "WIN", pointsEarned: 100,
  },
  {
    id: 6,
    match: {
      id: 95, home: TEAMS.liverpool, away: TEAMS.tottenham, league: "프리미어리그",
      kickoffAt: "2026-10-12T22:00:00", status: "FINISHED", homeScore: 3, awayScore: 3,
    },
    cheeredTeamId: TEAMS.tottenham.id, result: "DRAW", pointsEarned: 50,
  },
  {
    id: 7,
    match: {
      id: 96, home: TEAMS.chelsea, away: TEAMS.tottenham, league: "프리미어리그",
      kickoffAt: "2026-10-05T23:30:00", status: "FINISHED", homeScore: 2, awayScore: 1,
    },
    cheeredTeamId: TEAMS.tottenham.id, result: "LOSE", pointsEarned: 30,
  },
  {
    id: 8,
    match: {
      id: 97, home: TEAMS.arsenal, away: TEAMS.liverpool, league: "프리미어리그",
      kickoffAt: "2026-09-28T20:30:00", status: "FINISHED", homeScore: 1, awayScore: 0,
    },
    cheeredTeamId: TEAMS.arsenal.id, result: "WIN", pointsEarned: 100,
  },
  {
    id: 9,
    match: {
      id: 98, home: TEAMS.barcelona, away: TEAMS.realmadrid, league: "라리가",
      kickoffAt: "2026-09-21T23:00:00", status: "FINISHED", homeScore: 0, awayScore: 2,
    },
    cheeredTeamId: TEAMS.barcelona.id, result: "LOSE", pointsEarned: 30,
  },
  {
    id: 10,
    match: {
      id: 99, home: TEAMS.tottenham, away: TEAMS.mancity, league: "프리미어리그",
      kickoffAt: "2026-09-14T20:30:00", status: "FINISHED", homeScore: 4, awayScore: 1,
    },
    cheeredTeamId: TEAMS.tottenham.id, result: "WIN", pointsEarned: 100,
  },
  {
    id: 11,
    match: {
      id: 110, home: TEAMS.arsenal, away: TEAMS.chelsea, league: "프리미어리그",
      kickoffAt: "2026-09-07T22:00:00", status: "FINISHED", homeScore: 2, awayScore: 2,
    },
    cheeredTeamId: TEAMS.arsenal.id, result: "DRAW", pointsEarned: 50,
  },
  {
    id: 12,
    match: {
      id: 111, home: TEAMS.realmadrid, away: TEAMS.arsenal, league: "친선경기",
      kickoffAt: "2026-08-30T04:00:00", status: "FINISHED", homeScore: 1, awayScore: 3,
    },
    cheeredTeamId: TEAMS.arsenal.id, result: "WIN", pointsEarned: 100,
  },
  {
    id: 13,
    match: {
      id: 112, home: TEAMS.liverpool, away: TEAMS.arsenal, league: "프리미어리그",
      kickoffAt: "2026-08-23T22:00:00", status: "FINISHED", homeScore: 2, awayScore: 1,
    },
    cheeredTeamId: TEAMS.arsenal.id, result: "LOSE", pointsEarned: 30,
  },
  {
    id: 14,
    match: {
      id: 113, home: TEAMS.tottenham, away: TEAMS.barcelona, league: "친선경기",
      kickoffAt: "2026-08-16T20:30:00", status: "FINISHED", homeScore: 3, awayScore: 0,
    },
    cheeredTeamId: TEAMS.tottenham.id, result: "WIN", pointsEarned: 100,
  },
]

// 시즌 통계 (목업 기준 42경기)
export const SEASON_STATS = { total: 42, win: 28, draw: 3, lose: 13 }

// ---------- Badges ----------
export const BADGES: Badge[] = [
  { code: "VICTORY_FAIRY", name: "승리요정", desc: "승률 60% 이상", emoji: "👑", acquired: true },
  { code: "DEFEAT_FAIRY", name: "패배요정", desc: "패배율 30% 이상", emoji: "🌧️", acquired: true },
  { code: "WIN_STREAK_3", name: "연승러", desc: "3연승 달성", emoji: "🔥", acquired: true },
  { code: "DECIBEL_MASTER", name: "데시벨 마스터", desc: "최고 110dB 이상", emoji: "📢", acquired: true },
  { code: "STEADY_FAN", name: "꾸준한 응원단", desc: "10경기 이상", emoji: "📅", acquired: true },
  { code: "NIGHT_OWL", name: "새벽 직관러", desc: "새벽 경기 5회", emoji: "🦉", acquired: false },
  { code: "ANALYST", name: "분석왕", desc: "예측 적중 20회", emoji: "🧠", acquired: false },
  { code: "LOUDEST", name: "오늘의 응원왕", desc: "대결 1위", emoji: "🏆", acquired: true },
]

// ---------- Rankings ----------
export const VICTORY_RANKING: RankingEntry[] = [
  { rank: 1, nickname: "승리요정민지", rate: 1.0, played: 4, wins: 4, emoji: "😎" },
  { rank: 2, nickname: "승리요정도현", rate: 0.92, played: 12, wins: 11, emoji: "👑" },
  { rank: 3, nickname: "승리요정유나", rate: 0.9, played: 10, wins: 9, emoji: "🥰" },
  { rank: 4, nickname: "승리의집요정", rate: 0.88, played: 8, wins: 7, emoji: "🐶" },
  { rank: 5, nickname: "열정승리요정", rate: 0.85, played: 13, wins: 11, emoji: "🔥" },
]

export const DEFEAT_RANKING: RankingEntry[] = [
  { rank: 1, nickname: "패배왕곰돌이", rate: 1.0, played: 1, wins: 0, emoji: "🐻" },
  { rank: 2, nickname: "아쉬운토끼", rate: 0.75, played: 4, wins: 1, emoji: "🐰" },
  { rank: 3, nickname: "패배요정지니", rate: 0.66, played: 3, wins: 1, emoji: "🧞" },
  { rank: 4, nickname: "마이너스요정", rate: 0.62, played: 8, wins: 3, emoji: "📉" },
  { rank: 5, nickname: "실패는괜찮아", rate: 0.6, played: 5, wins: 2, emoji: "🫠" },
]

// ---------- Community feed ----------
export const COMMUNITY_FEED = [
  { nickname: "승리요정민지", emoji: "😎", text: "오늘 경기 무조건 간다요!!", ago: "1분 전" },
  { nickname: "패배요정지니", emoji: "🧞", text: "아스널은 좀 힘들지 않을까요...?", ago: "2분 전" },
  { nickname: "열정승리요정", emoji: "🔥", text: "이번엔 제발 이겨보자 🙏", ago: "3분 전" },
  { nickname: "아쉬운토끼", emoji: "🐰", text: "손흥민 폼 미쳤던데", ago: "5분 전" },
]

// ---------- Decibel battle (최종 결과 예시) ----------
export const BATTLE_PLAYERS: BattlePlayer[] = [
  { userId: 2, nickname: "승리요정민지", peakDb: 112.3, emoji: "😎" },
  { userId: 3, nickname: "아쉬운토끼", peakDb: 108.7, emoji: "🐰" },
  { userId: 4, nickname: "열정승리요정", peakDb: 105.9, emoji: "🔥" },
  { userId: 5, nickname: "풋볼러지니", peakDb: 101.2, emoji: "🧞" },
  { userId: 1, nickname: "뚜비응원단", peakDb: 97.6, emoji: "🐶", me: true },
]

export const BATTLE_REWARDS = [100, 50, 30]

// ---------- Fortune ----------
export const FORTUNES: Record<number, Fortune> = {
  [TEAMS.arsenal.id]: {
    teamId: TEAMS.arsenal.id,
    fortuneText: "흐름이 좋은 날이에요! 전반에 기선제압하면 승리 확률이 높아요.",
    cheerTip: "후반 교체 타이밍을 주목하세요",
    luckScore: 78,
  },
  [TEAMS.tottenham.id]: {
    teamId: TEAMS.tottenham.id,
    fortuneText: "변수가 많은 날. 세트피스 한 방이 승부를 가를 수 있어요.",
    cheerTip: "코너킥마다 크게 소리질러 주세요",
    luckScore: 61,
  },
}

// ============================================================
// 헬퍼 (명세 3장 비즈니스 규칙)
// ============================================================

// 승률 = 승 / (승+패), 무승부 제외
export function winRate(win: number, lose: number): number {
  const denom = win + lose
  return denom === 0 ? 0 : win / denom
}
export function loseRate(win: number, lose: number): number {
  const denom = win + lose
  return denom === 0 ? 0 : lose / denom
}

export function fairyOf(win: number, lose: number): FairyType {
  if (winRate(win, lose) >= 0.6) return "VICTORY"
  if (loseRate(win, lose) >= 0.3) return "DEFEAT"
  return "NEUTRAL"
}

export const FAIRY_META: Record<FairyType, { label: string; emoji: string; color: string }> = {
  VICTORY: { label: "승리요정", emoji: "👑", color: "var(--c-primary)" },
  DEFEAT: { label: "패배요정", emoji: "🌧️", color: "var(--c-lose)" },
  NEUTRAL: { label: "중립요정", emoji: "😐", color: "var(--c-muted)" },
}

export const pct = (v: number) => `${Math.round(v * 100)}%`

export function resultMeta(r: MatchResult) {
  switch (r) {
    case "WIN": return { label: "승리", color: "var(--c-win)", bg: "var(--c-win-soft)" }
    case "LOSE": return { label: "패배", color: "var(--c-lose)", bg: "var(--c-lose-soft)" }
    case "DRAW": return { label: "무승부", color: "var(--c-draw)", bg: "var(--c-surface-2)" }
    default: return { label: "예정", color: "var(--c-muted)", bg: "var(--c-surface-2)" }
  }
}

export function formatKDate(iso: string): string {
  const days = ["일", "월", "화", "수", "목", "금", "토"]
  const dt = new Date(iso)
  const mm = String(dt.getMonth() + 1).padStart(2, "0")
  const dd = String(dt.getDate()).padStart(2, "0")
  return `${mm}.${dd} (${days[dt.getDay()]})`
}

export function formatTime(iso: string): string {
  const dt = new Date(iso)
  return `${String(dt.getHours()).padStart(2, "0")}:${String(dt.getMinutes()).padStart(2, "0")}`
}

export const SEASON_WINRATE = winRate(SEASON_STATS.win, SEASON_STATS.lose) // 0.68
export const SEASON_LOSERATE = loseRate(SEASON_STATS.win, SEASON_STATS.lose) // 0.32

// ============================================================
// 공개 프로필 (프로필 URL 공유 → 서로의 프로필 열람)
// ============================================================

export interface PublicProfile {
  id: number
  nickname: string
  bio: string
  level: number
  levelTitle: string
  totalPoints: number
  teams: Team[]
  favoriteTeam: Team
  style: { label: string; value: number; emoji: string }[]
  stats: { total: number; win: number; draw: number; lose: number }
  records: CheerRecord[]
  badges: Badge[]
}

// 코드 목록으로 배지 획득 여부를 입힌다 (공통 BADGES 메타 재사용)
function badgesWith(codes: string[]): Badge[] {
  return BADGES.map((b) => ({ ...b, acquired: codes.includes(b.code) }))
}

// 간단한 경기 기록 팩토리 (타 유저 샘플용)
let _recId = 2000
function rec(
  home: Team,
  away: Team,
  homeScore: number,
  awayScore: number,
  cheered: Team,
  kickoffAt: string,
): CheerRecord {
  const cheeredScore = cheered.id === home.id ? homeScore : awayScore
  const otherScore = cheered.id === home.id ? awayScore : homeScore
  const result: MatchResult =
    cheeredScore > otherScore ? "WIN" : cheeredScore < otherScore ? "LOSE" : "DRAW"
  const pointsEarned = result === "WIN" ? 100 : result === "DRAW" ? 50 : 30
  _recId += 1
  return {
    id: _recId,
    match: {
      id: _recId + 7000,
      home,
      away,
      league: home.league,
      kickoffAt,
      status: "FINISHED",
      homeScore,
      awayScore,
    },
    cheeredTeamId: cheered.id,
    result,
    pointsEarned,
  }
}

// 본인 프로필 (기존 ME + 시즌 데이터 결합)
export const ME_PROFILE: PublicProfile = {
  ...ME,
  stats: SEASON_STATS,
  records: MY_RECORDS,
  badges: BADGES,
}

// 타 유저 샘플 — 랭킹/대결에 등장하는 페르소나와 id를 맞춘다
const MINJI_RECORDS: CheerRecord[] = [
  rec(TEAMS.mancity, TEAMS.liverpool, 3, 1, TEAMS.mancity, "2026-11-13T23:30:00"),
  rec(TEAMS.realmadrid, TEAMS.barcelona, 2, 0, TEAMS.realmadrid, "2026-11-08T23:00:00"),
  rec(TEAMS.chelsea, TEAMS.arsenal, 1, 0, TEAMS.chelsea, "2026-11-01T22:00:00"),
  rec(TEAMS.mancity, TEAMS.chelsea, 4, 2, TEAMS.mancity, "2026-10-25T22:00:00"),
]

const TOKKI_RECORDS: CheerRecord[] = [
  rec(TEAMS.tottenham, TEAMS.arsenal, 0, 2, TEAMS.tottenham, "2026-11-13T20:30:00"),
  rec(TEAMS.liverpool, TEAMS.tottenham, 3, 1, TEAMS.tottenham, "2026-11-06T22:00:00"),
  rec(TEAMS.tottenham, TEAMS.chelsea, 1, 1, TEAMS.tottenham, "2026-10-30T20:30:00"),
  rec(TEAMS.barcelona, TEAMS.tottenham, 2, 0, TEAMS.tottenham, "2026-10-23T23:00:00"),
]

export const PROFILES: Record<number, PublicProfile> = {
  1: ME_PROFILE,
  2: {
    id: 2,
    nickname: "승리요정민지",
    bio: "맨시티 직관 가면 거의 이겨요 😎",
    level: 15,
    levelTitle: "승리 요정",
    totalPoints: 5240,
    teams: [TEAMS.mancity, TEAMS.realmadrid],
    favoriteTeam: TEAMS.mancity,
    style: [
      { label: "열혈팬", value: 88, emoji: "🔥" },
      { label: "분석왕", value: 95, emoji: "📊" },
      { label: "데시벨러", value: 72, emoji: "📢" },
    ],
    stats: { total: 24, win: 18, draw: 2, lose: 4 },
    records: MINJI_RECORDS,
    badges: badgesWith(["VICTORY_FAIRY", "WIN_STREAK_3", "ANALYST", "LOUDEST"]),
  },
  3: {
    id: 3,
    nickname: "아쉬운토끼",
    bio: "그래도 토트넘 끝까지 응원해요 🐰",
    level: 9,
    levelTitle: "꾸준 응원러",
    totalPoints: 1980,
    teams: [TEAMS.tottenham],
    favoriteTeam: TEAMS.tottenham,
    style: [
      { label: "열혈팬", value: 96, emoji: "🔥" },
      { label: "분석왕", value: 48, emoji: "📊" },
      { label: "데시벨러", value: 90, emoji: "📢" },
    ],
    stats: { total: 20, win: 6, draw: 5, lose: 9 },
    records: TOKKI_RECORDS,
    badges: badgesWith(["DEFEAT_FAIRY", "STEADY_FAN", "NIGHT_OWL"]),
  },
}

export function getProfile(id: number): PublicProfile | undefined {
  return PROFILES[id]
}
