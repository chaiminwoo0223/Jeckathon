// 경기 중계 영상 (YouTube, TVING SPORTS 2026 KBO 공식 하이라이트, 삽입 허용 확인).
// 경기의 두 팀이 모두 나오는 영상 → 한 팀이라도 나오는 영상 → 기본 영상 순으로 고른다.
// 같은 후보가 여러 개면 대진으로 하나를 정해, 경기마다 다른 영상이 나오고 같은 경기는 늘 같은 영상이 나온다.

export interface Broadcast {
  youtubeId: string
  title: string
  teams: [string, string] // Team.name 과 같은 표기 ("LG", "두산", "KIA" ...)
}

export const DEFAULT_BROADCAST: Broadcast = {
  youtubeId: "yzTjqEbCn_s",
  title: "[삼성 vs KT] 11/4 한국시리즈 2차전",
  teams: ["삼성", "KT"],
}

export const BROADCASTS: Broadcast[] = [
  DEFAULT_BROADCAST,
  {
    youtubeId: "41F-_WHq_hQ",
    title: "[두산 vs LG] 10/14 와일드카드 결정전 1차전",
    teams: ["두산", "LG"],
  },
  {
    youtubeId: "9OTJOY5-usI",
    title: "[LG vs 두산] 8/1 경기",
    teams: ["LG", "두산"],
  },
  {
    youtubeId: "wyC8BnovUUA",
    title: "[KIA vs 삼성] 10/26 플레이오프 1차전",
    teams: ["KIA", "삼성"],
  },
  {
    youtubeId: "ejMdL3m6Dpc",
    title: "[삼성 vs KIA] 10/30 플레이오프 4차전",
    teams: ["삼성", "KIA"],
  },
  {
    youtubeId: "Qrb5938wR48",
    title: "[SSG vs 롯데] 9/16 경기",
    teams: ["SSG", "롯데"],
  },
  {
    youtubeId: "XDmtkjcY_Fc",
    title: "[롯데 vs SSG] 6/16 경기",
    teams: ["롯데", "SSG"],
  },
  {
    youtubeId: "KJTNDCfzll4",
    title: "[LG vs 삼성] 9/13 경기",
    teams: ["LG", "삼성"],
  },
  {
    youtubeId: "yKZzXXNmKIM",
    title: "[삼성 vs LG] 9/5 경기",
    teams: ["삼성", "LG"],
  },
  {
    youtubeId: "wh-Ql5Lb9Ps",
    title: "[LG vs KIA] 10/17 준플레이오프 1차전",
    teams: ["LG", "KIA"],
  },
  {
    youtubeId: "QQuNLG71hfg",
    title: "[두산 vs 롯데] 10/6 경기",
    teams: ["두산", "롯데"],
  },
  {
    youtubeId: "bEHHpUlvl-8",
    title: "[한화 vs 두산] 8/11 경기",
    teams: ["한화", "두산"],
  },
  {
    youtubeId: "vdY_rHWfiOY",
    title: "[키움 vs 한화] 3/28 경기",
    teams: ["키움", "한화"],
  },
  {
    youtubeId: "Z5nUsUoGkBA",
    title: "[LG vs 키움] 7/1 경기",
    teams: ["LG", "키움"],
  },
  {
    youtubeId: "qegNjNy2MAs",
    title: "[SSG vs NC] 10/5 경기",
    teams: ["SSG", "NC"],
  },
  {
    youtubeId: "_DM9oNFuZSU",
    title: "[NC vs 한화] 8/30 경기",
    teams: ["NC", "한화"],
  },
  {
    youtubeId: "S5znhSAl9dw",
    title: "[KT vs KIA] 10/1 경기",
    teams: ["KT", "KIA"],
  },
]

function hash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return Math.abs(h)
}

export function pickBroadcast(home: string, away: string): Broadcast {
  const has = (b: Broadcast, t: string) => b.teams.includes(t)
  const both = BROADCASTS.filter((b) => has(b, home) && has(b, away))
  const either = BROADCASTS.filter((b) => has(b, home) || has(b, away))
  const pool = both.length ? both : either
  if (!pool.length) return DEFAULT_BROADCAST
  return pool[hash(`${home}|${away}`) % pool.length]
}
